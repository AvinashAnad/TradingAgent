from __future__ import annotations

import json
import re
from typing import Any, Optional

import requests

from stocks_analyser.config import Settings
from stocks_analyser.models import CrossCheckResult, IndicatorSnapshot, StockFundamentals


class NvidiaHypothesisVerifier:
    """Optional NVIDIA LLM verifier for statistical trading decisions.

    The verifier is designed to audit the statistical engine output. In v1,
    engine behavior remains unchanged when mode is audit_only.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def is_enabled(self) -> bool:
        mode = self.settings.llm_crosscheck_mode.strip().lower()
        return mode != "off" and bool(self.settings.nvidia_api_key.strip())

    def cross_check(
        self,
        symbol: str,
        name: str,
        statistical_action: str,
        statistical_reasons: list[str],
        snapshot: IndicatorSnapshot,
        fundamentals: StockFundamentals,
        has_open_position: bool,
    ) -> Optional[CrossCheckResult]:
        mode = self.settings.llm_crosscheck_mode.strip().lower()
        if mode == "off" or not self.settings.nvidia_api_key.strip():
            return None

        system_prompt = (
            "You are a risk-aware market analysis assistant. "
            "Given indicator and fundamentals context, return only a JSON object "
            "with keys: action, confidence, rationale. "
            "action must be one of BUY, SELL, HOLD. confidence must be in [0,1]."
        )
        user_prompt = self._build_user_prompt(
            symbol=symbol,
            name=name,
            statistical_action=statistical_action,
            statistical_reasons=statistical_reasons,
            snapshot=snapshot,
            fundamentals=fundamentals,
            has_open_position=has_open_position,
        )

        payload = {
            "model": self.settings.nvidia_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.settings.nvidia_temperature,
            "max_tokens": self.settings.nvidia_max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.nvidia_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        response = requests.post(
            self.settings.nvidia_base_url,
            headers=headers,
            json=payload,
            timeout=self.settings.nvidia_timeout_seconds,
        )
        response.raise_for_status()

        raw_content = self._extract_content(response.json())
        parsed = self._parse_json_content(raw_content)

        llm_action = str(parsed.get("action", statistical_action)).strip().upper()
        if llm_action not in {"BUY", "SELL", "HOLD"}:
            llm_action = statistical_action

        llm_confidence = self._clamp_confidence(parsed.get("confidence"))
        llm_rationale = str(parsed.get("rationale", "")).strip() or "No rationale provided"

        return CrossCheckResult(
            action=llm_action,
            confidence=llm_confidence,
            rationale=llm_rationale,
            provider="nvidia",
            model=self.settings.nvidia_model,
            mode=mode,
        )

    def _build_user_prompt(
        self,
        symbol: str,
        name: str,
        statistical_action: str,
        statistical_reasons: list[str],
        snapshot: IndicatorSnapshot,
        fundamentals: StockFundamentals,
        has_open_position: bool,
    ) -> str:
        context = {
            "symbol": symbol,
            "name": name,
            "statistical_action": statistical_action,
            "statistical_reasons": statistical_reasons,
            "has_open_position": has_open_position,
            "indicator_snapshot": snapshot.__dict__,
            "fundamentals": fundamentals.__dict__,
        }
        return (
            "Cross-check this trading hypothesis and return JSON only with keys "
            "action, confidence, rationale. Context: "
            f"{json.dumps(context, separators=(',', ':'))}"
        )

    @staticmethod
    def _extract_content(body: dict[str, Any]) -> str:
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            return "{}"

        message = choices[0].get("message", {})
        content = message.get("content", "{}")

        if isinstance(content, list):
            parts: list[str] = []
            for part in content:
                if isinstance(part, dict):
                    text = part.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            return " ".join(parts) if parts else "{}"

        if isinstance(content, str):
            return content

        return "{}"

    @staticmethod
    def _parse_json_content(text: str) -> dict[str, Any]:
        raw = text.strip()
        if not raw:
            return {}

        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            pass

        # Some models may wrap JSON with prose; extract the first JSON object.
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if match is None:
            return {}

        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _clamp_confidence(value: Any) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            return 0.5

        if confidence < 0:
            return 0.0
        if confidence > 1:
            return 1.0
        return confidence

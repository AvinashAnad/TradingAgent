from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from typing import Any, Optional

import requests

from stocks_analyser.config import Settings


@dataclass
class DhanLiveDataAdapter:
    """Production-only adapter placeholder for live minute data from Dhan.

    v1 runs paper trading with yfinance historical data. This adapter defines
    the integration seam for future production mode.
    """

    settings: Settings

    def is_configured(self) -> bool:
        return bool(self.settings.dhan_access_token.strip() and self.settings.dhan_client_id.strip())

    def _build_url(self, endpoint: str) -> str:
        base = self.settings.dhan_base_url.rstrip("/")
        path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        return f"{base}{path}"

    def _symbol_map(self) -> dict[str, str]:
        raw = self.settings.dhan_symbol_security_map.strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                return {}
            mapped: dict[str, str] = {}
            for key, value in parsed.items():
                if key is None or value is None:
                    continue
                mapped[str(key).upper()] = str(value)
            return mapped
        except json.JSONDecodeError:
            return {}

    def resolve_security_id(self, symbol: str) -> Optional[str]:
        cleaned = symbol.strip()
        if not cleaned:
            return None
        if cleaned.isdigit():
            return cleaned
        return self._symbol_map().get(cleaned.upper())

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "access-token": self.settings.dhan_access_token,
            "client-id": self.settings.dhan_client_id,
        }

    def check_api_state(self) -> tuple[bool, str]:
        if not self.is_configured():
            return False, "missing Dhan credentials"

        url = self._build_url(self.settings.dhan_health_endpoint)
        try:
            response = requests.get(url, headers=self._auth_headers(), timeout=10)
            if 200 <= response.status_code < 300:
                return True, f"API state ok ({response.status_code})"
            return False, f"API state failed ({response.status_code})"
        except Exception as exc:
            return False, f"API state check error: {exc}"

    def place_market_order_by_symbol(
        self,
        symbol: str,
        side: str,
        quantity: int,
    ) -> tuple[bool, str, Optional[str]]:
        if not self.is_configured():
            return False, "missing Dhan credentials", None

        security_id = self.resolve_security_id(symbol)
        if security_id is None:
            return False, f"no securityId mapping found for symbol {symbol}", None

        url = self._build_url(self.settings.dhan_order_endpoint)
        payload = {
            "dhanClientId": self.settings.dhan_client_id,
            "transactionType": side,
            "exchangeSegment": self.settings.dhan_exchange_segment,
            "productType": self.settings.dhan_product_type,
            "orderType": self.settings.dhan_order_type,
            "validity": self.settings.dhan_validity,
            "securityId": security_id,
            "quantity": quantity,
        }

        try:
            response = requests.post(url, headers=self._auth_headers(), json=payload, timeout=15)
            response.raise_for_status()
            body = response.json() if response.content else {}
            order_id = body.get("orderId") or body.get("data", {}).get("orderId")
            return True, "live order submitted", str(order_id) if order_id else None
        except Exception as exc:
            return False, f"live order failed: {exc}", None

    def get_latest_quote(self, security_id: str) -> Optional[dict[str, Any]]:
        if not self.is_configured():
            return None

        url = self._build_url("/quotes")
        payload = {"securityId": security_id}
        response = requests.post(url, headers=self._auth_headers(), json=payload, timeout=15)
        response.raise_for_status()
        return response.json()

    def get_minute_candles(
        self,
        security_id: str,
        from_datetime: datetime,
        to_datetime: datetime,
        interval: int = 1,
    ) -> Optional[dict[str, Any]]:
        if not self.is_configured():
            return None

        url = self._build_url("/charts/historical")
        payload = {
            "securityId": security_id,
            "fromDate": from_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            "toDate": to_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            "interval": interval,
        }
        response = requests.post(url, headers=self._auth_headers(), json=payload, timeout=20)
        response.raise_for_status()
        return response.json()

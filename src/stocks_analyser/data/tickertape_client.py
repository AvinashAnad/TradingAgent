from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import requests

from stocks_analyser.config import Settings
from stocks_analyser.models import StockFundamentals


@dataclass
class TickertapeClient:
    settings: Settings

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json;charset=UTF-8",
            "Accept-Language": "en-IN,en;q=0.9",
            "User-Agent": "Mozilla/5.0 (Linux; Android 14; Mobile)",
        }

    def fetch_fundamentals(self, max_stocks: Optional[int] = None) -> list[StockFundamentals]:
        target_count = max_stocks or self.settings.max_stocks
        collected: list[StockFundamentals] = []
        offset = 0

        while len(collected) < target_count:
            page_size = min(self.settings.tickertape_page_size, target_count - len(collected))
            payload = {
                "sortBy": "mrktCapf",
                "sortOrder": -1,
                "project": [
                    "sid",
                    "ticker",
                    "name",
                    "sector",
                    "apef",
                    "advancedRatios",
                    "growthRatios",
                    "shareHolding",
                ],
                "offset": offset,
                "count": page_size,
                "match": {"mrktCapf": {"g": 0}},
                "sids": [],
            }

            url = f"{self.settings.tickertape_base_url}/screener/query"
            response = requests.post(
                url,
                headers=self._headers,
                json=payload,
                timeout=self.settings.tickertape_timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()

            rows = body.get("data") or body.get("result") or []
            if not rows:
                break

            for row in rows:
                parsed = self._parse_row(row)
                if parsed.symbol:
                    collected.append(parsed)

            offset += len(rows)
            if len(rows) < page_size:
                break

        return collected[:target_count]

    def _parse_row(self, row: dict[str, Any]) -> StockFundamentals:
        info = self._pick(row, ["stock", "info"], {})
        ratios = self._pick(row, ["stock", "advancedRatios"], {})
        growth = self._pick(row, ["stock", "growthRatios"], {})
        holding = self._pick(row, ["stock", "shareHolding"], {})

        symbol = self._pick_any(
            row,
            [["ticker"], ["sid"], ["stock", "sid"], ["stock", "ticker"], ["stock", "info", "ticker"]],
            default="",
        )
        name = self._pick_any(
            row,
            [["name"], ["stock", "name"], ["stock", "info", "name"]],
            default=symbol,
        )
        sector = self._pick_any(row, [["sector"], ["stock", "info", "sector"], ["stock", "sector"]])

        pe_ratio = self._to_float(
            self._pick_any(row, [["apef"], ["stock", "apef"], ["stock", "advancedRatios", "pe"], ["stock", "advancedRatios", "apef"]])
        )
        promoter_holding = self._to_float(
            self._pick_any(
                row,
                [
                    ["stock", "shareHolding", "promoter"],
                    ["stock", "shareHolding", "promoterHolding"],
                    ["shareHolding", "promoter"],
                    ["shareHolding", "promoterHolding"],
                ],
            )
        )
        revenue_growth = self._to_float(
            self._pick_any(
                row,
                [
                    ["stock", "growthRatios", "revenueGrowth"],
                    ["growthRatios", "revenueGrowth"],
                    ["stock", "growthRatios", "salesGrowth"],
                    ["growthRatios", "salesGrowth"],
                ],
            )
        )
        profit_growth = self._to_float(
            self._pick_any(
                row,
                [
                    ["stock", "growthRatios", "profitGrowth"],
                    ["growthRatios", "profitGrowth"],
                    ["stock", "growthRatios", "patGrowth"],
                    ["growthRatios", "patGrowth"],
                ],
            )
        )

        _ = info, ratios, growth, holding

        return StockFundamentals(
            symbol=str(symbol),
            name=str(name),
            sector=str(sector) if sector is not None else None,
            pe_ratio=pe_ratio,
            promoter_holding=promoter_holding,
            revenue_growth=revenue_growth,
            profit_growth=profit_growth,
        )

    @staticmethod
    def _pick(data: dict[str, Any], path: list[str], default: Any = None) -> Any:
        current: Any = data
        for key in path:
            if not isinstance(current, dict) or key not in current:
                return default
            current = current[key]
        return current

    @classmethod
    def _pick_any(cls, data: dict[str, Any], paths: list[list[str]], default: Any = None) -> Any:
        for path in paths:
            value = cls._pick(data, path)
            if value is not None:
                return value
        return default

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "access-token": self.settings.dhan_access_token,
            "client-id": self.settings.dhan_client_id,
        }

    def get_latest_quote(self, security_id: str) -> Optional[dict[str, Any]]:
        if not self.settings.dhan_access_token or not self.settings.dhan_client_id:
            return None

        url = f"{self.settings.dhan_base_url}/quotes"
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
        if not self.settings.dhan_access_token or not self.settings.dhan_client_id:
            return None

        url = f"{self.settings.dhan_base_url}/charts/historical"
        payload = {
            "securityId": security_id,
            "fromDate": from_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            "toDate": to_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            "interval": interval,
        }
        response = requests.post(url, headers=self._auth_headers(), json=payload, timeout=20)
        response.raise_for_status()
        return response.json()

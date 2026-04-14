from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple

import pandas as pd
import yfinance as yf


@dataclass
class YFinanceProvider:
    default_exchange_suffix: str = ".NS"
    _cache: Dict[Tuple[str, str, str], pd.DataFrame] = field(default_factory=dict)

    def normalize_symbol(self, symbol: str) -> str:
        symbol = symbol.strip().upper()
        if symbol.endswith(".NS") or symbol.endswith(".BO"):
            return symbol
        return f"{symbol}{self.default_exchange_suffix}"

    def get_ohlc(self, symbol: str, period: str = "6mo", interval: str = "1h") -> pd.DataFrame:
        normalized = self.normalize_symbol(symbol)
        key = (normalized, period, interval)
        if key in self._cache:
            return self._cache[key].copy()

        df = yf.download(
            normalized,
            period=period,
            interval=interval,
            auto_adjust=False,
            progress=False,
            threads=False,
        )

        if df.empty:
            return df

        # Newer yfinance versions can return a MultiIndex like ("Close", "TCS.NS").
        # For single-symbol fetches we only need the first level OHLCV names.
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [str(col[0]) for col in df.columns]

        df = df.rename(columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        })
        df = df[["open", "high", "low", "close", "volume"]].dropna()
        self._cache[key] = df.copy()
        return df

    def clear_cache(self) -> None:
        self._cache.clear()

from __future__ import annotations

import numpy as np
import pandas as pd

from stocks_analyser.models import IndicatorSnapshot


def _sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).mean()


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)

    avg_gain = up.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = down.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def build_snapshot(ohlc: pd.DataFrame) -> IndicatorSnapshot:
    if ohlc.empty or "close" not in ohlc.columns:
        raise ValueError("OHLC data must contain a non-empty 'close' column")

    close = ohlc["close"].astype(float)
    if len(close) < 60:
        raise ValueError("At least 60 points are required for indicator computation")

    sma20 = _sma(close, 20)
    sma50 = _sma(close, 50)
    ema20 = _ema(close, 20)
    ema50 = _ema(close, 50)

    ema12 = _ema(close, 12)
    ema26 = _ema(close, 26)
    macd = ema12 - ema26
    macd_signal = _ema(macd, 9)

    rsi14 = _rsi(close, 14)

    bb_middle = _sma(close, 20)
    bb_std = close.rolling(window=20, min_periods=20).std()
    bb_upper = bb_middle + (2 * bb_std)
    bb_lower = bb_middle - (2 * bb_std)

    latest_close = float(close.iloc[-1])
    latest_sma20 = float(sma20.iloc[-1])
    latest_sma50 = float(sma50.iloc[-1])
    latest_ema20 = float(ema20.iloc[-1])
    latest_ema50 = float(ema50.iloc[-1])
    latest_macd = float(macd.iloc[-1])
    latest_macd_signal = float(macd_signal.iloc[-1])
    latest_rsi14 = float(rsi14.iloc[-1])
    latest_bb_middle = float(bb_middle.iloc[-1])
    latest_bb_upper = float(bb_upper.iloc[-1])
    latest_bb_lower = float(bb_lower.iloc[-1])

    checks = {
        "sma_trend": latest_sma20 > latest_sma50 and latest_close >= latest_sma20,
        "ema_trend": latest_ema20 > latest_ema50,
        "macd": latest_macd > latest_macd_signal,
        "rsi": 40.0 <= latest_rsi14 <= 70.0,
        "bollinger": latest_close >= latest_bb_middle and latest_close <= latest_bb_upper,
    }
    score = sum(1 for status in checks.values() if status)

    return IndicatorSnapshot(
        close=latest_close,
        sma20=latest_sma20,
        sma50=latest_sma50,
        ema20=latest_ema20,
        ema50=latest_ema50,
        macd=latest_macd,
        macd_signal=latest_macd_signal,
        rsi14=latest_rsi14,
        bb_upper=latest_bb_upper,
        bb_middle=latest_bb_middle,
        bb_lower=latest_bb_lower,
        score=score,
    )

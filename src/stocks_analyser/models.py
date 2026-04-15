from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class StockFundamentals:
    symbol: str
    name: str
    sector: Optional[str] = None
    pe_ratio: Optional[float] = None
    promoter_holding: Optional[float] = None
    revenue_growth: Optional[float] = None
    profit_growth: Optional[float] = None


@dataclass(frozen=True)
class IndicatorSnapshot:
    close: float
    sma20: float
    sma50: float
    ema20: float
    ema50: float
    macd: float
    macd_signal: float
    rsi14: float
    bb_upper: float
    bb_middle: float
    bb_lower: float
    score: int


@dataclass(frozen=True)
class AnalysisResult:
    symbol: str
    name: str
    timestamp: datetime
    price: float
    snapshot: IndicatorSnapshot
    fundamentals: StockFundamentals
    action: str
    reasons: list[str]
    llm_action: Optional[str] = None
    llm_confidence: Optional[float] = None
    llm_rationale: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_mode: Optional[str] = None


@dataclass(frozen=True)
class Position:
    symbol: str
    quantity: float
    entry_price: float
    entry_time: datetime


@dataclass(frozen=True)
class DecisionLog:
    symbol: str
    action: str
    timestamp: datetime
    price: float
    score: int
    reasons: list[str]
    llm_action: Optional[str] = None
    llm_confidence: Optional[float] = None
    llm_rationale: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_mode: Optional[str] = None


@dataclass(frozen=True)
class CrossCheckResult:
    action: str
    confidence: float
    rationale: str
    provider: str
    model: str
    mode: str


@dataclass(frozen=True)
class ExecutionLog:
    symbol: str
    action: str
    timestamp: datetime
    mode: str
    execution_type: str
    status: str
    message: str
    broker_order_id: Optional[str] = None

from __future__ import annotations

from dataclasses import dataclass

from stocks_analyser.config import Settings
from stocks_analyser.models import IndicatorSnapshot, Position, StockFundamentals


@dataclass(frozen=True)
class StrategyResult:
    action: str
    reasons: list[str]


@dataclass
class Strategy:
    settings: Settings

    def evaluate_buy(self, fundamentals: StockFundamentals, snapshot: IndicatorSnapshot) -> StrategyResult:
        reasons: list[str] = []
        if snapshot.score < self.settings.min_signal_score:
            reasons.append(
                f"indicator score {snapshot.score} is below min {self.settings.min_signal_score}"
            )
            return StrategyResult(action="HOLD", reasons=reasons)

        if fundamentals.pe_ratio is None or fundamentals.pe_ratio > self.settings.max_pe:
            reasons.append(
                f"PE check failed: {fundamentals.pe_ratio} > {self.settings.max_pe}"
                if fundamentals.pe_ratio is not None
                else "PE missing"
            )
        if (
            fundamentals.promoter_holding is None
            or fundamentals.promoter_holding < self.settings.min_promoter_holding
        ):
            reasons.append(
                f"promoter holding check failed: {fundamentals.promoter_holding} < {self.settings.min_promoter_holding}"
                if fundamentals.promoter_holding is not None
                else "promoter holding missing"
            )
        if (
            fundamentals.revenue_growth is None
            or fundamentals.revenue_growth < self.settings.min_revenue_growth
        ):
            reasons.append(
                f"revenue growth check failed: {fundamentals.revenue_growth} < {self.settings.min_revenue_growth}"
                if fundamentals.revenue_growth is not None
                else "revenue growth missing"
            )
        if (
            fundamentals.profit_growth is None
            or fundamentals.profit_growth < self.settings.min_profit_growth
        ):
            reasons.append(
                f"profit growth check failed: {fundamentals.profit_growth} < {self.settings.min_profit_growth}"
                if fundamentals.profit_growth is not None
                else "profit growth missing"
            )

        if reasons:
            return StrategyResult(action="HOLD", reasons=reasons)

        return StrategyResult(
            action="BUY",
            reasons=[
                f"indicator score {snapshot.score} passed",
                "fundamentals passed",
            ],
        )

    def evaluate_sell(
        self,
        position: Position,
        snapshot: IndicatorSnapshot,
        current_price: float,
    ) -> StrategyResult:
        reasons: list[str] = []
        pnl = (current_price - position.entry_price) / position.entry_price

        if snapshot.score <= self.settings.sell_signal_score:
            reasons.append(
                f"indicator score {snapshot.score} <= sell threshold {self.settings.sell_signal_score}"
            )
        if pnl <= -self.settings.stop_loss_pct:
            reasons.append(
                f"stop loss hit: pnl {pnl:.2%} <= -{self.settings.stop_loss_pct:.2%}"
            )
        if pnl >= self.settings.take_profit_pct:
            reasons.append(
                f"take profit hit: pnl {pnl:.2%} >= {self.settings.take_profit_pct:.2%}"
            )

        if reasons:
            return StrategyResult(action="SELL", reasons=reasons)

        return StrategyResult(action="HOLD", reasons=["position still within long-term hold rules"])

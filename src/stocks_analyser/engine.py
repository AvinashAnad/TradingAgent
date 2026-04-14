from __future__ import annotations

from datetime import datetime, timezone

from stocks_analyser.config import Settings
from stocks_analyser.data.tickertape_client import TickertapeClient
from stocks_analyser.data.yfinance_provider import YFinanceProvider
from stocks_analyser.indicators import build_snapshot
from stocks_analyser.models import AnalysisResult, DecisionLog, Position, StockFundamentals
from stocks_analyser.storage import SQLiteStore
from stocks_analyser.strategy import Strategy


class StockAnalyserEngine:
    def __init__(
        self,
        settings: Settings,
        tickertape_client: TickertapeClient,
        price_provider: YFinanceProvider,
        store: SQLiteStore,
        strategy: Strategy,
    ) -> None:
        self.settings = settings
        self.tickertape_client = tickertape_client
        self.price_provider = price_provider
        self.store = store
        self.strategy = strategy

    def run_cycle(self) -> dict[str, int]:
        timestamp = datetime.now(timezone.utc)
        fundamentals = self.tickertape_client.fetch_fundamentals(max_stocks=self.settings.max_stocks)
        fundamentals_by_symbol = {f.symbol: f for f in fundamentals}

        open_positions = {p.symbol: p for p in self.store.get_open_positions()}
        symbols = set(fundamentals_by_symbol.keys()) | set(open_positions.keys())

        counts = {"BUY": 0, "SELL": 0, "HOLD": 0, "SKIP": 0}

        for symbol in sorted(symbols):
            fund = fundamentals_by_symbol.get(symbol)
            if fund is None:
                fund = StockFundamentals(symbol=symbol, name=symbol)

            try:
                ohlc = self.price_provider.get_ohlc(symbol)
                snapshot = build_snapshot(ohlc)
            except Exception as exc:
                counts["SKIP"] += 1
                self.store.log_decision(
                    DecisionLog(
                        symbol=symbol,
                        action="SKIP",
                        timestamp=timestamp,
                        price=0.0,
                        score=0,
                        reasons=[f"data unavailable: {exc}"],
                    )
                )
                continue

            price = snapshot.close
            action = "HOLD"
            reasons: list[str] = []

            if symbol in open_positions:
                sell_result = self.strategy.evaluate_sell(open_positions[symbol], snapshot, price)
                action = sell_result.action
                reasons = sell_result.reasons
                if action == "SELL":
                    self.store.close_position(symbol)
            else:
                buy_result = self.strategy.evaluate_buy(fund, snapshot)
                action = buy_result.action
                reasons = buy_result.reasons
                if action == "BUY":
                    self.store.upsert_position(
                        Position(
                            symbol=symbol,
                            quantity=1.0,
                            entry_price=price,
                            entry_time=timestamp,
                        )
                    )

            result = AnalysisResult(
                symbol=symbol,
                name=fund.name,
                timestamp=timestamp,
                price=price,
                snapshot=snapshot,
                fundamentals=fund,
                action=action,
                reasons=reasons,
            )
            self.store.save_signal(result)
            self.store.log_decision(
                DecisionLog(
                    symbol=symbol,
                    action=action,
                    timestamp=timestamp,
                    price=price,
                    score=snapshot.score,
                    reasons=reasons,
                )
            )
            counts[action] = counts.get(action, 0) + 1

        return counts


def build_engine(settings: Settings) -> StockAnalyserEngine:
    return StockAnalyserEngine(
        settings=settings,
        tickertape_client=TickertapeClient(settings),
        price_provider=YFinanceProvider(),
        store=SQLiteStore(settings.sqlite_path),
        strategy=Strategy(settings),
    )

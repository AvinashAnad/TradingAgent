from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from stocks_analyser.config import Settings
from stocks_analyser.data.dhan_adapter import DhanLiveDataAdapter
from stocks_analyser.data.tickertape_client import TickertapeClient
from stocks_analyser.data.yfinance_provider import YFinanceProvider
from stocks_analyser.indicators import build_snapshot
from stocks_analyser.llm.nvidia_crosscheck import NvidiaHypothesisVerifier
from stocks_analyser.models import AnalysisResult, CrossCheckResult, DecisionLog, ExecutionLog, Position, StockFundamentals
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
        broker_adapter: Optional[DhanLiveDataAdapter] = None,
        cross_checker: Optional[NvidiaHypothesisVerifier] = None,
    ) -> None:
        self.settings = settings
        self.tickertape_client = tickertape_client
        self.price_provider = price_provider
        self.store = store
        self.strategy = strategy
        self.broker_adapter = broker_adapter
        self.cross_checker = cross_checker

    @property
    def _mode(self) -> str:
        return self.settings.app_mode.strip().lower() or "dev"

    @property
    def _is_prod_mode(self) -> bool:
        return self._mode == "prod"

    def _log_execution(
        self,
        symbol: str,
        action: str,
        execution_type: str,
        status: str,
        message: str,
        timestamp: datetime,
        broker_order_id: Optional[str] = None,
    ) -> None:
        self.store.log_execution(
            ExecutionLog(
                symbol=symbol,
                action=action,
                timestamp=timestamp,
                mode=self._mode,
                execution_type=execution_type,
                status=status,
                message=message,
                broker_order_id=broker_order_id,
            )
        )

    def _check_broker_api_state(self, timestamp: datetime) -> None:
        if self.broker_adapter is None:
            self._log_execution(
                symbol="SYSTEM",
                action="API_CHECK",
                execution_type="BROKER",
                status="SKIP",
                message="broker adapter unavailable",
                timestamp=timestamp,
            )
            return

        ok, message = self.broker_adapter.check_api_state()
        self._log_execution(
            symbol="SYSTEM",
            action="API_CHECK",
            execution_type="BROKER",
            status="SUCCESS" if ok else "FAILED",
            message=message,
            timestamp=timestamp,
        )

    def _execute_trade(self, symbol: str, action: str, timestamp: datetime) -> bool:
        quantity = max(1, int(self.settings.default_trade_quantity))

        if not self._is_prod_mode:
            self._log_execution(
                symbol=symbol,
                action=action,
                execution_type="PAPER",
                status="SUCCESS",
                message=f"paper {action.lower()} simulated with quantity={quantity}",
                timestamp=timestamp,
            )
            return True

        if self.broker_adapter is None:
            self._log_execution(
                symbol=symbol,
                action=action,
                execution_type="LIVE",
                status="FAILED",
                message="live execution unavailable: broker adapter missing",
                timestamp=timestamp,
            )
            return False

        ok, message, order_id = self.broker_adapter.place_market_order_by_symbol(
            symbol=symbol,
            side=action,
            quantity=quantity,
        )
        self._log_execution(
            symbol=symbol,
            action=action,
            execution_type="LIVE",
            status="SUCCESS" if ok else "FAILED",
            message=message,
            timestamp=timestamp,
            broker_order_id=order_id,
        )
        return ok

    def _cross_check(
        self,
        symbol: str,
        fund: StockFundamentals,
        action: str,
        reasons: list[str],
        snapshot,
        has_open_position: bool,
    ) -> Optional[CrossCheckResult]:
        if self.cross_checker is None:
            return None

        try:
            return self.cross_checker.cross_check(
                symbol=symbol,
                name=fund.name,
                statistical_action=action,
                statistical_reasons=reasons,
                snapshot=snapshot,
                fundamentals=fund,
                has_open_position=has_open_position,
            )
        except Exception:
            return None

    def run_cycle(self) -> dict[str, int]:
        timestamp = datetime.now(timezone.utc)
        self._check_broker_api_state(timestamp)

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
            has_open_position = symbol in open_positions

            if has_open_position:
                sell_result = self.strategy.evaluate_sell(open_positions[symbol], snapshot, price)
                action = sell_result.action
                reasons = sell_result.reasons
                if action == "SELL":
                    if self._execute_trade(symbol=symbol, action="SELL", timestamp=timestamp):
                        self.store.close_position(symbol)
                    else:
                        reasons = [*reasons, "execution failed; position remains open"]
            else:
                buy_result = self.strategy.evaluate_buy(fund, snapshot)
                action = buy_result.action
                reasons = buy_result.reasons
                if action == "BUY":
                    if self._execute_trade(symbol=symbol, action="BUY", timestamp=timestamp):
                        self.store.upsert_position(
                            Position(
                                symbol=symbol,
                                quantity=float(max(1, int(self.settings.default_trade_quantity))),
                                entry_price=price,
                                entry_time=timestamp,
                            )
                        )
                    else:
                        reasons = [*reasons, "execution failed; position not opened"]

            cross_check = self._cross_check(
                symbol=symbol,
                fund=fund,
                action=action,
                reasons=reasons,
                snapshot=snapshot,
                has_open_position=has_open_position,
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
                llm_action=cross_check.action if cross_check else None,
                llm_confidence=cross_check.confidence if cross_check else None,
                llm_rationale=cross_check.rationale if cross_check else None,
                llm_provider=cross_check.provider if cross_check else None,
                llm_model=cross_check.model if cross_check else None,
                llm_mode=cross_check.mode if cross_check else None,
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
                    llm_action=cross_check.action if cross_check else None,
                    llm_confidence=cross_check.confidence if cross_check else None,
                    llm_rationale=cross_check.rationale if cross_check else None,
                    llm_provider=cross_check.provider if cross_check else None,
                    llm_model=cross_check.model if cross_check else None,
                    llm_mode=cross_check.mode if cross_check else None,
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
        broker_adapter=DhanLiveDataAdapter(settings),
        cross_checker=NvidiaHypothesisVerifier(settings),
    )

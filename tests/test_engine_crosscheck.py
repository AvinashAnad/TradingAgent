from __future__ import annotations

import sys
from pathlib import Path
import tempfile
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from stocks_analyser.config import Settings
from stocks_analyser.engine import StockAnalyserEngine
from stocks_analyser.models import CrossCheckResult, StockFundamentals
from stocks_analyser.storage import SQLiteStore
from stocks_analyser.strategy import StrategyResult


class FakeTickertapeClient:
    def fetch_fundamentals(self, max_stocks: int | None = None) -> list[StockFundamentals]:
        return [
            StockFundamentals(
                symbol="TCS",
                name="TCS",
                pe_ratio=20.0,
                promoter_holding=60.0,
                revenue_growth=10.0,
                profit_growth=11.0,
            )
        ]


class FakePriceProvider:
    def get_ohlc(self, symbol: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
        prices = [100 + i * 0.8 for i in range(80)]
        return pd.DataFrame(
            {
                "open": prices,
                "high": [p + 1 for p in prices],
                "low": [p - 1 for p in prices],
                "close": prices,
                "volume": [1000 for _ in prices],
            }
        )


class FakeStrategy:
    def evaluate_buy(self, fundamentals, snapshot) -> StrategyResult:  # type: ignore[no-untyped-def]
        return StrategyResult(action="BUY", reasons=["statistical buy"])

    def evaluate_sell(self, position, snapshot, current_price) -> StrategyResult:  # type: ignore[no-untyped-def]
        return StrategyResult(action="HOLD", reasons=["hold"])


class FakeVerifier:
    def cross_check(
        self,
        symbol: str,
        name: str,
        statistical_action: str,
        statistical_reasons: list[str],
        snapshot,
        fundamentals,
        has_open_position: bool,
    ) -> CrossCheckResult:
        _ = symbol, name, statistical_action, statistical_reasons, snapshot, fundamentals, has_open_position
        return CrossCheckResult(
            action="HOLD",
            confidence=0.74,
            rationale="llm audit disagrees",
            provider="nvidia",
            model="mock-model",
            mode="audit_only",
        )


def make_settings(sqlite_path: str) -> Settings:
    return Settings(
        app_mode="test",
        tickertape_base_url="https://api.tickertape.in",
        tickertape_timeout_seconds=20,
        tickertape_page_size=500,
        max_stocks=1,
        schedule_interval_minutes=60,
        min_signal_score=3,
        max_pe=40.0,
        min_promoter_holding=35.0,
        min_revenue_growth=0.0,
        min_profit_growth=0.0,
        sell_signal_score=1,
        stop_loss_pct=0.15,
        take_profit_pct=0.35,
        dhan_client_id="",
        dhan_access_token="",
        dhan_base_url="https://api.dhan.co",
        dhan_health_endpoint="/fundlimit",
        dhan_order_endpoint="/orders",
        dhan_exchange_segment="NSE_EQ",
        dhan_product_type="CNC",
        dhan_order_type="MARKET",
        dhan_validity="DAY",
        dhan_symbol_security_map="{}",
        default_trade_quantity=1,
        sqlite_path=sqlite_path,
        llm_crosscheck_mode="audit_only",
        nvidia_api_key="test-key",
        nvidia_base_url="https://example.test/v1/chat/completions",
        nvidia_model="mock-model",
        nvidia_timeout_seconds=20,
        nvidia_temperature=0.1,
        nvidia_max_tokens=200,
    )


class EngineCrossCheckAuditTest(unittest.TestCase):
    def test_audit_mode_logs_llm_fields_without_overriding_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = str(Path(tmp_dir) / "engine_test.db")
            settings = make_settings(sqlite_path=db_path)
            store = SQLiteStore(db_path)

            engine = StockAnalyserEngine(
                settings=settings,
                tickertape_client=FakeTickertapeClient(),
                price_provider=FakePriceProvider(),
                store=store,
                strategy=FakeStrategy(),
                cross_checker=FakeVerifier(),
            )

            counts = engine.run_cycle()
            self.assertEqual(counts.get("BUY"), 1)

            rows = store.latest_decisions(limit=1)
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row["action"], "BUY")
            self.assertEqual(row["llm_action"], "HOLD")
            self.assertAlmostEqual(float(row["llm_confidence"]), 0.74)
            self.assertEqual(row["llm_mode"], "audit_only")

            positions = store.get_open_positions()
            self.assertEqual(len(positions), 1)
            self.assertEqual(positions[0].symbol, "TCS")


if __name__ == "__main__":
    unittest.main()

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
from stocks_analyser.models import StockFundamentals
from stocks_analyser.storage import SQLiteStore
from stocks_analyser.strategy import StrategyResult


class FakeTickertapeClient:
    def fetch_fundamentals(self, max_stocks: int | None = None) -> list[StockFundamentals]:
        return [
            StockFundamentals(
                symbol="TCS",
                name="TCS",
                pe_ratio=22.0,
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
        return StrategyResult(action="BUY", reasons=["buy rule passed"])

    def evaluate_sell(self, position, snapshot, current_price) -> StrategyResult:  # type: ignore[no-untyped-def]
        return StrategyResult(action="HOLD", reasons=["hold"])


class FakeBrokerAdapter:
    def __init__(self, api_ok: bool = True, order_ok: bool = True) -> None:
        self.api_ok = api_ok
        self.order_ok = order_ok
        self.place_calls: list[tuple[str, str, int]] = []

    def check_api_state(self) -> tuple[bool, str]:
        if self.api_ok:
            return True, "API state ok (200)"
        return False, "API state failed (401)"

    def place_market_order_by_symbol(
        self,
        symbol: str,
        side: str,
        quantity: int,
    ) -> tuple[bool, str, str | None]:
        self.place_calls.append((symbol, side, quantity))
        if self.order_ok:
            return True, "live order submitted", "OID-123"
        return False, "live order failed", None


def make_settings(app_mode: str, sqlite_path: str) -> Settings:
    return Settings(
        app_mode=app_mode,
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
        dhan_client_id="client",
        dhan_access_token="token",
        dhan_base_url="https://api.dhan.co",
        dhan_health_endpoint="/fundlimit",
        dhan_order_endpoint="/orders",
        dhan_exchange_segment="NSE_EQ",
        dhan_product_type="CNC",
        dhan_order_type="MARKET",
        dhan_validity="DAY",
        dhan_symbol_security_map='{"TCS": "11536"}',
        default_trade_quantity=1,
        sqlite_path=sqlite_path,
        llm_crosscheck_mode="off",
        nvidia_api_key="",
        nvidia_base_url="https://integrate.api.nvidia.com/v1/chat/completions",
        nvidia_model="meta/llama-3.1-70b-instruct",
        nvidia_timeout_seconds=20,
        nvidia_temperature=0.1,
        nvidia_max_tokens=300,
    )


class EngineModeTest(unittest.TestCase):
    def test_dev_mode_uses_paper_execution_and_checks_api(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = str(Path(tmp_dir) / "dev_mode.db")
            store = SQLiteStore(db_path)
            broker = FakeBrokerAdapter(api_ok=True, order_ok=True)

            engine = StockAnalyserEngine(
                settings=make_settings(app_mode="dev", sqlite_path=db_path),
                tickertape_client=FakeTickertapeClient(),
                price_provider=FakePriceProvider(),
                store=store,
                strategy=FakeStrategy(),
                broker_adapter=broker,
                cross_checker=None,
            )

            counts = engine.run_cycle()
            self.assertEqual(counts.get("BUY"), 1)
            self.assertEqual(broker.place_calls, [])
            self.assertEqual(len(store.get_open_positions()), 1)

            rows = store.latest_executions(limit=5)
            self.assertEqual(rows[0]["action"], "BUY")
            self.assertEqual(rows[0]["execution_type"], "PAPER")
            self.assertEqual(rows[1]["action"], "API_CHECK")
            self.assertEqual(rows[1]["status"], "SUCCESS")

    def test_prod_mode_places_live_order_and_logs_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = str(Path(tmp_dir) / "prod_mode.db")
            store = SQLiteStore(db_path)
            broker = FakeBrokerAdapter(api_ok=True, order_ok=True)

            engine = StockAnalyserEngine(
                settings=make_settings(app_mode="prod", sqlite_path=db_path),
                tickertape_client=FakeTickertapeClient(),
                price_provider=FakePriceProvider(),
                store=store,
                strategy=FakeStrategy(),
                broker_adapter=broker,
                cross_checker=None,
            )

            counts = engine.run_cycle()
            self.assertEqual(counts.get("BUY"), 1)
            self.assertEqual(len(broker.place_calls), 1)
            self.assertEqual(broker.place_calls[0], ("TCS", "BUY", 1))
            self.assertEqual(len(store.get_open_positions()), 1)

            rows = store.latest_executions(limit=5)
            self.assertEqual(rows[0]["action"], "BUY")
            self.assertEqual(rows[0]["execution_type"], "LIVE")
            self.assertEqual(rows[0]["status"], "SUCCESS")
            self.assertEqual(rows[0]["broker_order_id"], "OID-123")


if __name__ == "__main__":
    unittest.main()

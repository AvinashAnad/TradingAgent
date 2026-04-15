from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import Mock, patch
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from stocks_analyser.config import Settings
from stocks_analyser.llm.nvidia_crosscheck import NvidiaHypothesisVerifier
from stocks_analyser.models import IndicatorSnapshot, StockFundamentals


def make_settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "app_mode": "test",
        "tickertape_base_url": "https://api.tickertape.in",
        "tickertape_timeout_seconds": 20,
        "tickertape_page_size": 500,
        "max_stocks": 1,
        "schedule_interval_minutes": 60,
        "min_signal_score": 3,
        "max_pe": 40.0,
        "min_promoter_holding": 35.0,
        "min_revenue_growth": 0.0,
        "min_profit_growth": 0.0,
        "sell_signal_score": 1,
        "stop_loss_pct": 0.15,
        "take_profit_pct": 0.35,
        "dhan_client_id": "",
        "dhan_access_token": "",
        "dhan_base_url": "https://api.dhan.co",
        "dhan_health_endpoint": "/fundlimit",
        "dhan_order_endpoint": "/orders",
        "dhan_exchange_segment": "NSE_EQ",
        "dhan_product_type": "CNC",
        "dhan_order_type": "MARKET",
        "dhan_validity": "DAY",
        "dhan_symbol_security_map": "{}",
        "default_trade_quantity": 1,
        "sqlite_path": "test.db",
        "llm_crosscheck_mode": "audit_only",
        "nvidia_api_key": "test-key",
        "nvidia_base_url": "https://example.test/v1/chat/completions",
        "nvidia_model": "mock-model",
        "nvidia_timeout_seconds": 20,
        "nvidia_temperature": 0.1,
        "nvidia_max_tokens": 200,
    }
    base.update(overrides)
    return Settings(**base)


def make_snapshot() -> IndicatorSnapshot:
    return IndicatorSnapshot(
        close=100.0,
        sma20=98.0,
        sma50=95.0,
        ema20=99.0,
        ema50=96.0,
        macd=1.2,
        macd_signal=0.9,
        rsi14=58.0,
        bb_upper=105.0,
        bb_middle=100.0,
        bb_lower=95.0,
        score=4,
    )


class NvidiaCrossCheckTest(unittest.TestCase):
    @patch("stocks_analyser.llm.nvidia_crosscheck.requests.post")
    def test_cross_check_parses_json_response(self, mock_post: Mock) -> None:
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"action":"SELL","confidence":0.82,"rationale":"Momentum divergence"}'
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        verifier = NvidiaHypothesisVerifier(make_settings())
        result = verifier.cross_check(
            symbol="TCS",
            name="Tata Consultancy Services",
            statistical_action="BUY",
            statistical_reasons=["statistical buy"],
            snapshot=make_snapshot(),
            fundamentals=StockFundamentals(symbol="TCS", name="TCS", pe_ratio=22.0),
            has_open_position=False,
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.action, "SELL")
        self.assertAlmostEqual(result.confidence, 0.82)
        self.assertEqual(result.provider, "nvidia")

    @patch("stocks_analyser.llm.nvidia_crosscheck.requests.post")
    def test_cross_check_skips_when_mode_off(self, mock_post: Mock) -> None:
        verifier = NvidiaHypothesisVerifier(make_settings(llm_crosscheck_mode="off"))
        result = verifier.cross_check(
            symbol="TCS",
            name="TCS",
            statistical_action="BUY",
            statistical_reasons=["statistical buy"],
            snapshot=make_snapshot(),
            fundamentals=StockFundamentals(symbol="TCS", name="TCS"),
            has_open_position=False,
        )

        self.assertIsNone(result)
        mock_post.assert_not_called()


if __name__ == "__main__":
    unittest.main()

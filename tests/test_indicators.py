from __future__ import annotations

import sys
from pathlib import Path
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from stocks_analyser.indicators import build_snapshot


class IndicatorsTest(unittest.TestCase):
    def test_build_snapshot_returns_expected_shape(self) -> None:
        prices = [100 + i * 0.8 for i in range(80)]
        df = pd.DataFrame(
            {
                "open": prices,
                "high": [p + 1 for p in prices],
                "low": [p - 1 for p in prices],
                "close": prices,
                "volume": [1000 for _ in prices],
            }
        )

        snapshot = build_snapshot(df)
        self.assertGreater(snapshot.sma20, 0)
        self.assertGreater(snapshot.sma50, 0)
        self.assertGreaterEqual(snapshot.score, 0)
        self.assertLessEqual(snapshot.score, 5)

    def test_build_snapshot_needs_minimum_points(self) -> None:
        prices = [100 + i for i in range(20)]
        df = pd.DataFrame(
            {
                "open": prices,
                "high": [p + 1 for p in prices],
                "low": [p - 1 for p in prices],
                "close": prices,
                "volume": [1000 for _ in prices],
            }
        )
        with self.assertRaises(ValueError):
            build_snapshot(df)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from unittest.mock import patch
import unittest

import pandas as pd

from stocks_analyser.data.yfinance_provider import YFinanceProvider


class YFinanceProviderTest(unittest.TestCase):
    @patch("stocks_analyser.data.yfinance_provider.yf.download")
    def test_get_ohlc_flattens_multiindex_columns(self, mock_download) -> None:
        columns = pd.MultiIndex.from_tuples(
            [
                ("Adj Close", "TCS.NS"),
                ("Close", "TCS.NS"),
                ("High", "TCS.NS"),
                ("Low", "TCS.NS"),
                ("Open", "TCS.NS"),
                ("Volume", "TCS.NS"),
            ],
            names=["Price", "Ticker"],
        )
        mock_download.return_value = pd.DataFrame(
            [[100.0, 101.0, 103.0, 99.0, 100.5, 12345]],
            columns=columns,
        )

        provider = YFinanceProvider()
        ohlc = provider.get_ohlc("TCS", period="1mo", interval="1d")

        self.assertEqual(list(ohlc.columns), ["open", "high", "low", "close", "volume"])
        self.assertEqual(float(ohlc.iloc[0]["close"]), 101.0)


if __name__ == "__main__":
    unittest.main()
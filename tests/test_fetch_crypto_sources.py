from __future__ import annotations

import types
import unittest

import pandas as pd

import src.data.fetch_crypto as fetch_crypto


def _candles(count: int = 25):
    base_ts = 1_700_000_000_000
    return [
        [base_ts + i * 60_000, 10 + i, 11 + i, 9 + i, 10.5 + i, 100 + i]
        for i in range(count)
    ]


def _make_ccxt(behaviors: dict):
    def exchange_class(name: str):
        class FakeExchange:
            def __init__(self, config):
                self.config = config
                self.markets = None

            def load_markets(self):
                behavior = behaviors.get(name, {})
                load_error = behavior.get("load_error")
                if load_error:
                    raise load_error
                self.markets = {
                    market["symbol"]: market
                    for market in behavior.get("markets", [])
                    if market.get("symbol")
                }
                return self.markets

            def fetch_markets(self):
                return behaviors.get(name, {}).get("fetch_markets", [])

            def set_markets(self, markets):
                self.markets = {
                    market["symbol"]: market
                    for market in markets
                    if market.get("symbol")
                }

            def fetch_ohlcv(self, symbol, timeframe, limit=100):
                ohlcv = behaviors.get(name, {}).get("ohlcv", {})
                if symbol not in ohlcv:
                    raise ValueError(f"{name} missing {symbol}")
                return ohlcv[symbol][:limit]

            def fetch_ticker(self, symbol):
                tickers = behaviors.get(name, {}).get("tickers", {})
                if symbol not in tickers:
                    raise ValueError(f"{name} missing ticker {symbol}")
                return tickers[symbol]

        return FakeExchange

    names = ["okx", "bybit", "kraken", "binance", "binanceusdm"]
    return types.SimpleNamespace(**{name: exchange_class(name) for name in names})


class FetchCryptoSourcesTest(unittest.TestCase):
    def setUp(self):
        self.original_ccxt = fetch_crypto.ccxt
        fetch_crypto._exchange_instances.clear()
        fetch_crypto._markets_loaded.clear()

    def tearDown(self):
        fetch_crypto.ccxt = self.original_ccxt
        fetch_crypto._exchange_instances.clear()
        fetch_crypto._markets_loaded.clear()

    def test_okx_filters_invalid_markets_after_load_markets_type_error(self):
        behaviors = {
            "okx": {
                "load_error": TypeError("'<' not supported between instances of 'NoneType' and 'str'"),
                "fetch_markets": [
                    {"id": None, "symbol": None, "spot": False, "type": "future"},
                    {"id": "BTC-USDT", "symbol": "BTC/USDT", "spot": True, "type": "spot"},
                ],
                "ohlcv": {"BTC/USDT": _candles()},
            }
        }
        fetch_crypto.ccxt = _make_ccxt(behaviors)

        result = fetch_crypto.fetch_crypto_data_with_metadata("BTC/USDT", timeframe="4h")

        self.assertEqual(result.exchange, "okx")
        self.assertEqual(result.market_type, "spot")
        self.assertEqual(result.resolved_symbol, "BTC/USDT")
        self.assertFalse(result.fallback_used)
        self.assertEqual(result.candles, 25)

    def test_rune_falls_back_to_bybit_spot(self):
        behaviors = {
            "okx": {"markets": [{"id": "BTC-USDT", "symbol": "BTC/USDT", "spot": True, "type": "spot"}]},
            "bybit": {
                "markets": [{"id": "RUNEUSDT", "symbol": "RUNE/USDT", "spot": True, "type": "spot"}],
                "ohlcv": {"RUNE/USDT": _candles()},
            },
        }
        fetch_crypto.ccxt = _make_ccxt(behaviors)

        result = fetch_crypto.fetch_crypto_data_with_metadata("RUNE/USDT", timeframe="4h")

        self.assertEqual(result.exchange, "bybit")
        self.assertEqual(result.market_type, "spot")
        self.assertEqual(result.resolved_symbol, "RUNE/USDT")
        self.assertTrue(result.fallback_used)
        self.assertEqual(result.attempts[0]["stage"], "resolve_symbol")

    def test_xmr_falls_back_to_kraken_spot(self):
        behaviors = {
            "okx": {"markets": []},
            "bybit": {"markets": []},
            "kraken": {
                "markets": [{"id": "XMR/USDT", "symbol": "XMR/USDT", "spot": True, "type": "spot"}],
                "ohlcv": {"XMR/USDT": _candles()},
            },
        }
        fetch_crypto.ccxt = _make_ccxt(behaviors)

        result = fetch_crypto.fetch_crypto_data_with_metadata("XMR/USDT", timeframe="4h")

        self.assertEqual(result.exchange, "kraken")
        self.assertEqual(result.market_type, "spot")
        self.assertEqual(result.resolved_symbol, "XMR/USDT")
        self.assertTrue(result.fallback_used)

    def test_quote_fallback_uses_usd_when_usdt_is_unavailable(self):
        behaviors = {
            "okx": {
                "markets": [{"id": "FOO-USD", "symbol": "FOO/USD", "spot": True, "type": "spot"}],
                "ohlcv": {"FOO/USD": _candles()},
            },
        }
        fetch_crypto.ccxt = _make_ccxt(behaviors)

        result = fetch_crypto.fetch_crypto_data_with_metadata("FOO/USDT", timeframe="4h")

        self.assertEqual(result.exchange, "okx")
        self.assertEqual(result.resolved_symbol, "FOO/USD")
        self.assertTrue(result.fallback_used)

    def test_get_crypto_data_stays_dataframe_compatible(self):
        behaviors = {
            "okx": {
                "markets": [{"id": "BTC-USDT", "symbol": "BTC/USDT", "spot": True, "type": "spot"}],
                "ohlcv": {"BTC/USDT": _candles()},
            },
        }
        fetch_crypto.ccxt = _make_ccxt(behaviors)

        df = fetch_crypto.get_crypto_data("BTC/USDT", timeframe="4h")

        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(list(df.columns), ["open", "high", "low", "close", "volume"])
        self.assertEqual(len(df), 25)


if __name__ == "__main__":
    unittest.main()

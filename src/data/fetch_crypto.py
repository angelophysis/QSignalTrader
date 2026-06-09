from __future__ import annotations

import ccxt
import pandas as pd


def get_crypto_data(
    symbol: str = "BTC/USDT",
    exchange_name: str = "binance",
    timeframe: str = "1h",
    limit: int = 100,
) -> pd.DataFrame:
    exchange_class = getattr(ccxt, exchange_name)
    exchange = exchange_class({"enableRateLimit": True})

    ohlcv = exchange.fetch_ohlcv(symbol, timeframe.lower(), limit=limit)

    df = pd.DataFrame(
        ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df

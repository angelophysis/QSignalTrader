from __future__ import annotations

import ccxt
import pandas as pd

_CRYPTO_EXCHANGES = ["okx", "bybit", "kraken", "binance"]


def _get_exchange(exchange_name: str = "okx"):
    exchange_class = getattr(ccxt, exchange_name)
    return exchange_class({"enableRateLimit": True, "timeout": 8000})


def get_crypto_data(
    symbol: str = "BTC/USDT",
    exchange_name: str = "okx",
    timeframe: str = "1h",
    limit: int = 100,
) -> pd.DataFrame:
    last_error = None
    exchanges_to_try = [exchange_name] + [e for e in _CRYPTO_EXCHANGES if e != exchange_name]

    for ex_name in exchanges_to_try:
        try:
            exchange = _get_exchange(ex_name)
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe.lower(), limit=limit)

            df = pd.DataFrame(
                ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            return df
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(
        f"Todas as exchanges falharam para {symbol} ({timeframe}): {last_error}"
    )

from __future__ import annotations


def is_btc(symbol: str) -> bool:
    s = symbol.strip().upper().replace(" ", "")
    return s in ("BTC", "BTCUSDT", "BTC/USDT", "BTC-USD", "XBTUSD", "XBT/USD")


def normalizar_symbol_btc(symbol: str) -> str:
    s = symbol.strip().upper().replace(" ", "")
    if s in ("BTC", "BTCUSDT", "BTC-USD", "XBTUSD", "XBT/USD"):
        return "BTC/USDT"
    return symbol


ATR_PERCENT_PERIOD = 14
ATR_PERCENT_MA_PERIOD = 50
ATR_PERCENT_SLOPE = 5

BB_PERIOD = 20
BB_STD = 2
BB_PERCENTILE_WINDOW = 252

RV_WINDOWS = [7, 30, 90]
RV_ANNUAL_FACTOR = 365

DVOL_SLOPE_3 = 3
DVOL_SLOPE_7 = 7
DVOL_MA_20 = 20
DVOL_MA_50 = 50
DVOL_LOOKBACK_DAYS = 365

IV_RANK_WINDOW = 365

RSI_BAIXA_FORTE = 42

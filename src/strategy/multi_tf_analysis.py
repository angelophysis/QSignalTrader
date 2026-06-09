from __future__ import annotations

import math

import numpy as np
import pandas as pd

from src.data.fetch_crypto import get_crypto_data
from src.data.yfinance_handler import YahooFinanceDataHandler
from src.indicators.technicals import add_atr, add_emas, add_rsi
from src.volatility.volatility_config import RSI_BAIXA_FORTE

CRYPTO_TIMEFRAMES = ["15m", "1h", "4h", "1D", "1W"]
CRYPTO_LIMITS = {"15m": 200, "1h": 200, "4h": 200, "1D": 500, "1W": 500}

STOCK_TIMEFRAMES = ["1d", "5d", "1wk"]
STOCK_PERIODS = {"1d": "3mo", "5d": "6mo", "1wk": "max"}

RSI_THRESHOLD = 58


def _safe_float(value: float | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, (int, float)):
        if math.isnan(value) or math.isinf(value):
            return None
        return round(float(value), 2)
    return None


def _safe_scalar(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, (int, float)):
        if math.isnan(value) or math.isinf(value):
            return None
        return float(value)
    return None


def _analisar_dataframe(df: pd.DataFrame) -> dict:
    if df.empty or len(df) < 21:
        return {
            "alinhamento_emas": False,
            "rsi": None,
            "rsi_forte": False,
            "atr": None,
            "tendencia_alta": False,
            "ultima_tendencia_alta": False,
            "alinhamento_emas_baixa": False,
            "rsi_fraco": False,
            "tendencia_baixa": False,
            "ultima_tendencia_baixa": False,
        }

    df = add_emas(df)
    df = add_rsi(df)
    df = add_atr(df)

    latest = df.iloc[-1]
    ema_8 = _safe_scalar(latest.get("ema_8"))
    ema_21 = _safe_scalar(latest.get("ema_21"))
    ema_50 = _safe_scalar(latest.get("ema_50"))

    alinhamento_emas = False
    if (
        ema_8 is not None
        and ema_21 is not None
        and ema_50 is not None
    ):
        alinhamento_emas = bool(ema_8 > ema_21 > ema_50)

    rsi_val = _safe_scalar(latest.get("rsi"))
    rsi_forte = bool(rsi_val is not None and rsi_val > RSI_THRESHOLD)
    rsi_fraco = bool(rsi_val is not None and rsi_val < RSI_BAIXA_FORTE)

    tendencia_alta = bool(alinhamento_emas and rsi_forte)

    ema_100 = _safe_scalar(latest.get("ema_100"))
    ema_200 = _safe_scalar(latest.get("ema_200"))
    alinhamento_emas_baixa = False
    if (
        ema_8 is not None and ema_21 is not None and ema_50 is not None
        and ema_100 is not None and ema_200 is not None
    ):
        alinhamento_emas_baixa = bool(ema_8 < ema_21 < ema_50 < ema_100 < ema_200)

    tendencia_baixa = bool(alinhamento_emas_baixa and rsi_fraco)

    prev = df.iloc[-2] if len(df) > 1 else latest
    prev_ema_8 = _safe_scalar(prev.get("ema_8"))
    prev_ema_21 = _safe_scalar(prev.get("ema_21"))
    prev_ema_50 = _safe_scalar(prev.get("ema_50"))
    prev_rsi = _safe_scalar(prev.get("rsi"))

    prev_alinhamento = False
    if (
        prev_ema_8 is not None
        and prev_ema_21 is not None
        and prev_ema_50 is not None
    ):
        prev_alinhamento = bool(prev_ema_8 > prev_ema_21 > prev_ema_50)
    prev_rsi_forte = bool(prev_rsi is not None and prev_rsi > RSI_THRESHOLD)
    prev_rsi_fraco = bool(prev_rsi is not None and prev_rsi < RSI_BAIXA_FORTE)
    prev_tendencia_alta = bool(prev_alinhamento and prev_rsi_forte)

    prev_ema_100 = _safe_scalar(prev.get("ema_100"))
    prev_ema_200 = _safe_scalar(prev.get("ema_200"))
    prev_alinhamento_baixa = False
    if (
        prev_ema_8 is not None and prev_ema_21 is not None and prev_ema_50 is not None
        and prev_ema_100 is not None and prev_ema_200 is not None
    ):
        prev_alinhamento_baixa = bool(prev_ema_8 < prev_ema_21 < prev_ema_50 < prev_ema_100 < prev_ema_200)
    prev_tendencia_baixa = bool(prev_alinhamento_baixa and prev_rsi_fraco)

    return {
        "alinhamento_emas": alinhamento_emas,
        "rsi": _safe_float(rsi_val),
        "rsi_forte": rsi_forte,
        "atr": _safe_float(latest.get("atr")),
        "tendencia_alta": tendencia_alta,
        "ultima_tendencia_alta": prev_tendencia_alta,
        "alinhamento_emas_baixa": alinhamento_emas_baixa,
        "rsi_fraco": rsi_fraco,
        "tendencia_baixa": tendencia_baixa,
        "ultima_tendencia_baixa": prev_tendencia_baixa,
    }


def analisar_confluencia(symbol: str = "BTC/USDT") -> dict:
    estado = {}
    for tf in CRYPTO_TIMEFRAMES:
        try:
            limit = CRYPTO_LIMITS.get(tf, 200)
            df = get_crypto_data(symbol=symbol, timeframe=tf, limit=limit)
            estado[tf] = _analisar_dataframe(df)
        except Exception:
            estado[tf] = {
                "alinhamento_emas": False,
                "rsi": None,
                "rsi_forte": False,
                "atr": None,
                "tendencia_alta": False,
                "ultima_tendencia_alta": False,
                "alinhamento_emas_baixa": False,
                "rsi_fraco": False,
                "tendencia_baixa": False,
                "ultima_tendencia_baixa": False,
            }
    return estado


def analisar_confluencia_stock(symbol: str = "AAPL") -> dict:
    dh = YahooFinanceDataHandler(auto_adjust=True)
    estado = {}

    for tf in STOCK_TIMEFRAMES:
        try:
            yf_interval = "1wk" if tf == "1wk" else "1d"
            period = STOCK_PERIODS.get(tf, "3mo")
            df = dh.fetch_ohlc(ticker=symbol, period=period, interval=yf_interval)
            if df.empty:
                raise ValueError("Sem dados")
            estado[tf] = _analisar_dataframe(df)
        except Exception:
            estado[tf] = {
                "alinhamento_emas": False,
                "rsi": None,
                "rsi_forte": False,
                "atr": None,
                "tendencia_alta": False,
                "ultima_tendencia_alta": False,
                "alinhamento_emas_baixa": False,
                "rsi_fraco": False,
                "tendencia_baixa": False,
                "ultima_tendencia_baixa": False,
            }
    return estado

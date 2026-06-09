from __future__ import annotations

import math

import numpy as np
import pandas as pd

from src.indicators.technicals import add_atr
from src.volatility.volatility_config import (
    ATR_PERCENT_MA_PERIOD,
    ATR_PERCENT_PERIOD,
    ATR_PERCENT_SLOPE,
    BB_PERIOD,
    BB_PERCENTILE_WINDOW,
    BB_STD,
    RV_ANNUAL_FACTOR,
)


def _safe(val) -> float | None:
    if val is None:
        return None
    if isinstance(val, np.generic):
        val = val.item()
    if isinstance(val, (int, float)):
        if math.isnan(val) or math.isinf(val):
            return None
        return round(float(val), 4)
    return None


def calcular_atr_percentual(df: pd.DataFrame) -> dict:
    atr_df = add_atr(df.copy(), period=ATR_PERCENT_PERIOD)
    atr_col = atr_df["atr"]
    close_col = atr_df["close"]

    atr_percent = (atr_col / close_col) * 100
    atr_percent_ma = atr_percent.rolling(ATR_PERCENT_MA_PERIOD).mean()

    latest_atr_pct = _safe(atr_percent.iloc[-1])
    latest_ma = _safe(atr_percent_ma.iloc[-1])
    ratio = round(latest_atr_pct / latest_ma, 4) if latest_atr_pct and latest_ma else None
    slope = None
    if len(atr_percent) > ATR_PERCENT_SLOPE:
        slope = _safe(atr_percent.iloc[-1] - atr_percent.iloc[-1 - ATR_PERCENT_SLOPE])

    return {
        "atr_percent": latest_atr_pct,
        "atr_percent_ma50": latest_ma,
        "atr_percent_ratio": ratio,
        "atr_percent_slope_5": slope,
    }


def calcular_bollinger_bandwidth(df: pd.DataFrame) -> dict:
    close = df["close"]
    ma = close.rolling(BB_PERIOD).mean()
    std = close.rolling(BB_PERIOD).std()
    upper = ma + BB_STD * std
    lower = ma - BB_STD * std

    bandwidth = (upper - lower) / ma
    latest_bw = _safe(bandwidth.iloc[-1])

    percentile = None
    if len(bandwidth) >= BB_PERCENTILE_WINDOW:
        window = bandwidth.iloc[-BB_PERCENTILE_WINDOW:]
        if latest_bw is not None:
            rank = (window < latest_bw).sum()
            percentile = round(float(rank) / len(window) * 100, 1)

    slope = None
    if len(bandwidth) > ATR_PERCENT_SLOPE:
        slope = _safe(bandwidth.iloc[-1] - bandwidth.iloc[-1 - ATR_PERCENT_SLOPE])

    return {
        "bandwidth": latest_bw,
        "bandwidth_percentile": percentile,
        "bandwidth_slope_5": slope,
    }


def calcular_realized_vol(df: pd.DataFrame) -> dict:
    log_ret = np.log(df["close"] / df["close"].shift(1)).dropna()

    result = {}
    for w in [7, 30, 90]:
        if len(log_ret) >= w:
            rv = float(log_ret.rolling(w).std().iloc[-1] * math.sqrt(RV_ANNUAL_FACTOR))
            result[f"rv{w}"] = round(rv, 4)
        else:
            result[f"rv{w}"] = None

    rv7 = result.get("rv7")
    rv30 = result.get("rv30")
    rv90 = result.get("rv90")

    result["rv7_rv30_ratio"] = round(rv7 / rv30, 4) if rv7 and rv30 else None
    result["rv30_rv90_ratio"] = round(rv30 / rv90, 4) if rv30 and rv90 else None

    return result


def calcular_volatilidade_realizada(df: pd.DataFrame) -> dict:
    if df.empty or len(df) < 50:
        return {
            "atr_percent": None, "atr_percent_ma50": None,
            "atr_percent_ratio": None, "atr_percent_slope_5": None,
            "bandwidth": None, "bandwidth_percentile": None, "bandwidth_slope_5": None,
            "rv7": None, "rv30": None, "rv90": None,
            "rv7_rv30_ratio": None, "rv30_rv90_ratio": None,
        }

    atr_metrics = calcular_atr_percentual(df)
    bb_metrics = calcular_bollinger_bandwidth(df)
    rv_metrics = calcular_realized_vol(df)

    return {**atr_metrics, **bb_metrics, **rv_metrics}

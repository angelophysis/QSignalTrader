from __future__ import annotations

import numpy as np
import pandas as pd

from src.indicators.technicals import add_emas, add_rsi


def _safe_float(val):
    if val is None:
        return None
    if isinstance(val, np.generic):
        val = val.item()
    if isinstance(val, (int, float)):
        if np.isnan(val) or np.isinf(val):
            return None
        return float(val)
    return None


def calculate_stock_momentum_score(df: pd.DataFrame) -> dict:
    if df.empty or len(df) < 50:
        return {"momentum_score": 0, "classification": "CONTRA", "reasons": [], "warnings": ["Dados insuficientes"]}

    df = add_rsi(df.copy(), period=14)
    df = add_emas(df.copy(), periods=[8, 21])

    latest = df.iloc[-1]
    rsi = _safe_float(latest.get("rsi"))
    rsi_3 = _safe_float(df["rsi"].iloc[-4]) if len(df) >= 4 else None
    rsi_5 = _safe_float(df["rsi"].iloc[-6]) if len(df) >= 6 else None
    rsi_delta_3 = round(rsi - rsi_3, 1) if rsi is not None and rsi_3 is not None else None
    rsi_delta_5 = round(rsi - rsi_5, 1) if rsi is not None and rsi_5 is not None else None

    close = _safe_float(latest.get("close"))
    close_10 = _safe_float(df["close"].iloc[-11]) if len(df) >= 11 else None
    close_20 = _safe_float(df["close"].iloc[-21]) if len(df) >= 21 else None
    roc_10 = round((close - close_10) / close_10 * 100, 2) if close and close_10 else None
    roc_20 = round((close - close_20) / close_20 * 100, 2) if close and close_20 else None

    ema_8 = _safe_float(latest.get("ema_8"))
    ema_21 = _safe_float(latest.get("ema_21"))
    ema8_above_ema21 = bool(ema_8 and ema_21 and ema_8 > ema_21)

    volume = _safe_float(latest.get("volume"))
    vol_mean_20 = _safe_float(df["volume"].rolling(20).mean().iloc[-1]) if "volume" in df.columns else None
    vol_rel = round(volume / vol_mean_20, 2) if volume and vol_mean_20 else None

    macd_line = None
    macd_signal = None
    macd_hist = None
    if len(df) >= 26:
        ema12 = df["close"].ewm(span=12, adjust=False).mean()
        ema26 = df["close"].ewm(span=26, adjust=False).mean()
        macd_series = ema12 - ema26
        macd_signal_series = macd_series.ewm(span=9, adjust=False).mean()
        macd_hist_series = macd_series - macd_signal_series
        macd_line = _safe_float(macd_series.iloc[-1])
        macd_signal = _safe_float(macd_signal_series.iloc[-1])
        macd_hist = _safe_float(macd_hist_series.iloc[-1])

    score = 0
    reasons = []
    warnings_list = []

    if rsi is not None:
        if rsi >= 60: score += 15; reasons.append("RSI >= 60")
        elif rsi >= 50: score += 10
        elif rsi < 40: score += 2; warnings_list.append("RSI fraco (< 40)")

    if rsi_delta_3 is not None:
        if rsi_delta_3 > 0: score += 10; reasons.append(f"RSI delta 3 positivo ({rsi_delta_3})")
        elif rsi_delta_3 < -3: warnings_list.append(f"RSI delta 3 negativo ({rsi_delta_3})")

    if rsi_delta_5 is not None:
        if rsi_delta_5 > 0: score += 8; reasons.append(f"RSI delta 5 positivo ({rsi_delta_5})")

    if roc_10 is not None:
        if roc_10 > 0: score += 12; reasons.append(f"ROC10 positivo ({roc_10}%)")
        elif roc_10 < -5: warnings_list.append(f"ROC10 negativo ({roc_10}%)")

    if roc_20 is not None:
        if roc_20 > 0: score += 10; reasons.append(f"ROC20 positivo ({roc_20}%)")
        elif roc_20 < -10: warnings_list.append(f"ROC20 muito negativo ({roc_20}%)")

    if ema8_above_ema21: score += 10; reasons.append("EMA8 acima da EMA21")
    else: score += 3; warnings_list.append("EMA8 abaixo da EMA21")

    if vol_rel is not None:
        if vol_rel >= 1.2: score += 10; reasons.append(f"Volume relativo alto ({vol_rel}x)")
        elif vol_rel >= 0.8: score += 5
        else: score += 2; warnings_list.append(f"Volume relativo baixo ({vol_rel}x)")

    if macd_hist is not None:
        if macd_hist > 0: score += 10; reasons.append("MACD histogram positivo")
        elif macd_hist < 0: warnings_list.append("MACD histogram negativo")

    score = min(100, max(0, score))

    if score >= 80: classification = "FORTE"
    elif score >= 60: classification = "FAVORAVEL"
    elif score >= 45: classification = "NEUTRO"
    elif score >= 25: classification = "FRACO"
    else: classification = "CONTRA"

    return {
        "momentum_score": score,
        "rsi": rsi,
        "rsi_delta_3": rsi_delta_3,
        "rsi_delta_5": rsi_delta_5,
        "roc_10": roc_10,
        "roc_20": roc_20,
        "macd_histogram": macd_hist,
        "ema8_above_ema21": ema8_above_ema21,
        "volume_relative": vol_rel,
        "classification": classification,
        "reasons": reasons,
        "warnings": warnings_list,
    }

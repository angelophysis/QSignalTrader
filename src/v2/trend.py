from __future__ import annotations

import numpy as np

from src.indicators.technicals import add_emas
from src.v2.config import MOMENTUM_FAVORABLE, TREND_HEALTHY, TREND_STRONG


def _safe(val):
    if val is None: return None
    if isinstance(val, np.generic): val = val.item()
    if isinstance(val, (int, float)):
        if np.isnan(val) or np.isinf(val): return None
        return float(val)
    return None


def calculate_trend_score(df) -> dict:
    if df is None or df.empty or len(df) < 50:
        return {"trend_score": 0, "classification": "BAIXA_FORTE", "reasons": [], "warnings": ["Dados insuficientes"]}

    df = add_emas(df.copy(), periods=[21, 50, 200])
    latest = df.iloc[-1]
    close = _safe(latest.get("close"))
    ema21 = _safe(latest.get("ema_21"))
    ema50 = _safe(latest.get("ema_50"))
    ema200 = _safe(latest.get("ema_200"))

    price_above_ema21 = close > ema21 if close and ema21 else False
    price_above_ema50 = close > ema50 if close and ema50 else False
    price_above_ema200 = close > ema200 if close and ema200 else False
    ema21_above_50 = ema21 > ema50 if ema21 and ema50 else False
    ema50_above_200 = ema50 > ema200 if ema50 and ema200 else False

    ema21_series = df["ema_21"]
    ema50_series = df["ema_50"]
    slope21 = _safe((ema21_series.iloc[-1] - ema21_series.iloc[-6]) / ema21_series.iloc[-1] * 100) if len(ema21_series) >= 6 else None
    slope50 = _safe((ema50_series.iloc[-1] - ema50_series.iloc[-6]) / ema50_series.iloc[-1] * 100) if len(ema50_series) >= 6 else None

    ret20 = _safe((close - _safe(df["close"].iloc[-21])) / _safe(df["close"].iloc[-21]) * 100) if len(df) >= 21 and close else None
    ret60 = _safe((close - _safe(df["close"].iloc[-61])) / _safe(df["close"].iloc[-61]) * 100) if len(df) >= 61 and close else None

    score = 0
    reasons = []
    warnings_list = []

    score += 15 if price_above_ema21 else 0
    score += 15 if price_above_ema50 else 0
    if price_above_ema200: score += 15; reasons.append("Preço acima EMA200")
    elif ema200: warnings_list.append("Preço abaixo EMA200")
    score += 15 if ema21_above_50 else 0
    score += 10 if ema50_above_200 else (0 if not ema200 else -0)
    score += 10 if (slope21 and slope21 > 0) else 0
    score += 10 if (slope50 and slope50 > 0) else 0
    score += 5 if (ret20 and ret20 > 0) else 0
    score += 5 if (ret60 and ret60 > 0) else 0

    score = min(100, max(0, score))

    if score >= TREND_STRONG: cls = "FORTE"
    elif score >= TREND_HEALTHY: cls = "SAUDAVEL"
    elif score >= 45: cls = "TRANSICAO"
    elif score >= 25: cls = "FRACA"
    else: cls = "BAIXA_FORTE"

    return {
        "trend_score": score, "classification": cls,
        "price_above_ema21": price_above_ema21, "price_above_ema50": price_above_ema50,
        "price_above_ema200": price_above_ema200, "ema21_above_ema50": ema21_above_50,
        "ema50_above_ema200": ema50_above_200, "ema21_slope": round(slope21, 2) if slope21 else None,
        "ema50_slope": round(slope50, 2) if slope50 else None,
        "reasons": reasons, "warnings": warnings_list,
    }

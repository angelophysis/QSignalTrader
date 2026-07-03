from __future__ import annotations

import numpy as np

from src.v2.config import RISK_ACCEPTABLE


def _safe(val):
    if val is None: return None
    if isinstance(val, np.generic): val = val.item()
    if isinstance(val, (int, float)):
        if np.isnan(val) or np.isinf(val): return None
        return float(val)
    return None


def calculate_risk_score(df, indicators: dict, supports: list[dict] | None = None) -> dict:
    if df is None or df.empty:
        return {"risk_score": 0, "classification": "EXTREMO", "reasons": [], "warnings": ["Sem dados"]}

    score = 100
    warnings_list = []
    reasons = []

    atr_pct = indicators.get("atr_pct")
    if atr_pct is not None:
        if atr_pct > 7: score -= 20; warnings_list.append(f"ATR% elevado ({atr_pct}%)")
        elif atr_pct > 4: score -= 10
        elif atr_pct < 1: score += 5

    dist_ema21 = indicators.get("dist_ema21_pct")
    if dist_ema21 is not None:
        if dist_ema21 > 12: score -= 35; warnings_list.append(f"Muito esticado da EMA21 (+{dist_ema21:.1f}%)")
        elif dist_ema21 > 8: score -= 20; warnings_list.append(f"Esticado da EMA21 (+{dist_ema21:.1f}%)")
        elif dist_ema21 > 5: score -= 10

    if len(df) >= 2:
        latest_candle = abs(_safe(df["high"].iloc[-1]) - _safe(df["low"].iloc[-1]))
        atr = indicators.get("atr")
        if latest_candle and atr and atr > 0:
            ratio = latest_candle / atr
            if ratio > 3: score -= 25; warnings_list.append(f"Candle {ratio:.1f}x ATR")
            elif ratio > 2: score -= 15

    if not supports or len(supports) == 0:
        score -= 15; warnings_list.append("Sem suporte abaixo")
    elif supports[0].get("distance_pct") is not None:
        inval_dist = abs(supports[0]["distance_pct"])
        if inval_dist > 10: score -= 15; warnings_list.append(f"Invalidação distante ({inval_dist:.1f}%)")

    if not warnings_list and score >= 85: reasons.append("Risco controlado")

    score = min(100, max(0, score))

    if score >= 80: cls = "CONTROLADO"
    elif score >= RISK_ACCEPTABLE: cls = "ACEITAVEL"
    elif score >= 40: cls = "MEDIO"
    elif score >= 20: cls = "ALTO"
    else: cls = "EXTREMO"

    return {
        "risk_score": score, "classification": cls,
        "atr_pct": atr_pct, "distance_ema21_pct": dist_ema21,
        "reasons": reasons, "warnings": warnings_list,
    }

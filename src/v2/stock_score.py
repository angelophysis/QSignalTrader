from __future__ import annotations

from src.v2.config import QSIGNAL_CLASS_MAP, QSIGNAL_WEIGHTS


def _data_quality(df, indicators, supports, resistances, benchmark_ok: bool) -> dict:
    score = 100
    warnings_list = []
    if indicators.get("candles", 0) < 180: score -= 20; warnings_list.append("Poucos candles (< 180)")
    if not indicators.get("price_above_ema200") and indicators.get("ema200"): score -= 10
    if indicators.get("vol_rel") is None: score -= 15; warnings_list.append("Sem dados de volume")
    if not supports or not resistances: score -= 15; warnings_list.append("S/R incompletos")
    if not benchmark_ok: score -= 10
    return {"data_quality_score": max(0, score), "warnings": warnings_list}


def calculate_qsignal_stock_score(
    trend: dict, momentum: dict, location: dict,
    relative_strength: dict, risk: dict,
    df=None, indicators: dict | None = None,
    supports: list | None = None, resistances: list | None = None,
    benchmark_ok: bool = True,
) -> dict:
    dq = _data_quality(df, indicators or {}, supports or [], resistances or [], benchmark_ok)

    components = {
        "trend": trend.get("trend_score", 0),
        "momentum": momentum.get("momentum_score", 0),
        "location": location.get("location_score", 0),
        "relative_strength": relative_strength.get("relative_strength_score", 50),
        "risk": risk.get("risk_score", 50),
        "data_quality": dq["data_quality_score"],
    }

    total = sum(components[k] * QSIGNAL_WEIGHTS[k] for k in QSIGNAL_WEIGHTS)
    total = min(100, max(0, round(total)))

    cls = "RUIM"
    for thresh, label in QSIGNAL_CLASS_MAP:
        if total >= thresh:
            cls = label
            break

    all_reasons = []
    all_warnings = dq.get("warnings", [])

    for name, comp in [("trend", trend), ("momentum", momentum), ("location", location),
                       ("relative_strength", relative_strength), ("risk", risk)]:
        all_reasons.extend(comp.get("reasons", []))
        all_warnings.extend(comp.get("warnings", []))

    # Protective warnings
    if location.get("location_score", 0) < 45: all_warnings.append("Location Score baixo — ponto ruim")
    if risk.get("risk_score", 0) < 40: all_warnings.append("Risk Score baixo — risco elevado")
    if momentum.get("momentum_score", 0) < 45: all_warnings.append("Momentum fraco — cautela")
    if location.get("is_near_resistance"): all_warnings.append("Preço próximo de resistência")
    if location.get("is_extended"): all_warnings.append("Preço esticado da EMA21")

    return {
        "qsignal_stock_score": total, "classification": cls,
        "component_scores": components, "weights": QSIGNAL_WEIGHTS,
        "reasons": list(set(all_reasons)), "warnings": list(set(all_warnings)),
    }

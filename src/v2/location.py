from __future__ import annotations

from src.v2.config import (
    LOCATION_GOOD,
    MIN_REWARD_RISK_ACCEPTABLE,
    MIN_REWARD_RISK_GOOD,
    NEAR_RESISTANCE_PCT,
    NEAR_SUPPORT_PCT,
)


def calculate_location_score(current_price: float, supports: list[dict], resistances: list[dict],
                              indicators: dict | None = None) -> dict:
    if current_price is None or current_price <= 0:
        return {"location_score": 50, "classification": "NEUTRA", "reasons": [], "warnings": ["Preço indisponível"]}

    nearest_support = supports[0] if supports else None
    nearest_resistance = resistances[0] if resistances else None

    dist_support_pct = abs(nearest_support["distance_pct"]) if nearest_support else None
    dist_resistance_pct = nearest_resistance["distance_pct"] if nearest_resistance else None

    reward_risk = dist_resistance_pct / dist_support_pct if dist_resistance_pct and dist_support_pct and dist_support_pct > 0 else None

    score = 50
    reasons = []
    warnings_list = []

    # Near support
    ns = nearest_support
    if ns and ns.get("distance_pct") is not None:
        dist_abs = abs(ns["distance_pct"])
        if dist_abs <= NEAR_SUPPORT_PCT and ns.get("strength", 0) >= 60:
            score += 20; reasons.append(f"Próximo de {ns.get('label', 'suporte')} forte ({ns['price']:.2f})")
        elif dist_abs <= NEAR_SUPPORT_PCT:
            score += 12; reasons.append(f"Próximo de suporte ({ns['price']:.2f})")
        elif dist_abs <= 6:
            score += 5
    else:
        warnings_list.append("Sem suporte claro próximo")

    # Near resistance
    nr = nearest_resistance
    if nr and nr.get("distance_pct") is not None:
        if nr["distance_pct"] <= NEAR_RESISTANCE_PCT and nr.get("strength", 0) >= 60:
            score -= 20; warnings_list.append(f"Colado em {nr.get('label', 'resistência')} forte ({nr['price']:.2f})")
        elif nr["distance_pct"] <= NEAR_RESISTANCE_PCT:
            score -= 10; warnings_list.append(f"Próximo de resistência ({nr['price']:.2f})")

    # Reward/risk
    if reward_risk is not None:
        if reward_risk >= MIN_REWARD_RISK_GOOD: score += 10; reasons.append(f"R/R até R1 bom ({reward_risk:.1f}:1)")
        elif reward_risk >= MIN_REWARD_RISK_ACCEPTABLE: score += 5
        elif reward_risk < 1.0: score -= 15; warnings_list.append(f"R/R desfavorável ({reward_risk:.1f}:1)")

    # Extension from EMA21
    dist_ema21 = indicators.get("dist_ema21_pct") if indicators else None
    if dist_ema21 is not None:
        if abs(dist_ema21) <= 5:
            score += 10 if dist_ema21 > -2 else 5
        elif dist_ema21 > 8:
            score -= 15; warnings_list.append(f"Esticado da EMA21 (+{dist_ema21:.1f}%)")
        elif dist_ema21 < -8:
            score -= 5

    score = min(100, max(0, score))

    if score >= LOCATION_GOOD: cls = "OTIMA"
    elif score >= 55: cls = "BOA"
    elif score >= 40: cls = "NEUTRA"
    elif score >= 25: cls = "RUIM"
    else: cls = "PERIGOSA"

    return {
        "location_score": score, "classification": cls,
        "nearest_support": nearest_support, "nearest_resistance": nearest_resistance,
        "distance_support_pct": dist_support_pct, "distance_resistance_pct": dist_resistance_pct,
        "reward_risk_to_r1": round(reward_risk, 2) if reward_risk else None,
        "is_near_support": dist_support_pct is not None and dist_support_pct <= NEAR_SUPPORT_PCT,
        "is_near_resistance": dist_resistance_pct is not None and dist_resistance_pct <= NEAR_RESISTANCE_PCT,
        "is_extended": dist_ema21 is not None and dist_ema21 > 8 if dist_ema21 else False,
        "reasons": reasons, "warnings": warnings_list,
    }

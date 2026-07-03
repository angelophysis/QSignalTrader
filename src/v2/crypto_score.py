from __future__ import annotations

from src.v2.config import QSIGNAL_CLASS_MAP, QSIGNAL_CRYPTO_WEIGHTS


def calculate_qsignal_crypto_score(trend: dict, momentum: dict, location: dict,
                                    btc_rs: dict, risk: dict, data_quality: float = 100) -> dict:
    components = {
        "trend": trend.get("trend_score", 0),
        "momentum": momentum.get("momentum_score", 0),
        "location": location.get("location_score", 0),
        "btc_relative_strength": btc_rs.get("btc_relative_strength_score", 50),
        "risk": risk.get("risk_score", 50),
        "data_quality": data_quality,
    }

    total = sum(components[k] * QSIGNAL_CRYPTO_WEIGHTS[k] for k in QSIGNAL_CRYPTO_WEIGHTS)
    total = min(100, max(0, round(total)))

    cls = "RUIM"
    for thresh, label in QSIGNAL_CLASS_MAP:
        if total >= thresh:
            cls = label
            break

    all_reasons = []
    all_warnings = []
    for comp in [trend, momentum, location, btc_rs, risk]:
        all_reasons.extend(comp.get("reasons", []))
        all_warnings.extend(comp.get("warnings", []))

    if risk.get("risk_score", 0) < 40:
        all_warnings.append("Risk Score baixo — risco elevado para cripto")
    if momentum.get("momentum_score", 0) < 45:
        all_warnings.append("Momentum fraco — cautela")
    btc_score = btc_rs.get("btc_relative_strength_score", 50)
    if btc_score < 40 and btc_rs.get("classification") != "BENCHMARK":
        all_warnings.append("Força relativa vs BTC baixa")

    return {
        "qsignal_crypto_score": total, "classification": cls,
        "component_scores": components, "weights": QSIGNAL_CRYPTO_WEIGHTS,
        "reasons": list(set(all_reasons)), "warnings": list(set(all_warnings)),
    }

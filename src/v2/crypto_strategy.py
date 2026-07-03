from __future__ import annotations


def determine_crypto_strategy(qsignal_score: dict, regime: dict, trend: dict, momentum: dict,
                               location: dict, risk: dict, btc_rs: dict, supports: list[dict],
                               resistances: list[dict]) -> dict:
    regime_key = regime.get("regime", "CRYPTO_INDEFINIDO")
    total_score = qsignal_score.get("qsignal_crypto_score", 0)
    t_score = trend.get("trend_score", 0)
    m_score = momentum.get("momentum_score", 0)
    l_score = location.get("location_score", 0)
    r_score = risk.get("risk_score", 0)
    btc_score = btc_rs.get("btc_relative_strength_score", 50)

    trigger = resistances[0]["price"] if resistances else None
    invalidation = supports[0]["price"] if supports and l_score >= 50 else (supports[1]["price"] if len(supports) > 1 else (supports[0]["price"] if supports else None))

    # Altcoin leader
    if regime_key == "CRYPTO_ALTCOIN_LIDER" and m_score >= 60 and r_score >= 45:
        return {"strategy": "CRYPTO_ALTCOIN_LEADER", "action_without_position": "COMPRAR_PARCIAL",
                "action_with_position": "MANTER", "confidence": "MEDIA",
                "trigger_level": trigger, "invalidation_level": invalidation,
                "main_reason": "Performando melhor que BTC com momentum favorável."}

    # Trend continuation
    if regime_key in ("CRYPTO_BULL_FORTE", "CRYPTO_BULL_SAUDAVEL") and total_score >= 70 and t_score >= 70 and m_score >= 60 and r_score >= 50:
        return {"strategy": "CRYPTO_TREND_CONTINUATION",
                "action_without_position": "COMPRAR_PARCIAL" if l_score >= 55 else "AGUARDAR_GATILHO",
                "action_with_position": "MANTER", "confidence": "ALTA" if l_score >= 55 else "MEDIA",
                "trigger_level": trigger, "invalidation_level": invalidation,
                "main_reason": "Tendência saudável com momentum favorável."}

    # Pullback buy
    if regime_key == "CRYPTO_PULLBACK_DE_ALTA" and t_score >= 60 and l_score >= 65 and m_score >= 45:
        return {"strategy": "CRYPTO_PULLBACK_BUY", "action_without_position": "COMPRAR_PARCIAL",
                "action_with_position": "MANTER", "confidence": "MEDIA",
                "trigger_level": supports[0]["price"] if supports else None,
                "invalidation_level": supports[1]["price"] if len(supports) > 1 else (supports[0]["price"] if supports else None),
                "main_reason": "Pullback em tendência de alta."}

    # Breakout
    if regime_key in ("CRYPTO_BREAKOUT_SETUP", "CRYPTO_BREAKOUT_CONFIRMADO") and m_score >= 65 and r_score >= 45:
        conf = "MEDIA" if regime_key == "CRYPTO_BREAKOUT_CONFIRMADO" else "BAIXA"
        return {"strategy": "CRYPTO_BREAKOUT_CONFIRMATION",
                "action_without_position": "COMPRAR_PARCIAL" if regime_key == "CRYPTO_BREAKOUT_CONFIRMADO" else "AGUARDAR_GATILHO",
                "action_with_position": "MANTER", "confidence": conf,
                "trigger_level": trigger, "invalidation_level": invalidation,
                "main_reason": "Setup de breakout." + (" Confirmado." if regime_key == "CRYPTO_BREAKOUT_CONFIRMADO" else " Aguardar.")}

    # Recovery
    if regime_key == "CRYPTO_RECUPERACAO":
        return {"strategy": "CRYPTO_RECOVERY_WATCH",
                "action_without_position": "OBSERVAR", "action_with_position": "MANTER_COM_CAUTELA",
                "confidence": "BAIXA", "trigger_level": trigger, "invalidation_level": invalidation,
                "main_reason": "Recuperação em andamento.", "warnings": ["Recuperação não é tendência confirmada."]}

    # Defensive
    if regime_key in ("CRYPTO_BEAR_FORTE", "CRYPTO_CAPITULACAO", "CRYPTO_DISTRIBUICAO") or r_score < 30 or t_score < 30:
        return {"strategy": "CRYPTO_DEFENSIVE_MODE", "action_without_position": "EVITAR",
                "action_with_position": "REDUZIR" if regime_key in ("CRYPTO_BEAR_FORTE", "CRYPTO_CAPITULACAO") else "MANTER_COM_CAUTELA",
                "confidence": "ALTA" if regime_key == "CRYPTO_CAPITULACAO" else "MEDIA",
                "trigger_level": None, "invalidation_level": invalidation,
                "main_reason": "Cenário desfavorável."}

    # No trade
    return {"strategy": "CRYPTO_NO_TRADE", "action_without_position": "EVITAR",
            "action_with_position": "MANTER_COM_CAUTELA", "confidence": "BAIXA",
            "trigger_level": None, "invalidation_level": invalidation,
            "main_reason": "Sinais insuficientes para decisão clara."}

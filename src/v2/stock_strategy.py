from __future__ import annotations


def determine_stock_strategy(qsignal_score: dict, regime: dict, trend: dict, momentum: dict,
                              location: dict, risk: dict, supports: list[dict],
                              resistances: list[dict]) -> dict:
    regime_key = regime.get("regime", "INDEFINIDO")
    total_score = qsignal_score.get("qsignal_stock_score", 0)
    t_score = trend.get("trend_score", 0)
    m_score = momentum.get("momentum_score", 0)
    l_score = location.get("location_score", 0)
    r_score = risk.get("risk_score", 0)

    trigger = None
    invalidation = None
    conf = "BAIXA"

    # Extract trigger & invalidation from S/R
    if resistances:
        trigger = resistances[0]["price"]
    if supports:
        invalidation = supports[0]["price"] if l_score >= 50 else (supports[1]["price"] if len(supports) > 1 else supports[0]["price"])

    # TREND_CONTINUATION
    if regime_key in ("BULL_FORTE", "BULL_SAUDAVEL") and total_score >= 70 and t_score >= 70 and m_score >= 60 and r_score >= 50:
        conf = "ALTA" if l_score >= 55 else "MEDIA"
        strat = "TREND_CONTINUATION"
        if l_score >= 55:
            return {"strategy": strat, "action_without_position": "COMPRAR_PARCIAL", "action_with_position": "MANTER",
                    "confidence": conf, "trigger_level": trigger, "invalidation_level": invalidation,
                    "main_reason": "Tendência saudável com momentum e risco favoráveis.",
                    "reasons": [], "warnings": []}
        else:
            return {"strategy": strat, "action_without_position": "AGUARDAR_GATILHO", "action_with_position": "MANTER",
                    "confidence": conf, "trigger_level": trigger, "invalidation_level": invalidation,
                    "main_reason": "Tendência saudável, mas ponto de entrada não é ideal.",
                    "reasons": [], "warnings": ["Location Score baixo — aguardar melhor ponto."]}

    # PULLBACK_BUY
    if regime_key == "PULLBACK_DE_ALTA" and t_score >= 60 and l_score >= 65 and m_score >= 45 and r_score >= 45:
        conf = "MEDIA"
        return {"strategy": "PULLBACK_BUY", "action_without_position": "COMPRAR_PARCIAL", "action_with_position": "AUMENTAR",
                "confidence": conf, "trigger_level": supports[0]["price"] if supports else None,
                "invalidation_level": supports[1]["price"] if len(supports) > 1 else (supports[0]["price"] if supports else None),
                "main_reason": "Pullback em tendência de alta com bom ponto de entrada.",
                "reasons": [], "warnings": []}

    # BREAKOUT_CONFIRMATION
    if regime_key in ("BREAKOUT_SETUP", "BREAKOUT_CONFIRMADO") and m_score >= 65 and r_score >= 45:
        conf = "MEDIA"
        if regime_key == "BREAKOUT_CONFIRMADO":
            return {"strategy": "BREAKOUT_CONFIRMATION", "action_without_position": "COMPRAR_PARCIAL", "action_with_position": "MANTER",
                    "confidence": conf, "trigger_level": trigger, "invalidation_level": invalidation,
                    "main_reason": "Breakout confirmado com volume e momentum.", "reasons": [], "warnings": []}
        else:
            return {"strategy": "BREAKOUT_CONFIRMATION", "action_without_position": "AGUARDAR_GATILHO", "action_with_position": "MANTER",
                    "confidence": "BAIXA", "trigger_level": trigger,
                    "invalidation_level": supports[0]["price"] if supports else None,
                    "main_reason": "Setup de breakout detectado. Aguardar confirmação.", "reasons": [],
                    "warnings": ["Breakout ainda não confirmado."]}

    # RECOVERY_WATCH
    if regime_key == "RECUPERACAO":
        conf = "BAIXA"
        if total_score >= 70:
            return {"strategy": "RECOVERY_WATCH", "action_without_position": "COMPRAR_PARCIAL", "action_with_position": "MANTER_COM_CAUTELA",
                    "confidence": conf, "trigger_level": trigger, "invalidation_level": invalidation,
                    "main_reason": "Recuperação com bom score. Posição pequena com cautela.", "reasons": [],
                    "warnings": ["Recuperação não é tendência confirmada."]}
        return {"strategy": "RECOVERY_WATCH", "action_without_position": "OBSERVAR", "action_with_position": "MANTER_COM_CAUTELA",
                "confidence": conf, "trigger_level": None, "invalidation_level": invalidation,
                "main_reason": "Recuperação em andamento. Aguardar confirmação.", "reasons": [],
                "warnings": ["Recuperação não é tendência confirmada."]}

    # DEFENSIVE_MODE
    if regime_key in ("DISTRIBUICAO", "BEAR_FORTE") or r_score < 30 or t_score < 30:
        conf = "ALTA" if regime_key == "BEAR_FORTE" else "MEDIA"
        return {"strategy": "DEFENSIVE_MODE", "action_without_position": "EVITAR", "action_with_position": "REDUZIR",
                "confidence": conf, "trigger_level": None, "invalidation_level": None,
                "main_reason": "Cenário desfavorável para compras.", "reasons": [], "warnings": ["Evitar novas entradas."]}

    # NO_TRADE (fallback)
    return {"strategy": "NO_TRADE", "action_without_position": "EVITAR", "action_with_position": "MANTER_COM_CAUTELA",
            "confidence": "BAIXA", "trigger_level": None, "invalidation_level": invalidation,
            "main_reason": "Sinais insuficientes para decisão clara.", "reasons": [],
            "warnings": ["Aguardar definição do cenário."]}

from __future__ import annotations


def classify_stock_regime(trend: dict, momentum: dict, location: dict, risk: dict,
                           radar_modes: list[str] | None = None, indicators: dict | None = None) -> dict:
    t_score = trend.get("trend_score", 0)
    m_score = momentum.get("momentum_score", 0)
    l_score = location.get("location_score", 0)
    r_score = risk.get("risk_score", 0)
    modes = radar_modes or []

    reasons = []
    warnings_list = []

    # BULL_FORTE
    if t_score >= 80 and m_score >= 70 and r_score >= 50:
        return {"regime": "BULL_FORTE", "confidence": "ALTA",
                "description": "Tendência forte com momentum elevado e risco controlado.", "reasons": reasons, "warnings": warnings_list}

    # BREAKOUT_CONFIRMADO
    if m_score >= 70 and location.get("is_near_resistance") and indicators and indicators.get("vol_rel", 0) >= 1.2 and r_score >= 45:
        return {"regime": "BREAKOUT_CONFIRMADO", "confidence": "MEDIA",
                "description": "Preço rompendo resistência com volume e momentum.", "reasons": reasons, "warnings": warnings_list}

    # BREAKOUT_SETUP
    if "BREAKOUT_SETUP" in modes and m_score >= 60:
        return {"regime": "BREAKOUT_SETUP", "confidence": "MEDIA",
                "description": "Setup de rompimento detectado. Aguardar confirmação.", "reasons": reasons,
                "warnings": ["Setup ainda não confirmou rompimento."]}

    # PULLBACK_DE_ALTA
    if ("PULLBACK_DE_ALTA" in modes or (t_score >= 60 and 45 <= m_score <= 70 and l_score >= 60)):
        return {"regime": "PULLBACK_DE_ALTA", "confidence": "MEDIA",
                "description": "Pullback em tendência de alta. Ponto potencial de entrada.", "reasons": reasons, "warnings": warnings_list}

    # BULL_SAUDAVEL
    if t_score >= 60 and m_score >= 55 and r_score >= 50:
        return {"regime": "BULL_SAUDAVEL", "confidence": "ALTA" if t_score >= 70 else "MEDIA",
                "description": "Tendência saudável com momentum favorável.", "reasons": reasons, "warnings": warnings_list}

    # RECUPERACAO
    if "RECUPERACAO_INICIAL" in modes or (35 <= t_score <= 65 and m_score >= 35 and m_score < 55):
        warnings_list.append("Recuperação ainda exige confirmação.")
        return {"regime": "RECUPERACAO", "confidence": "BAIXA",
                "description": "Recuperação em andamento. Ainda não é tendência confirmada.", "reasons": reasons, "warnings": warnings_list}

    # DISTRIBUICAO
    if t_score >= 50 and m_score < 45 and r_score < 55:
        warnings_list.append("Momentum perdendo força — possível distribuição.")
        return {"regime": "DISTRIBUICAO", "confidence": "MEDIA",
                "description": "Tendência ainda presente, mas momentum enfraquecendo.", "reasons": reasons, "warnings": warnings_list}

    # BEAR_FORTE
    if t_score < 30 and m_score < 40:
        return {"regime": "BEAR_FORTE", "confidence": "ALTA",
                "description": "Tendência de baixa forte. Evitar compras.", "reasons": reasons, "warnings": warnings_list}

    # LATERALIZACAO
    if 40 <= t_score <= 60 and 40 <= m_score <= 60 and not modes:
        return {"regime": "LATERALIZACAO", "confidence": "MEDIA",
                "description": "Ativo lateralizado, sem direção clara.", "reasons": reasons, "warnings": warnings_list}

    return {"regime": "INDEFINIDO", "confidence": "BAIXA",
            "description": "Sinais contraditórios. Aguardar definição.", "reasons": reasons, "warnings": warnings_list}

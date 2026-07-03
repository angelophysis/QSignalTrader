from __future__ import annotations


def classify_crypto_regime(trend: dict, momentum: dict, location: dict, risk: dict,
                            btc_rs: dict, radar_modes: list[str] | None = None) -> dict:
    t_score = trend.get("trend_score", 0)
    m_score = momentum.get("momentum_score", 0)
    l_score = location.get("location_score", 0)
    r_score = risk.get("risk_score", 0)
    btc_score = btc_rs.get("btc_relative_strength_score", 50)
    modes = radar_modes or []

    # Capitulação: trend muito fraco + risk extremo + RSI baixo
    if t_score < 25 and r_score < 25:
        return {"regime": "CRYPTO_CAPITULACAO", "confidence": "ALTA",
                "description": "Capitulação. Trend e risco extremos.", "reasons": [], "warnings": []}

    # Bear forte
    if t_score < 30 and m_score < 40:
        return {"regime": "CRYPTO_BEAR_FORTE", "confidence": "ALTA",
                "description": "Bear forte. Evitar compras.", "reasons": [], "warnings": []}

    # Bull forte
    if t_score >= 80 and m_score >= 70 and r_score >= 50:
        return {"regime": "CRYPTO_BULL_FORTE", "confidence": "ALTA",
                "description": "Bull forte com momentum e risco controlado.", "reasons": [], "warnings": []}

    # Altcoin líder
    if btc_score >= 75 and m_score >= 60 and t_score >= 55:
        return {"regime": "CRYPTO_ALTCOIN_LIDER", "confidence": "MEDIA",
                "description": "Performando melhor que BTC com momentum favorável.", "reasons": [], "warnings": []}

    # Breakout
    if "CRYPTO_BREAKOUT_SETUP" in modes and m_score >= 60:
        return {"regime": "CRYPTO_BREAKOUT_SETUP", "confidence": "MEDIA",
                "description": "Setup de breakout. Aguardar confirmação.", "reasons": [],
                "warnings": ["Breakout ainda não confirmado."]}

    # Pullback
    if "CRYPTO_PULLBACK_DE_ALTA" in modes or (t_score >= 60 and 40 <= m_score <= 65 and l_score >= 60):
        return {"regime": "CRYPTO_PULLBACK_DE_ALTA", "confidence": "MEDIA",
                "description": "Pullback em tendência de alta.", "reasons": [], "warnings": []}

    # Bull saudável
    if t_score >= 60 and m_score >= 55 and r_score >= 50:
        return {"regime": "CRYPTO_BULL_SAUDAVEL", "confidence": "ALTA" if t_score >= 70 else "MEDIA",
                "description": "Bull saudável com momentum favorável.", "reasons": [], "warnings": []}

    # Recuperação
    if "CRYPTO_RECUPERACAO" in modes or (35 <= t_score <= 65 and m_score >= 35 and m_score < 55):
        return {"regime": "CRYPTO_RECUPERACAO", "confidence": "BAIXA",
                "description": "Recuperação em andamento.", "reasons": [],
                "warnings": ["Recuperação ainda exige confirmação."]}

    # Distribuição
    if t_score >= 50 and m_score < 45 and r_score < 55:
        return {"regime": "CRYPTO_DISTRIBUICAO", "confidence": "MEDIA",
                "description": "Tendência presente mas momentum enfraquecendo.", "reasons": [], "warnings": []}

    # Lateral
    if 40 <= t_score <= 60 and 40 <= m_score <= 60:
        return {"regime": "CRYPTO_LATERALIZACAO", "confidence": "MEDIA",
                "description": "Ativo lateralizado, sem direção clara.", "reasons": [], "warnings": []}

    return {"regime": "CRYPTO_INDEFINIDO", "confidence": "BAIXA",
            "description": "Sinais contraditórios.", "reasons": [], "warnings": []}

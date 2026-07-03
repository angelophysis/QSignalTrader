from __future__ import annotations

from src.data.fetch_crypto import get_crypto_data
from src.v2.momentum import calculate_stock_momentum_score
from src.v2.trend import calculate_trend_score
from src.v2.location import calculate_location_score
from src.v2.risk import calculate_risk_score
from src.v2.support_resistance import calculate_support_resistance_levels
from src.v2.radar_lite import calculate_radar_lite_indicators, calculate_radar_lite_score
from src.v2.crypto_relative_strength import calculate_crypto_relative_strength_score
from src.v2.crypto_score import calculate_qsignal_crypto_score
from src.v2.crypto_regime import classify_crypto_regime
from src.v2.crypto_strategy import determine_crypto_strategy
from src.v2.crypto_signal_formatter import format_crypto_analysis_summary


def analyze_crypto_v2(symbol: str, period: str = "1y") -> dict:
    errors = []
    is_btc = symbol.upper().replace(" ", "").replace("/", "") in ("BTCUSDT", "BTC/USDT", "BTC-USD", "BTCUSD")

    # ── Fetch data ──
    try:
        df = get_crypto_data(symbol=symbol, timeframe="1d", limit=300)
    except Exception as e:
        return {"symbol": symbol, "error": f"Erro ao buscar dados: {e}", "errors": [{"module": "data", "error": str(e)}]}

    if df.empty or len(df) < 50:
        return {"symbol": symbol, "error": "Dados insuficientes", "errors": []}

    current_price = float(df["close"].iloc[-1])

    # ── Indicators ──
    try:
        indicators = calculate_radar_lite_indicators(df)
    except Exception as e:
        return {"symbol": symbol, "error": f"Erro indicadores: {e}", "errors": [{"module": "indicators", "error": str(e)}]}

    try:
        radar_score = calculate_radar_lite_score(indicators)
    except Exception as e:
        radar_score = {"radar_lite_score": 0, "radar_modes": [], "reasons": [], "warnings": []}
        errors.append({"module": "radar", "error": str(e)})

    # ── Momentum ──
    try:
        momentum = calculate_stock_momentum_score(df)
    except Exception as e:
        momentum = {"momentum_score": 0, "classification": "INDEFINIDO", "reasons": [], "warnings": [str(e)]}
        errors.append({"module": "momentum", "error": str(e)})

    # ── SR ──
    try:
        sr = calculate_support_resistance_levels(df, current_price)
    except Exception as e:
        sr = {"supports": [], "resistances": [], "warnings": [str(e)]}
        errors.append({"module": "sr", "error": str(e)})
    supports = sr.get("supports", [])
    resistances = sr.get("resistances", [])

    # ── Trend ──
    try:
        trend = calculate_trend_score(df)
    except Exception as e:
        trend = {"trend_score": 0, "classification": "INDEFINIDO", "reasons": [], "warnings": [str(e)]}
        errors.append({"module": "trend", "error": str(e)})

    # ── Location ──
    try:
        location = calculate_location_score(current_price, supports, resistances, indicators)
    except Exception as e:
        location = {"location_score": 0, "classification": "INDEFINIDO", "reasons": [], "warnings": [str(e)]}
        errors.append({"module": "location", "error": str(e)})

    # ── Risk ──
    try:
        risk = calculate_risk_score(df, indicators, supports)
    except Exception as e:
        risk = {"risk_score": 0, "classification": "INDEFINIDO", "reasons": [], "warnings": [str(e)]}
        errors.append({"module": "risk", "error": str(e)})

    # ── BTC Relative Strength ──
    try:
        btc_rs = calculate_crypto_relative_strength_score(df, symbol=symbol)
    except Exception as e:
        btc_rs = {"btc_relative_strength_score": 50, "classification": "NEUTRA", "reasons": [], "warnings": [str(e)]}
        errors.append({"module": "btc_rs", "error": str(e)})

    # ── Crypto Score ──
    try:
        crypto_score = calculate_qsignal_crypto_score(trend, momentum, location, btc_rs, risk)
    except Exception as e:
        crypto_score = {"qsignal_crypto_score": 0, "classification": "RUIM", "component_scores": {}, "reasons": [], "warnings": [str(e)]}
        errors.append({"module": "score", "error": str(e)})

    # ── Regime ──
    try:
        regime = classify_crypto_regime(trend, momentum, location, risk, btc_rs, radar_score.get("radar_modes"))
    except Exception as e:
        regime = {"regime": "CRYPTO_INDEFINIDO", "confidence": "BAIXA", "description": "", "reasons": [], "warnings": [str(e)]}
        errors.append({"module": "regime", "error": str(e)})

    # ── Strategy ──
    try:
        strategy = determine_crypto_strategy(crypto_score, regime, trend, momentum, location, risk, btc_rs, supports, resistances)
    except Exception as e:
        strategy = {"strategy": "CRYPTO_NO_TRADE", "action_without_position": "EVITAR", "action_with_position": "MANTER_COM_CAUTELA",
                    "confidence": "BAIXA", "main_reason": str(e)}
        errors.append({"module": "strategy", "error": str(e)})

    analysis = {
        "symbol": symbol, "preco_atual": current_price,
        "radar_lite_score": radar_score.get("radar_lite_score"),
        "radar_modes": radar_score.get("radar_modes", []),
        "momentum": momentum, "supports": supports, "resistances": resistances,
        "trend": trend, "location": location, "risk": risk,
        "btc_relative_strength": btc_rs, "qsignal_score": crypto_score,
        "regime": regime, "strategy": strategy,
        "reasons": crypto_score.get("reasons", []), "warnings": crypto_score.get("warnings", []),
        "errors": errors,
    }

    try:
        analysis["formatted"] = format_crypto_analysis_summary(analysis)
    except Exception as e:
        analysis["formatted"] = {"summary": "Erro ao formatar.", "bullish_points": [], "bearish_points": []}

    return analysis

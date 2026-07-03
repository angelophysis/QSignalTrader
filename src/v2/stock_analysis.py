from __future__ import annotations

from src.data.yfinance_handler import YahooFinanceDataHandler
from src.v2.config import DEFAULT_PERIOD
from src.v2.momentum import calculate_stock_momentum_score
from src.v2.radar_lite import calculate_radar_lite_indicators, calculate_radar_lite_score
from src.v2.support_resistance import calculate_support_resistance_levels
from src.v2.trend import calculate_trend_score
from src.v2.location import calculate_location_score
from src.v2.risk import calculate_risk_score
from src.v2.relative_strength import calculate_relative_strength_score
from src.v2.stock_score import calculate_qsignal_stock_score
from src.v2.stock_regime import classify_stock_regime
from src.v2.stock_strategy import determine_stock_strategy
from src.v2.stock_signal_formatter import format_stock_analysis_summary


def _safe_dict(d: dict | None) -> dict:
    return d if isinstance(d, dict) else {}


def analyze_stock_v2(ticker: str, period: str = DEFAULT_PERIOD) -> dict:
    errors = []

    dh = YahooFinanceDataHandler(auto_adjust=True)

    try:
        df = dh.fetch_ohlc(ticker=ticker, period=period, interval="1d")
    except Exception as e:
        return {"ticker": ticker, "error": f"Erro ao buscar dados: {e}", "errors": [{"module": "data", "error": str(e)}]}

    if df.empty or len(df) < 50:
        return {"ticker": ticker, "error": "Dados insuficientes (menos de 50 candles)", "errors": []}

    current_price = float(df["close"].iloc[-1])

    # ── Radar Lite indicators ──
    try:
        indicators = calculate_radar_lite_indicators(df)
    except Exception as e:
        return {"ticker": ticker, "error": f"Erro nos indicadores: {e}", "errors": [{"module": "indicators", "error": str(e)}]}

    try:
        radar_score = calculate_radar_lite_score(indicators)
    except Exception as e:
        radar_score = {"radar_lite_score": 0, "status": "IGNORAR", "radar_modes": [], "reasons": [], "warnings": []}
        errors.append({"module": "radar_score", "error": str(e)})

    # ── Momentum ──
    try:
        momentum = calculate_stock_momentum_score(df)
    except Exception as e:
        momentum = {"momentum_score": 0, "classification": "INDEFINIDO", "reasons": [], "warnings": [str(e)]}
        errors.append({"module": "momentum", "error": str(e)})

    # ── Support / Resistance ──
    try:
        sr = calculate_support_resistance_levels(df, current_price)
    except Exception as e:
        sr = {"supports": [], "resistances": [], "warnings": [str(e)]}
        errors.append({"module": "support_resistance", "error": str(e)})
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

    # ── Relative Strength ──
    try:
        rel_str = calculate_relative_strength_score(df, ticker=ticker)
    except Exception as e:
        rel_str = {"relative_strength_score": 50, "classification": "NEUTRA", "reasons": [], "warnings": [str(e)]}
        errors.append({"module": "relative_strength", "error": str(e)})

    # ── QSignal Score ──
    try:
        stock_score = calculate_qsignal_stock_score(
            trend, momentum, location, rel_str, risk, df, indicators, supports, resistances,
            benchmark_ok=rel_str.get("benchmark") is not None,
        )
    except Exception as e:
        stock_score = {"qsignal_stock_score": 0, "classification": "RUIM", "component_scores": {}, "reasons": [], "warnings": [str(e)]}
        errors.append({"module": "stock_score", "error": str(e)})

    # ── Regime ──
    try:
        regime = classify_stock_regime(trend, momentum, location, risk, radar_score.get("radar_modes"), indicators)
    except Exception as e:
        regime = {"regime": "INDEFINIDO", "confidence": "BAIXA", "description": "", "reasons": [], "warnings": [str(e)]}
        errors.append({"module": "regime", "error": str(e)})

    # ── Strategy ──
    try:
        strategy = determine_stock_strategy(stock_score, regime, trend, momentum, location, risk, supports, resistances)
    except Exception as e:
        strategy = {"strategy": "NO_TRADE", "action_without_position": "EVITAR", "action_with_position": "MANTER_COM_CAUTELA",
                    "confidence": "BAIXA", "main_reason": str(e)}
        errors.append({"module": "strategy", "error": str(e)})

    analysis = {
        "ticker": ticker,
        "preco_atual": current_price,
        "radar_lite_score": radar_score.get("radar_lite_score"),
        "status": radar_score.get("status"),
        "radar_modes": radar_score.get("radar_modes", []),
        "rsi": indicators.get("rsi"),
        "rsi_delta_3": indicators.get("rsi_delta_3"),
        "roc_10": indicators.get("roc_10"),
        "momentum": momentum,
        "supports": supports,
        "resistances": resistances,
        "trend": trend,
        "location": location,
        "risk": risk,
        "relative_strength": rel_str,
        "qsignal_score": stock_score,
        "regime": regime,
        "strategy": strategy,
        "reasons": stock_score.get("reasons", []),
        "warnings": stock_score.get("warnings", []),
        "errors": errors,
    }

    # ── Formatter ──
    try:
        analysis["formatted"] = format_stock_analysis_summary(analysis)
    except Exception as e:
        analysis["formatted"] = {"summary": "Erro ao formatar análise.", "bullish_points": [], "bearish_points": [], "operational_plan": ""}
        errors.append({"module": "formatter", "error": str(e)})

    return analysis

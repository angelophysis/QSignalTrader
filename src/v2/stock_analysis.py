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


def analyze_stock_v2(ticker: str, period: str = DEFAULT_PERIOD) -> dict:
    dh = YahooFinanceDataHandler(auto_adjust=True)

    try:
        df = dh.fetch_ohlc(ticker=ticker, period=period, interval="1d")
    except Exception as e:
        return {"ticker": ticker, "error": f"Erro ao buscar dados: {e}"}

    if df.empty or len(df) < 50:
        return {"ticker": ticker, "error": "Dados insuficientes (menos de 50 candles)"}

    indicators = calculate_radar_lite_indicators(df)
    radar_score = calculate_radar_lite_score(indicators)
    momentum = calculate_stock_momentum_score(df)
    current_price = float(df["close"].iloc[-1])
    sr = calculate_support_resistance_levels(df, current_price)
    supports = sr.get("supports", [])
    resistances = sr.get("resistances", [])

    # ── Sprint 2: new modules ──
    trend = calculate_trend_score(df)
    location = calculate_location_score(current_price, supports, resistances, indicators)
    risk = calculate_risk_score(df, indicators, supports)
    rel_str = calculate_relative_strength_score(df, ticker=ticker)
    stock_score = calculate_qsignal_stock_score(
        trend, momentum, location, rel_str, risk, df, indicators, supports, resistances,
        benchmark_ok=rel_str.get("benchmark") is not None,
    )
    regime = classify_stock_regime(trend, momentum, location, risk, radar_score.get("radar_modes"), indicators)
    strategy = determine_stock_strategy(stock_score, regime, trend, momentum, location, risk, supports, resistances)

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
    }
    analysis["formatted"] = format_stock_analysis_summary(analysis)
    return analysis

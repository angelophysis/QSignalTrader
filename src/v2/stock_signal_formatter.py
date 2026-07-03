from __future__ import annotations

from src.v2.config import REGIME_LABELS, STRATEGY_LABELS


def format_stock_analysis_summary(analysis: dict) -> dict:
    regime_key = analysis.get("regime", {}).get("regime", "INDEFINIDO")
    strategy_key = analysis.get("strategy", {}).get("strategy", "NO_TRADE")
    qs = analysis.get("qsignal_score", {})
    score_val = qs.get("qsignal_stock_score", 0)
    ticker = analysis.get("ticker", "?")

    regime_name = REGIME_LABELS.get(regime_key, regime_key)
    strategy_name = STRATEGY_LABELS.get(strategy_key, strategy_key)

    headline = f"{ticker} — {regime_name} | Score {score_val}/100"
    summary = f"{ticker} está em regime {regime_name.lower()}, com QSignalStockScore de {score_val}/100."
    strat = analysis.get("strategy", {})
    summary += f" Estratégia sugerida: {strategy_name.lower()}."

    bullish = list(analysis.get("reasons", []))[:5]
    bearish = list(analysis.get("warnings", []))[:5]

    op_plan = f"Sem posição: {strat.get('action_without_position', '—')}. "
    op_plan += f"Com posição: {strat.get('action_with_position', '—')}."

    risk_notes = []
    if strat.get("trigger_level"): risk_notes.append(f"Gatilho: {strat['trigger_level']:.2f}")
    if strat.get("invalidation_level"): risk_notes.append(f"Invalidação: {strat['invalidation_level']:.2f}")

    return {
        "headline": headline, "summary": summary,
        "bullish_points": bullish, "bearish_points": bearish,
        "operational_plan": op_plan, "risk_notes": risk_notes,
    }

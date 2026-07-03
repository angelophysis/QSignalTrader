from __future__ import annotations

from src.v2.config import CRYPTO_REGIME_LABELS, CRYPTO_STRATEGY_LABELS


def format_crypto_analysis_summary(analysis: dict) -> dict:
    regime_key = analysis.get("regime", {}).get("regime", "CRYPTO_INDEFINIDO")
    strategy_key = analysis.get("strategy", {}).get("strategy", "CRYPTO_NO_TRADE")
    qs = analysis.get("qsignal_score", {})
    score_val = qs.get("qsignal_crypto_score", 0)
    symbol = analysis.get("symbol", "?")

    regime_name = CRYPTO_REGIME_LABELS.get(regime_key, regime_key)
    strategy_name = CRYPTO_STRATEGY_LABELS.get(strategy_key, strategy_key)

    headline = f"{symbol} — {regime_name} | Score {score_val}/100"
    summary = f"{symbol} está em regime {regime_name.lower()}, com QSignalCryptoScore de {score_val}/100."
    summary += f" Estratégia: {strategy_name.lower()}."

    bullish = list(analysis.get("reasons", []))[:5]
    bearish = list(analysis.get("warnings", []))[:5]

    strat = analysis.get("strategy", {})
    op_plan = f"Sem posição: {strat.get('action_without_position', '—')}. Com posição: {strat.get('action_with_position', '—')}."

    risk_notes = []
    if strat.get("trigger_level"): risk_notes.append(f"Gatilho: {strat['trigger_level']:.2f}")
    if strat.get("invalidation_level"): risk_notes.append(f"Invalidação: {strat['invalidation_level']:.2f}")

    return {
        "headline": headline, "summary": summary,
        "bullish_points": bullish, "bearish_points": bearish,
        "operational_plan": op_plan, "risk_notes": risk_notes,
    }

from __future__ import annotations

import numpy as np
import pandas as pd

from src.data.fetch_crypto import get_crypto_data
from src.indicators.technicals import add_rsi, add_emas
from src.v2.config import CRYPTO_RADAR_RSI_MIN, CRYPTO_RADAR_RSI_MAX


def _safe(val):
    if val is None: return None
    if isinstance(val, np.generic): val = val.item()
    if isinstance(val, (int, float)):
        if np.isnan(val) or np.isinf(val): return None
        return float(val)
    return None


def _calculate_4h_indicators(df: pd.DataFrame) -> dict:
    if df.empty or len(df) < 30:
        return {"error": "Dados insuficientes", "candles": len(df)}
    df = add_rsi(df.copy(), period=14)
    df = add_emas(df.copy(), periods=[21, 50])
    latest = df.iloc[-1]

    rsi = _safe(latest.get("rsi"))
    rsi_3 = _safe(df["rsi"].iloc[-4]) if len(df) >= 4 else None
    rsi_5 = _safe(df["rsi"].iloc[-6]) if len(df) >= 6 else None

    close = _safe(latest.get("close"))
    ema21 = _safe(latest.get("ema_21"))
    ema50 = _safe(latest.get("ema_50"))

    close_10 = _safe(df["close"].iloc[-11]) if len(df) >= 11 else None
    roc_10 = round((close - close_10) / close_10 * 100, 2) if close and close_10 else None

    atr_val = _safe(latest.get("atr"))
    atr_pct = round(atr_val / close * 100, 2) if atr_val and close else None

    price_above_ema21 = bool(close and ema21 and close > ema21)
    price_above_ema50 = bool(close and ema50 and close > ema50)
    ema21_above_50 = bool(ema21 and ema50 and ema21 > ema50)

    return {
        "close": close, "rsi": rsi, "rsi_delta_3": round(rsi - rsi_3, 1) if rsi and rsi_3 else None,
        "rsi_delta_5": round(rsi - rsi_5, 1) if rsi and rsi_5 else None,
        "ema21": ema21, "ema50": ema50, "roc_10": roc_10, "atr_pct": atr_pct,
        "price_above_ema21": price_above_ema21, "price_above_ema50": price_above_ema50,
        "ema21_above_50": ema21_above_50, "candles": len(df),
    }


def run_crypto_radar_v2(symbols: list[str], min_score: float = 40, max_tickers: int = 50) -> dict:
    all_processed = []
    errors_list = []
    loaded = len(symbols)
    processed = 0

    for sym in symbols:
        try:
            df = get_crypto_data(symbol=sym, timeframe="4h", limit=150)
            ind = _calculate_4h_indicators(df)
            if "error" in ind:
                errors_list.append({"Symbol": sym, "Erro": ind["error"]})
                continue
            processed += 1

            score = 0
            reasons = []
            warnings_list = []

            rsi = ind.get("rsi")
            if rsi is not None:
                if CRYPTO_RADAR_RSI_MIN <= rsi <= CRYPTO_RADAR_RSI_MAX:
                    score += 30
                    reasons.append(f"RSI zona ideal ({rsi})")
                elif 40 <= rsi <= 55 and ind.get("rsi_delta_3") and ind["rsi_delta_3"] > 0:
                    score += 20
                    reasons.append(f"RSI recuperando ({rsi})")
                elif rsi > 75:
                    warnings_list.append(f"RSI esticado ({rsi})")
                    score += 5
                elif rsi < 35:
                    warnings_list.append(f"RSI muito fraco ({rsi})")
                    score += 5
                else:
                    score += 12

            rsi_d3 = ind.get("rsi_delta_3")
            rsi_d5 = ind.get("rsi_delta_5")
            mom = 0
            if rsi_d3 is not None and rsi_d3 > 0: mom += 10
            if rsi_d5 is not None and rsi_d5 > 0: mom += 8
            if ind.get("roc_10") is not None and ind["roc_10"] > 0: mom += 10
            score += min(30, mom)
            if mom >= 15: reasons.append("Momentum positivo")

            if ind.get("price_above_ema21"): score += 8
            if ind.get("price_above_ema50"): score += 7
            if ind.get("ema21_above_50"): score += 7

            score = min(100, max(0, score))

            modes = []
            if rsi is not None and CRYPTO_RADAR_RSI_MIN <= rsi <= CRYPTO_RADAR_RSI_MAX:
                if ind.get("price_above_ema50") and ind.get("ema21_above_50"):
                    modes.append("CRYPTO_TENDENCIA_SAUDAVEL")
            if rsi is not None and 40 <= rsi <= 55 and rsi_d3 is not None and rsi_d3 > 0:
                modes.append("CRYPTO_PULLBACK_DE_ALTA")
            if rsi is not None and rsi >= 45 and rsi_d3 is not None and rsi_d3 > 0 and ind.get("roc_10", 0) > -3:
                modes.append("CRYPTO_RECUPERACAO")

            all_processed.append({
                "Symbol": sym, "Price": ind.get("close"),
                "RadarScore": score, "RSI": rsi, "RSI_Delta_3": rsi_d3,
                "ROC_10": ind.get("roc_10"), "ATR_Pct": ind.get("atr_pct"),
                "Modos": ", ".join(modes), "Warnings": "; ".join(warnings_list),
            })
        except Exception as e:
            errors_list.append({"Symbol": sym, "Erro": str(e)[:100]})

    df_all = pd.DataFrame(all_processed)
    if not df_all.empty:
        df_all = df_all.sort_values("RadarScore", ascending=False).reset_index(drop=True)

    candidates = df_all[df_all["RadarScore"] >= min_score] if not df_all.empty else pd.DataFrame()
    rejected = df_all[df_all["RadarScore"] < min_score] if not df_all.empty else pd.DataFrame()

    return {
        "candidates": candidates.head(max_tickers) if not candidates.empty else candidates,
        "rejected": rejected.head(max_tickers) if not rejected.empty else rejected,
        "errors": pd.DataFrame(errors_list) if errors_list else pd.DataFrame(),
        "diagnostics": {"loaded": loaded, "processed": processed, "approved": len(candidates),
                        "rejected": len(rejected), "errors": len(errors_list)},
    }

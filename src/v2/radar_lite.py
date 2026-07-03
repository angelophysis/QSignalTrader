from __future__ import annotations

import math

import numpy as np
import pandas as pd

from src.data.yfinance_handler import YahooFinanceDataHandler
from src.indicators.technicals import add_atr, add_emas, add_rsi
from src.v2.config import (
    BREAKOUT_MAX_DIST_FROM_20D_HIGH,
    DEFAULT_MIN_SCORE,
    DEFAULT_PERIOD,
    DEFAULT_MAX_TICKERS,
    MAX_DISTANCE_EMA21_PCT,
    MIN_VOL_REL_BREAKOUT,
    RADAR_MODES,
    RSI_BREAKOUT_MAX,
    RSI_BREAKOUT_MIN,
    RSI_PULLBACK_MAX,
    RSI_PULLBACK_MIN,
    RSI_RECOVERY_CROSS,
    RSI_TREND_MAX,
    RSI_TREND_MIN,
    STATUS_THRESHOLDS,
    W_DATA_QUALITY,
    W_EXTENSION_RISK,
    W_MOMENTUM_TURN,
    W_RSI_ZONE,
    W_TREND_FILTER,
    W_VOLUME,
)


def _safe_float(val):
    if val is None:
        return None
    if isinstance(val, np.generic):
        val = val.item()
    if isinstance(val, (int, float)):
        if math.isnan(val) or math.isinf(val):
            return None
        return float(val)
    return None


def calculate_radar_lite_indicators(df: pd.DataFrame) -> dict:
    if df.empty or len(df) < 50:
        return {"error": "Dados insuficientes", "candles": len(df)}

    df = add_rsi(df.copy(), period=14)
    df = add_emas(df.copy(), periods=[21, 50, 200])
    df = add_atr(df.copy(), period=14)

    latest = df.iloc[-1]
    close = _safe_float(latest.get("close"))

    rsi = _safe_float(latest.get("rsi"))
    rsi_3 = _safe_float(df["rsi"].iloc[-4]) if len(df) >= 4 else None
    rsi_5 = _safe_float(df["rsi"].iloc[-6]) if len(df) >= 6 else None
    rsi_delta_3 = round(rsi - rsi_3, 1) if rsi is not None and rsi_3 is not None else None
    rsi_delta_5 = round(rsi - rsi_5, 1) if rsi is not None and rsi_5 is not None else None

    ema21 = _safe_float(latest.get("ema_21"))
    ema50 = _safe_float(latest.get("ema_50"))
    ema200 = _safe_float(latest.get("ema_200"))

    close_10 = _safe_float(df["close"].iloc[-11]) if len(df) >= 11 else None
    close_20 = _safe_float(df["close"].iloc[-21]) if len(df) >= 21 else None
    roc_10 = round((close - close_10) / close_10 * 100, 2) if close and close_10 else None
    roc_20 = round((close - close_20) / close_20 * 100, 2) if close and close_20 else None

    atr = _safe_float(latest.get("atr"))
    atr_pct = round(atr / close * 100, 2) if atr and close else None

    volume = _safe_float(latest.get("volume"))
    vol_mean_20 = _safe_float(df["volume"].rolling(20).mean().iloc[-1]) if "volume" in df.columns else None
    vol_rel = round(volume / vol_mean_20, 2) if volume and vol_mean_20 else None

    dist_ema21 = round((close / ema21 - 1) * 100, 2) if close and ema21 else None
    dist_ema50 = round((close / ema50 - 1) * 100, 2) if close and ema50 else None
    max_high_20 = _safe_float(df["high"].rolling(20).max().iloc[-1])
    dist_max20 = round((close / max_high_20 - 1) * 100, 2) if close and max_high_20 else None
    min_low_20 = _safe_float(df["low"].rolling(20).min().iloc[-1])

    price_above_ema21 = bool(ema21 and close and close > ema21) if ema21 and close else False
    price_above_ema50 = bool(ema50 and close and close > ema50) if ema50 and close else False
    price_above_ema200 = bool(ema200 and close and close > ema200) if ema200 and close else False
    ema21_above_ema50 = bool(ema21 and ema50 and ema21 > ema50) if ema21 and ema50 else False

    close_5_ago = _safe_float(df["close"].iloc[-6]) if len(df) >= 6 else None
    close_above_5d = bool(close and close_5_ago and close > close_5_ago) if close and close_5_ago else False

    return {
        "close": close, "rsi": rsi, "rsi_delta_3": rsi_delta_3, "rsi_delta_5": rsi_delta_5,
        "ema21": ema21, "ema50": ema50, "ema200": ema200,
        "roc_10": roc_10, "roc_20": roc_20,
        "atr": atr, "atr_pct": atr_pct,
        "vol_rel": vol_rel,
        "dist_ema21_pct": dist_ema21, "dist_ema50_pct": dist_ema50, "dist_max20_pct": dist_max20,
        "max_high_20": max_high_20, "min_low_20": min_low_20,
        "price_above_ema21": price_above_ema21, "price_above_ema50": price_above_ema50,
        "price_above_ema200": price_above_ema200, "ema21_above_ema50": ema21_above_ema50,
        "close_above_5d": close_above_5d,
        "candles": len(df),
    }


def calculate_radar_lite_score(indicators: dict) -> dict:
    if "error" in indicators:
        return {"radar_lite_score": 0, "radar_modes": [], "status": "IGNORAR", "reasons": [], "warnings": [indicators["error"]]}

    score = 0
    reasons = []
    warnings_list = []

    rsi = indicators.get("rsi")
    rsi_d3 = indicators.get("rsi_delta_3")
    rsi_d5 = indicators.get("rsi_delta_5")

    rsi_zone = 0
    if rsi is not None:
        if RSI_TREND_MIN <= rsi <= RSI_TREND_MAX: rsi_zone = 25; reasons.append(f"RSI em zona ideal ({rsi})")
        elif RSI_PULLBACK_MIN <= rsi <= RSI_RECOVERY_CROSS and rsi_d3 is not None and rsi_d3 > 0: rsi_zone = 22; reasons.append(f"RSI em pullback com delta positivo ({rsi})")
        elif 55 <= rsi <= 72 and indicators.get("dist_max20_pct") is not None and indicators["dist_max20_pct"] >= -3: rsi_zone = 20; reasons.append(f"RSI breakout ({rsi})")
        elif 45 <= rsi <= 55 and rsi_d3 is not None and rsi_d3 > 0: rsi_zone = 18; reasons.append(f"RSI cruzando para cima ({rsi})")
        elif rsi > 75: rsi_zone = 3; warnings_list.append(f"RSI esticado ({rsi})")
        elif rsi < 40: rsi_zone = rsi_d3 > 0 if rsi_d3 else 0 and 10; warnings_list.append(f"RSI fraco ({rsi})")
        else: rsi_zone = 10
    score += rsi_zone

    mom_turn = 0
    if rsi_d3 is not None and rsi_d3 > 0: mom_turn += 6
    if rsi_d5 is not None and rsi_d5 > 0: mom_turn += 5
    if indicators.get("roc_10") is not None and indicators["roc_10"] > 0: mom_turn += 6
    if indicators.get("roc_20") is not None and indicators["roc_20"] > 0: mom_turn += 4
    if indicators.get("close_above_5d"): mom_turn += 4
    score += min(W_MOMENTUM_TURN, mom_turn)
    if mom_turn >= 15: reasons.append(f"Momentum turn positivo ({mom_turn}/{W_MOMENTUM_TURN})")

    trend = 0
    if indicators.get("price_above_ema21"): trend += 5
    if indicators.get("price_above_ema50"): trend += 5
    if indicators.get("ema21_above_ema50"): trend += 5
    if indicators.get("price_above_ema200"): trend += 5
    score += min(W_TREND_FILTER, trend)
    if trend >= 15: reasons.append(f"Filtro de tendência forte ({trend}/{W_TREND_FILTER})")

    ext = 0
    dist = indicators.get("dist_ema21_pct")
    if dist is not None:
        if -3 <= dist <= 5: ext = 15
        elif 5 < dist <= 8: ext = 11
        elif 8 < dist <= 12: ext = 6; warnings_list.append(f"Preço esticado da EMA21 ({dist}%)")
        elif dist > 12: ext = 1; warnings_list.append(f"Preço muito esticado da EMA21 ({dist}%)")
        elif dist < -8: ext = 4; reasons.append("Possível pullback")
        else: ext = 8
    score += ext

    vol = 0
    vr = indicators.get("vol_rel")
    if vr is not None:
        if vr >= 1.5: vol = 10; reasons.append(f"Volume relativo alto ({vr}x)")
        elif vr >= 1.2: vol = 8
        elif vr >= 0.8: vol = 5
        elif vr > 0: vol = 2; warnings_list.append(f"Volume baixo ({vr}x)")
    score += vol

    dq = 5
    if indicators.get("candles", 0) < 100: dq -= 2; warnings_list.append("Poucos candles")
    if indicators.get("vol_rel") is None: dq -= 2; warnings_list.append("Sem dados de volume")
    score += dq

    score = min(100, max(0, score))

    status = "IGNORAR"
    for (lo, hi), label in STATUS_THRESHOLDS.items():
        if lo <= score <= hi:
            status = label
            break

    modes = detect_radar_modes(indicators, {
        "rsi_zone_score": rsi_zone, "momentum_turn_score": mom_turn, "trend_filter_score": trend,
        "extension_risk_score": ext, "volume_score": vol, "data_quality_score": dq,
    })

    return {
        "radar_lite_score": score,
        "rsi_zone_score": rsi_zone, "momentum_turn_score": mom_turn, "trend_filter_score": trend,
        "extension_risk_score": ext, "volume_score": vol, "data_quality_score": dq,
        "radar_modes": modes, "status": status,
        "reasons": reasons, "warnings": warnings_list,
    }


def detect_radar_modes(indicators: dict, scores: dict) -> list[str]:
    modes = []
    rsi = indicators.get("rsi")

    if rsi is not None and RSI_TREND_MIN <= rsi <= RSI_TREND_MAX:
        if (indicators.get("price_above_ema50") and indicators.get("ema21_above_ema50")
                and indicators.get("dist_ema21_pct") is not None and abs(indicators["dist_ema21_pct"]) <= MAX_DISTANCE_EMA21_PCT):
            modes.append("TENDENCIA_SAUDAVEL")

    if rsi is not None and RSI_PULLBACK_MIN <= rsi <= RSI_PULLBACK_MAX:
        d3 = indicators.get("rsi_delta_3")
        d5 = indicators.get("rsi_delta_5")
        dist = indicators.get("dist_ema21_pct")
        if (d3 is not None and d3 > 0) or (d5 is not None and d5 > 0):
            if indicators.get("price_above_ema50") or (dist is not None and -5 <= dist <= 3):
                if not modes:
                    modes.append("PULLBACK_DE_ALTA")

    if rsi is not None and RSI_BREAKOUT_MIN <= rsi <= RSI_BREAKOUT_MAX:
        dist_max = indicators.get("dist_max20_pct")
        if dist_max is not None and dist_max >= -BREAKOUT_MAX_DIST_FROM_20D_HIGH:
            if indicators.get("roc_10") is not None and indicators["roc_10"] > 0:
                vr = indicators.get("vol_rel")
                if vr is not None and vr >= MIN_VOL_REL_BREAKOUT:
                    dist_e21 = indicators.get("dist_ema21_pct")
                    if dist_e21 is None or dist_e21 <= MAX_DISTANCE_EMA21_PCT:
                        modes.append("BREAKOUT_SETUP")

    if rsi is not None and rsi >= RSI_RECOVERY_CROSS and rsi <= RSI_TREND_MIN:
        d3 = indicators.get("rsi_delta_3")
        if d3 is not None and d3 > 0:
            roc10 = indicators.get("roc_10")
            if roc10 is not None and roc10 > -3:
                modes.append("RECUPERACAO_INICIAL")

    return modes


def run_stock_radar_v2(
    tickers: list[str],
    period: str = DEFAULT_PERIOD,
    min_score: float = DEFAULT_MIN_SCORE,
    mode_filter: str | None = None,
    max_tickers: int = DEFAULT_MAX_TICKERS,
) -> dict:
    dh = YahooFinanceDataHandler(auto_adjust=True)
    all_processed = []
    errors = []
    loaded = len(tickers)
    processed = 0

    for ticker in tickers:
        try:
            df = dh.fetch_ohlc(ticker=ticker, period=period, interval="1d")
            indicators = calculate_radar_lite_indicators(df)
            score_data = calculate_radar_lite_score(indicators)
            processed += 1

            row = {
                "Ticker": ticker,
                "Preco": indicators.get("close"),
                "Status": score_data["status"],
                "RadarLiteScore": score_data["radar_lite_score"],
                "Modos": ", ".join(score_data.get("radar_modes", [])),
                "RSI": indicators.get("rsi"),
                "RSI_Delta_3": indicators.get("rsi_delta_3"),
                "ROC_10": indicators.get("roc_10"),
                "ROC_20": indicators.get("roc_20"),
                "Preco_EMA50": "✅" if indicators.get("price_above_ema50") else "❌",
                "EMA21_EMA50": "✅" if indicators.get("ema21_above_ema50") else "❌",
                "Dist_EMA21_Pct": indicators.get("dist_ema21_pct"),
                "Vol_Rel": indicators.get("vol_rel"),
                "Dist_Max20_Pct": indicators.get("dist_max20_pct"),
                "Warnings": "; ".join(score_data.get("warnings", [])),
            }
            all_processed.append(row)
        except Exception as e:
            errors.append({"Ticker": ticker, "Erro": str(e)[:100]})

    df_all = pd.DataFrame(all_processed)
    if not df_all.empty:
        df_all = df_all.sort_values("RadarLiteScore", ascending=False).reset_index(drop=True)

    candidates = df_all[df_all["RadarLiteScore"] >= min_score] if not df_all.empty else pd.DataFrame()
    if mode_filter and not candidates.empty:
        candidates = candidates[candidates["Modos"].str.contains(mode_filter, na=False)]

    rejected = df_all[df_all["RadarLiteScore"] < min_score] if not df_all.empty else pd.DataFrame()

    candidates = candidates.head(max_tickers) if not candidates.empty else candidates
    rejected_top = rejected.head(max_tickers) if not rejected.empty else rejected

    return {
        "candidates": candidates,
        "rejected": rejected_top,
        "errors": pd.DataFrame(errors) if errors else pd.DataFrame(),
        "diagnostics": {
            "loaded": loaded,
            "processed": processed,
            "approved": len(candidates),
            "rejected": len(rejected),
            "errors": len(errors),
        },
    }

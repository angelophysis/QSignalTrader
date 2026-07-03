from __future__ import annotations

import math

import numpy as np
import pandas as pd

from src.data.yfinance_handler import YahooFinanceDataHandler
from src.indicators.technicals import add_atr, add_emas, add_rsi
from src.v2.config import (
    BREAKOUT_MAX_DIST_FROM_20D_HIGH,
    CLUSTER_PCT,
    DEFAULT_PERIOD,
    MAX_LEVELS_EACH_SIDE,
    SWING_WINDOW,
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


def _detect_swing_points(high: pd.Series, low: pd.Series, window: int = SWING_WINDOW):
    swing_highs = []
    swing_lows = []
    n = len(high)
    for i in range(window, n - window):
        h = high.iloc[i]
        l = low.iloc[i]
        if all(h >= high.iloc[i - j] for j in range(1, window + 1)) and all(h >= high.iloc[i + j] for j in range(1, window + 1)):
            swing_highs.append({"price": round(float(h), 2), "index": i, "date": str(high.index[i])[:10]})
        if all(l <= low.iloc[i - j] for j in range(1, window + 1)) and all(l <= low.iloc[i + j] for j in range(1, window + 1)):
            swing_lows.append({"price": round(float(l), 2), "index": i, "date": str(low.index[i])[:10]})
    return swing_highs, swing_lows


def _cluster_levels(raw_levels: list[dict], cluster_pct: float = CLUSTER_PCT) -> list[dict]:
    if not raw_levels:
        return []
    sorted_levels = sorted(raw_levels, key=lambda x: x["price"])
    clusters = []
    current = {"price": sorted_levels[0]["price"], "sources": [sorted_levels[0]],
               "count": 1, "recency": sorted_levels[0].get("index", 0)}
    for level in sorted_levels[1:]:
        pct_diff = abs(level["price"] - current["price"]) / current["price"] * 100
        if pct_diff < cluster_pct:
            current["price"] = (current["price"] * current["count"] + level["price"]) / (current["count"] + 1)
            current["sources"].append(level)
            current["count"] += 1
            current["recency"] = max(current["recency"], level.get("index", 0))
        else:
            clusters.append(current)
            current = {"price": level["price"], "sources": [level], "count": 1, "recency": level.get("index", 0)}
    clusters.append(current)
    return clusters


def _compute_strength(cluster: dict, current_price: float, total_candles: int, has_ema: bool = False) -> int:
    score = 40
    score += min(30, cluster["count"] * 15)
    recency_ratio = cluster["recency"] / total_candles if total_candles > 0 else 0.5
    score += min(15, int(recency_ratio * 15))
    if has_ema:
        score += 10
    return min(100, max(0, score))


def calculate_support_resistance_levels(
    df: pd.DataFrame, current_price: float, max_levels: int = MAX_LEVELS_EACH_SIDE
) -> dict:
    if df.empty or len(df) < 20:
        return {"supports": [], "resistances": [], "warnings": ["Dados insuficientes para calcular níveis."]}

    n = len(df)
    high = df["high"]
    low = df["low"]
    close = df["close"]

    raw_levels = []

    swing_highs, swing_lows = _detect_swing_points(high, low)
    for s in swing_highs:
        raw_levels.append({"price": s["price"], "type": "swing_high", "index": s["index"], "date": s["date"]})
    for s in swing_lows:
        raw_levels.append({"price": s["price"], "type": "swing_low", "index": s["index"], "date": s["date"]})

    max_20 = _safe_float(high.rolling(20).max().iloc[-1])
    min_20 = _safe_float(low.rolling(20).min().iloc[-1])
    max_50 = _safe_float(high.rolling(50).max().iloc[-1]) if n >= 50 else None
    min_50 = _safe_float(low.rolling(50).min().iloc[-1]) if n >= 50 else None

    for p, nome in [(max_20, "max20"), (min_20, "min20"), (max_50, "max50"), (min_50, "min50")]:
        if p is not None:
            raw_levels.append({"price": round(p, 2), "type": nome, "index": n - 1, "date": ""})

    df_ema = add_emas(df.copy(), periods=[21, 50, 200])
    for col, tipo in [("ema_21", "EMA21"), ("ema_50", "EMA50"), ("ema_200", "EMA200")]:
        v = _safe_float(df_ema[col].iloc[-1])
        if v is not None:
            raw_levels.append({"price": round(v, 2), "type": tipo, "index": n - 1, "date": ""})

    hh = _safe_float(high.max())
    ll = _safe_float(low.min())
    if hh and ll and hh != ll:
        for pct in [0.0, 0.382, 0.5, 0.618, 1.0]:
            fib = round(ll + (hh - ll) * pct, 2)
            raw_levels.append({"price": fib, "type": f"fib_{pct}", "index": 0, "date": ""})

    rounding = 0.01 if current_price < 10 else 0.1 if current_price < 100 else 1.0 if current_price < 1000 else 10.0
    rounded = round(current_price / rounding) * rounding
    raw_levels.append({"price": rounded, "type": "round", "index": n - 1, "date": ""})

    clusters = _cluster_levels(raw_levels)
    supports_list = []
    resistances_list = []

    for c in clusters:
        price = round(c["price"], 2)
        has_ema = any("EMA" in s.get("type", "") for s in c["sources"])
        strength = _compute_strength(c, current_price, n, has_ema)
        dist_pct = round((price - current_price) / current_price * 100, 2)
        source_types = [s["type"] for s in c["sources"]]

        level = {
            "price": price,
            "strength": strength,
            "distance_pct": dist_pct,
            "sources": source_types,
        }
        if price < current_price:
            supports_list.append(level)
        elif price > current_price:
            resistances_list.append(level)

    supports_list.sort(key=lambda x: x["price"], reverse=True)
    resistances_list.sort(key=lambda x: x["price"])

    supports = []
    for i, s in enumerate(supports_list[:max_levels]):
        s["label"] = f"S{i + 1}"
        supports.append(s)
    resistances = []
    for i, r in enumerate(resistances_list[:max_levels]):
        r["label"] = f"R{i + 1}"
        resistances.append(r)

    warnings = []
    if len(supports) < max_levels:
        warnings.append(f"Apenas {len(supports)} suportes encontrados.")
    if len(resistances) < max_levels:
        warnings.append(f"Apenas {len(resistances)} resistências encontradas.")

    return {"supports": supports, "resistances": resistances, "warnings": warnings if warnings else []}

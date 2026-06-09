from __future__ import annotations

import numpy as np
import pandas as pd


def add_emas(df: pd.DataFrame, periods: list[int] | None = None) -> pd.DataFrame:
    if periods is None:
        periods = [8, 21, 50, 100, 200]

    out = df.copy()
    for p in periods:
        out[f"ema_{p}"] = out["close"].ewm(span=p, adjust=False).mean()
    return out


def add_rsi(df: pd.DataFrame, period: int = 14, price_col: str = "close") -> pd.DataFrame:
    out = df.copy()
    delta = out[price_col].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)

    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    out["rsi"] = 100.0 - (100.0 / (1.0 + rs))
    out["rsi"] = out["rsi"].fillna(50.0)
    return out


def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    out = df.copy()
    high = out["high"]
    low = out["low"]
    close_prev = out["close"].shift(1)

    tr1 = high - low
    tr2 = (high - close_prev).abs()
    tr3 = (low - close_prev).abs()

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    out["atr"] = true_range.ewm(alpha=1 / period, adjust=False).mean()
    return out


def add_fibonacci_pivots(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    h = out["high"]
    l = out["low"]
    c = out["close"]

    out["pivot"] = (h + l + c) / 3.0

    range_val = h - l
    out["r1"] = out["pivot"] + range_val * 0.382
    out["r2"] = out["pivot"] + range_val * 0.618
    out["r3"] = out["pivot"] + range_val * 1.0
    out["s1"] = out["pivot"] - range_val * 0.382
    out["s2"] = out["pivot"] - range_val * 0.618
    out["s3"] = out["pivot"] - range_val * 1.0
    return out

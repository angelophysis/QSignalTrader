from __future__ import annotations

import numpy as np

from src.data.yfinance_handler import YahooFinanceDataHandler
from src.v2.config import RS_GOOD


def _safe(val):
    if val is None: return None
    if isinstance(val, np.generic): val = val.item()
    if isinstance(val, (int, float)):
        if np.isnan(val) or np.isinf(val): return None
        return float(val)
    return None


def _get_benchmark(ticker: str) -> str:
    return "^GSPC"


_FALLBACK_BENCHMARKS = ["SPY"]


def _fetch_benchmark(name: str) -> tuple:
    dh = YahooFinanceDataHandler(auto_adjust=True)
    for bm in [name] + _FALLBACK_BENCHMARKS:
        if bm == name:
            continue
        try:
            df = dh.fetch_ohlc(ticker=bm, period="1y", interval="1d")
            if df is not None and not df.empty and len(df) >= 21:
                return df, bm
        except Exception:
            continue
    # Try original name too
    try:
        df = dh.fetch_ohlc(ticker=name, period="1y", interval="1d")
        if df is not None and not df.empty and len(df) >= 21:
            return df, name
    except Exception:
        pass
    return None, None


def calculate_relative_strength_score(stock_df, benchmark_df=None, ticker: str | None = None) -> dict:
    if stock_df is None or stock_df.empty or len(stock_df) < 50:
        return {"relative_strength_score": 50, "classification": "NEUTRA",
                "reasons": [], "warnings": ["Dados insuficientes para RS"]}

    bench_df = benchmark_df
    bench_name = "^GSPC"

    if bench_df is None:
        bench_df, actual_bench = _fetch_benchmark(bench_name)
        if actual_bench:
            bench_name = actual_bench

    stock_close = stock_df["close"]
    stock_ret20 = _safe((stock_close.iloc[-1] / stock_close.iloc[-21] - 1) * 100) if len(stock_close) >= 21 else None
    stock_ret60 = _safe((stock_close.iloc[-1] / stock_close.iloc[-61] - 1) * 100) if len(stock_close) >= 61 else None

    if bench_df is not None and not bench_df.empty and len(bench_df) >= 21:
        bench_close = bench_df["close"]
        bench_ret20 = _safe((bench_close.iloc[-1] / bench_close.iloc[-21] - 1) * 100) if len(bench_close) >= 21 else None
        bench_ret60 = _safe((bench_close.iloc[-1] / bench_close.iloc[-61] - 1) * 100) if len(bench_close) >= 61 else None
    else:
        return {"relative_strength_score": 50, "classification": "NEUTRA", "benchmark": bench_name,
                "reasons": [], "warnings": ["Benchmark indisponível. RS Score neutro."]}

    rel20 = round(stock_ret20 - bench_ret20, 2) if stock_ret20 is not None and bench_ret20 is not None else None
    rel60 = round(stock_ret60 - bench_ret60, 2) if stock_ret60 is not None and bench_ret60 is not None else None

    score = 0
    reasons = []
    warnings_list = []

    if rel20 is not None:
        if rel20 > 5: score += 35; reasons.append(f"Retorno relativo 20D forte (+{rel20}%)")
        elif rel20 > 0: score += 25; reasons.append(f"Supera benchmark em 20D (+{rel20}%)")
        elif rel20 < -5: warnings_list.append(f"Abaixo do benchmark em 20D ({rel20}%)")

    if rel60 is not None:
        if rel60 > 10: score += 35
        elif rel60 > 0: score += 25
        elif rel60 < -10: warnings_list.append(f"Abaixo do benchmark em 60D ({rel60}%)")

    # Ratio slope
    if len(stock_close) >= 21 and len(bench_close) >= 21:
        norm_stock = stock_close / stock_close.iloc[-21]
        norm_bench = bench_close / bench_close.iloc[-21]
        ratio = norm_stock / norm_bench
        ratio_slope = _safe(ratio.iloc[-1] - ratio.iloc[-21])
        if ratio_slope and ratio_slope > 0: score += 20; reasons.append("Força relativa subindo")

    # Bonus: stock positive while benchmark negative in 20D
    if stock_ret20 is not None and stock_ret20 > 0 and bench_ret20 is not None and bench_ret20 < 0:
        score += 10; reasons.append("Ação sobe enquanto benchmark cai")

    score = min(100, max(0, score))

    if score >= 80: cls = "LIDER"
    elif score >= RS_GOOD: cls = "FORTE"
    elif score >= 45: cls = "NEUTRA"
    elif score >= 25: cls = "FRACA"
    else: cls = "MUITO_FRACA"

    return {
        "relative_strength_score": score, "classification": cls, "benchmark": bench_name,
        "stock_return_20d": stock_ret20, "benchmark_return_20d": bench_ret20,
        "stock_return_60d": stock_ret60, "benchmark_return_60d": bench_ret60,
        "relative_return_20d": rel20, "relative_return_60d": rel60,
        "reasons": reasons, "warnings": warnings_list,
    }

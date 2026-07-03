from __future__ import annotations

import numpy as np

from src.data.fetch_crypto import get_crypto_data


def _safe(val):
    if val is None: return None
    if isinstance(val, np.generic): val = val.item()
    if isinstance(val, (int, float)):
        if np.isnan(val) or np.isinf(val): return None
        return float(val)
    return None


def calculate_crypto_relative_strength_score(crypto_df, btc_df=None, symbol: str | None = None) -> dict:
    is_btc = symbol and symbol.upper().replace(" ", "").replace("/", "") in ("BTCUSDT", "BTC/USDT", "BTC-USD", "BTCUSD")

    if is_btc:
        return {
            "btc_relative_strength_score": 50, "classification": "BENCHMARK",
            "benchmark": "BTC/USDT", "reasons": [], "warnings": ["BTC é o benchmark cripto. RS neutro."],
        }

    # Fetch BTC data if not provided
    if btc_df is None:
        try:
            btc_df = get_crypto_data(symbol="BTC/USDT", timeframe="1d", limit=300)
        except Exception:
            return {
                "btc_relative_strength_score": 50, "classification": "NEUTRA",
                "benchmark": "BTC/USDT", "reasons": [], "warnings": ["BTC benchmark indisponível."],
            }

    if crypto_df is None or crypto_df.empty or len(crypto_df) < 50:
        return {
            "btc_relative_strength_score": 50, "classification": "NEUTRA",
            "benchmark": "BTC/USDT", "reasons": [], "warnings": ["Dados insuficientes para RS cripto."],
        }

    crypto_close = crypto_df["close"]
    btc_close = btc_df["close"]

    crypto_ret20 = _safe((crypto_close.iloc[-1] / crypto_close.iloc[-21] - 1) * 100) if len(crypto_close) >= 21 else None
    crypto_ret60 = _safe((crypto_close.iloc[-1] / crypto_close.iloc[-61] - 1) * 100) if len(crypto_close) >= 61 else None
    btc_ret20 = _safe((btc_close.iloc[-1] / btc_close.iloc[-21] - 1) * 100) if len(btc_close) >= 21 else None
    btc_ret60 = _safe((btc_close.iloc[-1] / btc_close.iloc[-61] - 1) * 100) if len(btc_close) >= 61 else None

    rel20 = round(crypto_ret20 - btc_ret20, 2) if crypto_ret20 is not None and btc_ret20 is not None else None
    rel60 = round(crypto_ret60 - btc_ret60, 2) if crypto_ret60 is not None and btc_ret60 is not None else None

    score = 0
    reasons = []
    warnings_list = []

    if rel20 is not None:
        if rel20 > 10: score += 35; reasons.append(f"Força relativa 20D forte (+{rel20}% vs BTC)")
        elif rel20 > 0: score += 25; reasons.append(f"Supera BTC em 20D (+{rel20}%)")
        elif rel20 < -10: warnings_list.append(f"Fraco vs BTC em 20D ({rel20}%)")

    if rel60 is not None:
        if rel60 > 20: score += 35
        elif rel60 > 0: score += 25
        elif rel60 < -20: warnings_list.append(f"Fraco vs BTC em 60D ({rel60}%)")

    if crypto_ret20 is not None and crypto_ret20 > 0 and btc_ret20 is not None and btc_ret20 < 0:
        score += 10; reasons.append("Sobe enquanto BTC cai")

    score = min(100, max(0, score))

    if score >= 80: cls = "LIDER"
    elif score >= 60: cls = "FORTE"
    elif score >= 45: cls = "NEUTRA"
    elif score >= 25: cls = "FRACA"
    else: cls = "MUITO_FRACA"

    return {
        "btc_relative_strength_score": score, "classification": cls,
        "benchmark": "BTC/USDT", "asset_return_20d": crypto_ret20, "btc_return_20d": btc_ret20,
        "asset_return_60d": crypto_ret60, "btc_return_60d": btc_ret60,
        "relative_return_20d": rel20, "relative_return_60d": rel60,
        "reasons": reasons, "warnings": warnings_list,
    }

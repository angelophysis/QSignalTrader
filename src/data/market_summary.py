from __future__ import annotations

import yfinance as yf

from src.data.fetch_crypto import fetch_crypto_ticker_with_metadata


def _safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        f = float(val)
        if f != f or f == float('inf') or f == float('-inf'):
            return None
        return f
    except (ValueError, TypeError):
        return None


def get_crypto_market_summary(symbol: str, exchange_name: str = "okx") -> dict:
    try:
        result = fetch_crypto_ticker_with_metadata(symbol, exchange_name=exchange_name)
        ticker = result.ticker

        preco = _safe_float(ticker.get("last"))
        pct = _safe_float(ticker.get("percentage"))
        if pct is None:
            open_p = _safe_float(ticker.get("open"))
            if preco is not None and open_p is not None and open_p != 0:
                pct = round((preco - open_p) / open_p * 100, 2)

        low = _safe_float(ticker.get("low"))
        high = _safe_float(ticker.get("high"))
        return {
            "preco_atual": round(preco, 2) if preco else None,
            "variacao_24h_percent": pct,
            "min_24h": round(low, 2) if low else None,
            "max_24h": round(high, 2) if high else None,
            "periodo": "24h",
            "fonte": f"ccxt/{result.exchange}/{result.market_type}",
            "exchange": result.exchange,
            "market_type": result.market_type,
            "resolved_symbol": result.resolved_symbol,
            "fallback_used": result.fallback_used,
            "attempts": result.attempts,
        }
    except Exception as exc:
        summary = _empty_summary("24h", "ccxt")
        summary["erro"] = str(exc)[:240]
        summary["attempts"] = getattr(exc, "attempts", [])
        return summary


def get_stock_market_summary(symbol: str) -> dict:
    try:
        tk = yf.Ticker(symbol)
        hist = tk.history(period="2d", interval="1d")
        if hist.empty or len(hist) < 1:
            return _empty_summary("último pregão", "yfinance")

        ultimo = hist.iloc[-1]
        preco = _safe_float(ultimo.get("Close"))
        low = _safe_float(ultimo.get("Low"))
        high = _safe_float(ultimo.get("High"))

        pct = None
        if len(hist) >= 2:
            anterior = _safe_float(hist.iloc[-2].get("Close"))
            if preco is not None and anterior is not None and anterior != 0:
                pct = round((preco - anterior) / anterior * 100, 2)

        return {
            "preco_atual": round(preco, 2) if preco else None,
            "variacao_24h_percent": pct,
            "min_24h": round(low, 2) if low else None,
            "max_24h": round(high, 2) if high else None,
            "periodo": "último pregão",
            "fonte": "yfinance",
        }
    except Exception:
        return _empty_summary("último pregão", "yfinance")


def _empty_summary(periodo: str, fonte: str) -> dict:
    return {
        "preco_atual": None,
        "variacao_24h_percent": None,
        "min_24h": None,
        "max_24h": None,
        "periodo": periodo,
        "fonte": fonte,
    }


def get_market_summary(symbol: str, tipo: str) -> dict:
    if tipo == "cripto":
        return get_crypto_market_summary(symbol)
    return get_stock_market_summary(symbol)

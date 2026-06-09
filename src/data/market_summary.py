from __future__ import annotations

import ccxt
import yfinance as yf


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


def get_crypto_market_summary(symbol: str, exchange_name: str = "binance") -> dict:
    try:
        exchange_class = getattr(ccxt, exchange_name)
        exchange = exchange_class({"enableRateLimit": True})
        ticker = exchange.fetch_ticker(symbol)

        preco = _safe_float(ticker.get("last"))
        pct = _safe_float(ticker.get("percentage"))
        if pct is None:
            open_p = _safe_float(ticker.get("open"))
            if preco is not None and open_p is not None and open_p != 0:
                pct = round((preco - open_p) / open_p * 100, 2)

        return {
            "preco_atual": round(preco, 2) if preco else None,
            "variacao_24h_percent": pct,
            "min_24h": round(_safe_float(ticker.get("low")), 2) if _safe_float(ticker.get("low")) else None,
            "max_24h": round(_safe_float(ticker.get("high")), 2) if _safe_float(ticker.get("high")) else None,
            "periodo": "24h",
            "fonte": "ccxt",
        }
    except Exception:
        return _empty_summary("24h", "ccxt")


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

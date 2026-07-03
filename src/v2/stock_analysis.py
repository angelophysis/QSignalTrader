from __future__ import annotations

from src.data.yfinance_handler import YahooFinanceDataHandler
from src.v2.config import DEFAULT_PERIOD
from src.v2.momentum import calculate_stock_momentum_score
from src.v2.radar_lite import calculate_radar_lite_indicators, calculate_radar_lite_score
from src.v2.support_resistance import calculate_support_resistance_levels


def analyze_stock_v2(ticker: str, period: str = DEFAULT_PERIOD) -> dict:
    dh = YahooFinanceDataHandler(auto_adjust=True)

    try:
        df = dh.fetch_ohlc(ticker=ticker, period=period, interval="1d")
    except Exception as e:
        return {"ticker": ticker, "error": f"Erro ao buscar dados: {e}"}

    if df.empty or len(df) < 50:
        return {"ticker": ticker, "error": "Dados insuficientes (menos de 50 candles)"}

    indicators = calculate_radar_lite_indicators(df)
    score_data = calculate_radar_lite_score(indicators)
    momentum = calculate_stock_momentum_score(df)

    current_price = float(df["close"].iloc[-1])
    sr = calculate_support_resistance_levels(df, current_price)

    leitura_parts = []
    if score_data.get("radar_modes"):
        modos_nomes = [m for m in score_data["radar_modes"]]
        leitura_parts.append(f"Ativo classificado como: {', '.join(modos_nomes)}.")

    if momentum.get("classification") in ("FORTE", "FAVORAVEL"):
        leitura_parts.append(f"Momentum {momentum['classification'].lower()}.")
    elif momentum.get("classification") == "CONTRA":
        leitura_parts.append("Momentum contraindicado.")

    if sr.get("supports") and sr.get("resistances"):
        s1 = sr["supports"][0]["price"] if sr["supports"] else None
        r1 = sr["resistances"][0]["price"] if sr["resistances"] else None
        if s1 and r1:
            leitura_parts.append(f"Suporte imediato em {s1}, resistência em {r1}.")

    return {
        "ticker": ticker,
        "preco_atual": current_price,
        "radar_lite_score": score_data.get("radar_lite_score"),
        "status": score_data.get("status"),
        "radar_modes": score_data.get("radar_modes", []),
        "rsi": indicators.get("rsi"),
        "rsi_delta_3": indicators.get("rsi_delta_3"),
        "roc_10": indicators.get("roc_10"),
        "momentum": momentum,
        "supports": sr.get("supports", []),
        "resistances": sr.get("resistances", []),
        "reasons": score_data.get("reasons", []),
        "warnings": score_data.get("warnings", []) + momentum.get("warnings", []) + sr.get("warnings", []),
        "leitura": " ".join(leitura_parts) if leitura_parts else "Dados insuficientes para leitura completa.",
    }

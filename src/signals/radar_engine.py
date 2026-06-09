from __future__ import annotations

import time as _time
from pathlib import Path

import pandas as pd

from src.data.fetch_crypto import get_crypto_data
from src.data.yfinance_handler import YahooFinanceDataHandler
from src.indicators.technicals import add_rsi
from src.signals.rsi_entry_engine import classificar_rsi_entrada

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

_CACHE: dict = {}
_CACHE_TTL = 900  # 15 minutos


def _normalizar_symbol(symbol: str) -> str:
    s = symbol.strip().upper()
    known_pairs = {
        "BTC": "BTC/USDT", "BTCUSDT": "BTC/USDT",
        "ETH": "ETH/USDT", "ETHUSDT": "ETH/USDT",
        "SOL": "SOL/USDT", "SOLUSDT": "SOL/USDT",
        "BNB": "BNB/USDT", "BNBUSDT": "BNB/USDT",
        "XRP": "XRP/USDT", "XRPUSDT": "XRP/USDT",
        "ADA": "ADA/USDT", "ADAUSDT": "ADA/USDT",
        "AVAX": "AVAX/USDT", "AVAXUSDT": "AVAX/USDT",
        "LINK": "LINK/USDT", "LINKUSDT": "LINK/USDT",
        "DOGE": "DOGE/USDT", "DOGEUSDT": "DOGE/USDT",
        "DOT": "DOT/USDT", "DOTUSDT": "DOT/USDT",
        "NEAR": "NEAR/USDT", "NEARUSDT": "NEAR/USDT",
        "APT": "APT/USDT", "APTUSDT": "APT/USDT",
        "ARB": "ARB/USDT", "ARBUSDT": "ARB/USDT",
        "OP": "OP/USDT", "OPUSDT": "OP/USDT",
        "SUI": "SUI/USDT", "SUIUSDT": "SUI/USDT",
        "INJ": "INJ/USDT", "INJUSDT": "INJ/USDT",
        "TON": "TON/USDT", "TONUSDT": "TON/USDT",
        "TRX": "TRX/USDT", "TRXUSDT": "TRX/USDT",
        "LTC": "LTC/USDT", "LTCUSDT": "LTC/USDT",
        "BCH": "BCH/USDT", "BCHUSDT": "BCH/USDT",
        "FIL": "FIL/USDT", "FILUSDT": "FIL/USDT",
        "ATOM": "ATOM/USDT", "ATOMUSDT": "ATOM/USDT",
        "UNI": "UNI/USDT", "UNIUSDT": "UNI/USDT",
        "AAVE": "AAVE/USDT", "AAVEUSDT": "AAVE/USDT",
        "RUNE": "RUNE/USDT", "RUNEUSDT": "RUNE/USDT",
        "SEI": "SEI/USDT", "SEIUSDT": "SEI/USDT",
        "FET": "FET/USDT", "FETUSDT": "FET/USDT",
        "RNDR": "RNDR/USDT", "RNDRUSDT": "RNDR/USDT",
        "TIA": "TIA/USDT", "TIAUSDT": "TIA/USDT",
        "MATIC": "MATIC/USDT", "MATICUSDT": "MATIC/USDT",
    }
    if "/" not in s:
        if s in known_pairs:
            return known_pairs[s]
    return s


def _normalizar_stock(symbol: str) -> str:
    return symbol.strip().upper()


def _criar_lista_padrao(tipo: str):
    path = _PROJECT_ROOT / f"radar_{tipo}.txt"
    if path.exists():
        return
    if tipo == "cripto":
        defaults = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    else:
        defaults = ["AAPL", "MSFT", "NVDA", "TSLA", "SPY", "QQQ"]
    path.write_text("\n".join(defaults), encoding="utf-8")


def carregar_lista(tipo: str) -> list[str]:
    _criar_lista_padrao(tipo)
    path = _PROJECT_ROOT / f"radar_{tipo}.txt"
    symbols = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        s = _normalizar_symbol(line) if tipo == "cripto" else _normalizar_stock(line)
        if s and s not in symbols:
            symbols.append(s)
    return symbols


def _calcular_rsi_principal(symbol: str, tipo: str) -> float | None:
    try:
        if tipo == "cripto":
            df = get_crypto_data(symbol=symbol, timeframe="4h", limit=120)
        else:
            dh = YahooFinanceDataHandler(auto_adjust=True)
            df = dh.fetch_ohlc(ticker=symbol, period="3mo", interval="1d")

        if df.empty or len(df) < 20:
            return None

        df = add_rsi(df)
        rsi_val = df["rsi"].iloc[-1]
        if pd.isna(rsi_val):
            return None
        return round(float(rsi_val), 1)
    except Exception:
        return None


def _enriquecer_aprovado(rsi_val: float, symbol: str, tipo: str) -> dict:
    try:
        from src.signals.signal_engine import gerar_analise_completa
        from src.data.market_summary import get_market_summary

        analysis = gerar_analise_completa(symbol)
        ms = get_market_summary(symbol, tipo)
    except Exception:
        analysis = None
        ms = {}

    rsi_class = classificar_rsi_entrada(rsi_val)

    if analysis:
        tendencia = analysis.get("direcao", {}).get("interpretacao", "—")
        vol = analysis.get("volatilidade_v2", analysis.get("volatilidade", {}))
        vol_msg = vol.get("mensagem", vol.get("regime", "—")) if isinstance(vol, dict) else "—"
        dec = analysis.get("decisao", {})
        dec_msg = dec.get("decisao", "—") if isinstance(dec, dict) else "—"
    else:
        tendencia = "—"
        vol_msg = "—"
        dec_msg = "—"

    preco = ms.get("preco_atual") if isinstance(ms, dict) else None
    variacao = ms.get("variacao_24h_percent") if isinstance(ms, dict) else None

    return {
        "symbol": symbol,
        "tipo": tipo,
        "preco_atual": preco,
        "variacao_percentual": variacao,
        "timeframe_principal": "4h" if tipo == "cripto" else "1d",
        "rsi_principal": rsi_val,
        "status_rsi": f"{rsi_class['emoji']} {rsi_class['mensagem']}",
        "tendencia": tendencia,
        "volatilidade": vol_msg,
        "decisao": dec_msg,
    }


def executar_radar(tipo: str, force: bool = False) -> dict:
    tf_key = "4h" if tipo == "cripto" else "1D"
    cache_key = f"radar_{tipo}"

    if not force and cache_key in _CACHE:
        cached_result, cached_at = _CACHE[cache_key]
        if _time.time() - cached_at < _CACHE_TTL:
            result = dict(cached_result)
            result["cache_hit"] = True
            return result

    start = _time.time()
    symbols = carregar_lista(tipo)
    aprovados = []
    rejeitados = []
    erros = []

    rsi_min, rsi_max = 56, 66

    for symbol in symbols:
        try:
            rsi = _calcular_rsi_principal(symbol, tipo)
            if rsi is None:
                erros.append({"symbol": symbol, "erro": "Dados indisponíveis"})
                continue

            if rsi_min <= rsi <= rsi_max:
                enriched = _enriquecer_aprovado(rsi, symbol, tipo)
                aprovados.append(enriched)
            elif rsi < rsi_min:
                rejeitados.append({"symbol": symbol, "rsi_principal": rsi, "motivo": f"RSI abaixo de {rsi_min}"})
            else:
                rejeitados.append({"symbol": symbol, "rsi_principal": rsi, "motivo": f"RSI acima de {rsi_max}"})
        except Exception as e:
            erros.append({"symbol": symbol, "erro": str(e)})

    elapsed = round(_time.time() - start, 1)
    result = {
        "tipo": tipo,
        "criterio": f"RSI {tf_key} entre {rsi_min} e {rsi_max}",
        "rsi_min": rsi_min,
        "rsi_max": rsi_max,
        "timeframe_principal": tf_key,
        "total_analisados": len(symbols),
        "total_aprovados": len(aprovados),
        "aprovados": aprovados,
        "rejeitados": rejeitados,
        "erros": erros,
        "execucao_segundos": elapsed,
        "cache_hit": False,
        "timestamp": _time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    _CACHE[cache_key] = (result, _time.time())
    return result

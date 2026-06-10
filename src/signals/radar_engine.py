from __future__ import annotations

import time as _time
from pathlib import Path

import pandas as pd

from src.data.fetch_crypto import _get_exchange, _CRYPTO_EXCHANGES
from src.data.yfinance_handler import YahooFinanceDataHandler
from src.indicators.technicals import add_rsi
from src.signals.rsi_entry_engine import classificar_rsi_entrada

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

_CACHE: dict = {}
_CACHE_TTL_SUCCESS = 900
_CACHE_TTL_ERROR = 120

_RETRY_PAUSE_S = 1.2
_SYMBOL_PAUSE_S = 0.2

_TRANSIENT_PATTERNS = (
    "RequestTimeout", "RateLimitExceeded", "DDoSProtection",
    "NetworkError", "ExchangeNotAvailable", "timed out",
)


def _is_transient(error_msg: str) -> bool:
    for p in _TRANSIENT_PATTERNS:
        if p.lower() in error_msg.lower():
            return True
    return False


def _classify_error(e: Exception) -> str:
    msg = str(e)
    if "timeout" in msg.lower() or "timed out" in msg.lower():
        return "timeout"
    if "rate" in msg.lower() and ("limit" in msg.lower() or "exceeded" in msg.lower()):
        return "rate_limit"
    if "not found" in msg.lower() or "does not exist" in msg.lower() or "invalid symbol" in msg.lower():
        return "par_indisponivel"
    if "network" in msg.lower() or "connection" in msg.lower() or "dns" in msg.lower():
        return "erro_rede"
    if "ddos" in msg.lower():
        return "rate_limit"
    return "erro_desconhecido"


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


def _calcular_rsi_principal(symbol: str, tipo: str, retry: bool = True) -> tuple[float | None, dict | None]:
    try:
        if tipo == "cripto":
            df = _fetch_ohlcv_with_retry(symbol, "4h", 120, retry)
        else:
            dh = YahooFinanceDataHandler(auto_adjust=True)
            df = dh.fetch_ohlc(ticker=symbol, period="3mo", interval="1d")

        if df is None or df.empty or len(df) < 20:
            return None, {"tipo": "dados_insuficientes", "candles": len(df) if df is not None else 0}

        df = add_rsi(df)
        rsi_val = df["rsi"].iloc[-1]
        if pd.isna(rsi_val):
            return None, {"tipo": "rsi_indisponivel"}
        return round(float(rsi_val), 1), None
    except Exception as e:
        err_type = _classify_error(e)
        err_msg = str(e)[:120]
        if retry and _is_transient(str(e)):
            _time.sleep(_RETRY_PAUSE_S)
            return _calcular_rsi_principal(symbol, tipo, retry=False)
        return None, {"tipo": err_type, "mensagem": err_msg}


def _fetch_ohlcv_with_retry(symbol: str, timeframe: str, limit: int, retry: bool):
    from src.data.fetch_crypto import get_crypto_data
    return get_crypto_data(symbol=symbol, timeframe=timeframe, limit=limit)


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
        cached_result, cached_at, had_errors = _CACHE[cache_key]
        ttl = _CACHE_TTL_ERROR if had_errors else _CACHE_TTL_SUCCESS
        if _time.time() - cached_at < ttl:
            result = dict(cached_result)
            result["cache_hit"] = True
            return result

    start = _time.time()
    symbols = carregar_lista(tipo)
    aprovados = []
    rejeitados = []
    erros = []
    error_counts: dict = {}

    rsi_min, rsi_max = 56, 66

    for i, symbol in enumerate(symbols):
        if i > 0:
            _time.sleep(_SYMBOL_PAUSE_S)

        try:
            rsi, err_info = _calcular_rsi_principal(symbol, tipo)
            if rsi is None:
                entry = {"symbol": symbol}
                if err_info:
                    entry["erro"] = err_info.get("mensagem", str(err_info))
                    entry["tipo_erro"] = err_info.get("tipo", "desconhecido")
                    error_counts[err_info.get("tipo", "desconhecido")] = error_counts.get(err_info.get("tipo", "desconhecido"), 0) + 1
                else:
                    entry["erro"] = "Dados insuficientes"
                    entry["tipo_erro"] = "dados_insuficientes"
                    error_counts["dados_insuficientes"] = error_counts.get("dados_insuficientes", 0) + 1
                erros.append(entry)
                continue

            if rsi_min <= rsi <= rsi_max:
                enriched = _enriquecer_aprovado(rsi, symbol, tipo)
                aprovados.append(enriched)
            elif rsi < rsi_min:
                rejeitados.append({"symbol": symbol, "rsi_principal": rsi, "motivo": f"RSI abaixo de {rsi_min}"})
            else:
                rejeitados.append({"symbol": symbol, "rsi_principal": rsi, "motivo": f"RSI acima de {rsi_max}"})
        except Exception as e:
            err_type = _classify_error(e)
            error_counts[err_type] = error_counts.get(err_type, 0) + 1
            erros.append({"symbol": symbol, "erro": str(e)[:120], "tipo_erro": err_type})

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
        "error_counts": error_counts,
        "execucao_segundos": elapsed,
        "cache_hit": False,
        "timestamp": _time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    had_errors = len(erros) > len(symbols) * 0.25
    _CACHE[cache_key] = (result, _time.time(), had_errors)
    return result

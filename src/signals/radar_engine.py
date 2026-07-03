from __future__ import annotations

import time as _time
from pathlib import Path

import pandas as pd

from src.data.fetch_crypto import (
    CACHE_VERSION,
    CRYPTO_TIMEOUT_MS,
    fetch_crypto_data_with_metadata,
    get_crypto_source_labels,
)
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
    if (
        "not found" in msg.lower()
        or "does not exist" in msg.lower()
        or "invalid symbol" in msg.lower()
        or "bad symbol" in msg.lower()
        or "symbolnotavailable" in msg.lower()
        or "indisponivel" in msg.lower()
    ):
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
            fetch_result = fetch_crypto_data_with_metadata(
                symbol=symbol, timeframe="4h", limit=120
            )
            df = fetch_result.df
            meta = {
                "tipo": "ok",
                "exchange": fetch_result.exchange,
                "market_type": fetch_result.market_type,
                "resolved_symbol": fetch_result.resolved_symbol,
                "candles": fetch_result.candles,
                "fallback_used": fetch_result.fallback_used,
                "attempts": fetch_result.attempts,
            }
        else:
            dh = YahooFinanceDataHandler(auto_adjust=True)
            df = dh.fetch_ohlc(ticker=symbol, period="3mo", interval="1d")
            meta = {"tipo": "ok", "candles": len(df)}

        if df is None or df.empty or len(df) < 20:
            meta["tipo"] = "dados_insuficientes"
            meta["candles"] = len(df) if df is not None else 0
            return None, meta

        df = add_rsi(df)
        rsi_val = df["rsi"].iloc[-1]
        if pd.isna(rsi_val):
            meta["tipo"] = "rsi_indisponivel"
            return None, meta
        return round(float(rsi_val), 1), meta
    except Exception as e:
        err_type = _classify_error(e)
        err_msg = str(e)[:120]
        if retry and _is_transient(str(e)):
            _time.sleep(_RETRY_PAUSE_S)
            return _calcular_rsi_principal(symbol, tipo, retry=False)
        return None, {
            "tipo": err_type,
            "mensagem": err_msg,
            "attempts": getattr(e, "attempts", []),
        }


def _enriquecer_aprovado(
    rsi_val: float,
    symbol: str,
    tipo: str,
    meta: dict | None = None,
    analise_completa: bool = False,
) -> dict:
    meta = meta or {}
    try:
        from src.data.market_summary import get_market_summary

        ms = get_market_summary(symbol, tipo)
    except Exception:
        ms = {}

    analysis = None
    if analise_completa:
        try:
            from src.signals.signal_engine import gerar_analise_completa

            analysis = gerar_analise_completa(symbol)
        except Exception:
            analysis = None

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
        "exchange": meta.get("exchange") or ms.get("exchange"),
        "market_type": meta.get("market_type") or ms.get("market_type"),
        "resolved_symbol": meta.get("resolved_symbol") or ms.get("resolved_symbol"),
        "candles": meta.get("candles"),
        "fallback_used": bool(meta.get("fallback_used") or ms.get("fallback_used")),
        "attempts": meta.get("attempts", []),
    }


def _erro_entry(symbol: str, err_info: dict | None) -> dict:
    err_info = err_info or {"tipo": "desconhecido"}
    return {
        "symbol": symbol,
        "erro": err_info.get("mensagem", "Dados indisponiveis"),
        "tipo_erro": err_info.get("tipo", "desconhecido"),
        "exchange": err_info.get("exchange"),
        "market_type": err_info.get("market_type"),
        "resolved_symbol": err_info.get("resolved_symbol"),
        "candles": err_info.get("candles"),
        "fallback_used": bool(err_info.get("fallback_used")),
        "attempts": err_info.get("attempts", []),
    }


def _diagnostico_fontes(rows: list[dict]) -> dict:
    exchanges = sorted({r.get("exchange") for r in rows if r.get("exchange")})
    market_types = sorted({r.get("market_type") for r in rows if r.get("market_type")})
    fallbacks = [r for r in rows if r.get("fallback_used")]
    resolved = [
        {
            "symbol": r.get("symbol"),
            "exchange": r.get("exchange"),
            "market_type": r.get("market_type"),
            "resolved_symbol": r.get("resolved_symbol"),
            "candles": r.get("candles"),
            "fallback_used": r.get("fallback_used"),
        }
        for r in rows
        if r.get("exchange") or r.get("resolved_symbol")
    ]
    return {
        "cache_version": CACHE_VERSION,
        "timeout_ms": CRYPTO_TIMEOUT_MS,
        "source_order": get_crypto_source_labels(),
        "exchanges_usadas": exchanges,
        "market_types_usados": market_types,
        "ativos_com_fallback": fallbacks,
        "simbolos_resolvidos": resolved,
    }


def executar_radar(tipo: str, force: bool = False, analise_completa: bool = False) -> dict:
    tf_key = "4h" if tipo == "cripto" else "1D"
    cache_key = f"{CACHE_VERSION}:radar_{tipo}:full={int(analise_completa)}"

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
            rsi, meta = _calcular_rsi_principal(symbol, tipo)
            if rsi is None:
                entry = _erro_entry(symbol, meta)
                err_type = entry["tipo_erro"]
                error_counts[err_type] = error_counts.get(err_type, 0) + 1
                erros.append(entry)
                continue

            if rsi_min <= rsi <= rsi_max:
                enriched = _enriquecer_aprovado(
                    rsi,
                    symbol,
                    tipo,
                    meta=meta,
                    analise_completa=analise_completa,
                )
                aprovados.append(enriched)
            elif rsi < rsi_min:
                rejeitados.append({
                    "symbol": symbol,
                    "rsi_principal": rsi,
                    "motivo": f"RSI abaixo de {rsi_min}",
                    **(meta or {}),
                })
            else:
                rejeitados.append({
                    "symbol": symbol,
                    "rsi_principal": rsi,
                    "motivo": f"RSI acima de {rsi_max}",
                    **(meta or {}),
                })
        except Exception as e:
            err_type = _classify_error(e)
            error_counts[err_type] = error_counts.get(err_type, 0) + 1
            erros.append({
                "symbol": symbol,
                "erro": str(e)[:120],
                "tipo_erro": err_type,
                "attempts": getattr(e, "attempts", []),
            })

    elapsed = round(_time.time() - start, 1)
    all_rows = aprovados + rejeitados + erros
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
        "diagnostico": _diagnostico_fontes(all_rows) if tipo == "cripto" else {},
        "analise_completa": analise_completa,
        "execucao_segundos": elapsed,
        "cache_hit": False,
        "timestamp": _time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    had_errors = len(erros) > len(symbols) * 0.25
    _CACHE[cache_key] = (result, _time.time(), had_errors)
    return result

from __future__ import annotations

from datetime import datetime

import pytz

from src.signals.logger import salvar_sinal, salvar_volatilidade_btc, salvar_estado_direcional, carregar_estado_direcional
from src.strategy.multi_tf_analysis import (
    analisar_confluencia,
    analisar_confluencia_stock,
)
from src.volatility.volatility_config import is_btc, normalizar_symbol_btc, RSI_BAIXA_FORTE

_PRAZOS_CRIPTO = {"curto": {"15m", "1h", "4h"}, "medio": {"1D"}, "longo": {"1W"}}
_PRAZOS_STOCK = {"curto": {"1d", "5d"}, "medio": {"1wk"}, "longo": set()}


def _detectar_tipo(symbol: str) -> str:
    return "cripto" if "/" in symbol else "acao"


def _detectar_perda_tendencia(curr_alta: set, curr_baixa: set,
                               prev_alta: set, prev_baixa: set, tipo: str) -> dict | None:
    prazos = _PRAZOS_CRIPTO if tipo == "cripto" else _PRAZOS_STOCK

    for direcao, curr_set, prev_set, prefixo, icone in [
        ("alta", curr_alta, prev_alta, "alta", "alta"),
        ("baixa", curr_baixa, prev_baixa, "baixa", "baixa"),
    ]:
        for prazo_nome, prazo_tfs in prazos.items():
            if not prazo_tfs:
                continue
            prev_no_prazo = prev_set & prazo_tfs
            curr_no_prazo = curr_set & prazo_tfs
            if prev_no_prazo and not curr_no_prazo:
                return {
                    "regime_direcional": f"perda_tendencia_{prefixo}_{prazo_nome}",
                    "lado": "neutro", "forca": "indefinida",
                    "interpretacao": f"⚠️ Perda da tendência de {prefixo} de {prazo_nome} prazo",
                }
    return None


def _classificar_direcao(timeframes_alta: set, timeframes_baixa: set, tipo: str,
                          prev_alta: set | None = None, prev_baixa: set | None = None) -> dict:
    if prev_alta is not None and prev_baixa is not None:
        perda = _detectar_perda_tendencia(
            timeframes_alta, timeframes_baixa, prev_alta, prev_baixa, tipo
        )
        if perda:
            return perda

    if tipo == "cripto":
        todos = {"15m", "1h", "4h", "1D", "1W"}

        # ── Alta ──
        if timeframes_alta == todos:
            return {"regime_direcional": "alta_forte", "lado": "long", "forca": "forte",
                    "interpretacao": "📈 Tendência de alta forte"}
        if timeframes_alta == {"1D", "4h", "1h", "15m"}:
            return {"regime_direcional": "alta_forte", "lado": "long", "forca": "forte",
                    "interpretacao": "📈 Tendência de alta no médio prazo com possível reversão para alta no longo prazo"}
        if timeframes_alta == {"4h", "1h", "15m"}:
            return {"regime_direcional": "alta_moderada", "lado": "long", "forca": "moderada",
                    "interpretacao": "📈 Tendência de alta no curto prazo com possível reversão para o médio prazo"}
        if timeframes_alta == {"1h", "15m"}:
            return {"regime_direcional": "alta_leve", "lado": "long", "forca": "leve",
                    "interpretacao": "📉 Alta leve no curto prazo"}
        if timeframes_alta == {"15m"}:
            return {"regime_direcional": "sem_tendencia_direcional", "lado": "neutro", "forca": "indefinida",
                    "interpretacao": "ℹ️ Alta apenas no 15m — não é suficiente para indicar tendência"}
        if timeframes_alta == {"1D"}:
            return {"regime_direcional": "possivel_reversao_alta", "lado": "long", "forca": "moderada",
                    "interpretacao": "🔄 Possível reversão de tendência no médio prazo, ainda incerta"}
        if timeframes_alta == {"1D", "1W"}:
            return {"regime_direcional": "alta_moderada", "lado": "long", "forca": "moderada",
                    "interpretacao": "🔄 Tendência macro preservada com correção no curto prazo"}
        if timeframes_alta == {"1D", "1h", "15m"}:
            return {"regime_direcional": "transicao", "lado": "neutro", "forca": "indefinida",
                    "interpretacao": "🟡 Zona de transição – sinais mistos entre curto e médio prazo"}
        if timeframes_alta == {"1W"}:
            return {"regime_direcional": "alta_moderada", "lado": "long", "forca": "moderada",
                    "interpretacao": "📉 Tendência de alta no longo prazo com correção nos demais tempos"}
        if timeframes_alta == {"1W", "1D"}:
            return {"regime_direcional": "alta_moderada", "lado": "long", "forca": "moderada",
                    "interpretacao": "🔄 Tendência macro preservada com correção no curto prazo"}
        if timeframes_alta == {"1W", "1D", "4h"}:
            return {"regime_direcional": "alta_forte", "lado": "long", "forca": "forte",
                    "interpretacao": "📈 Tendência de alta no médio/longo prazo"}
        if timeframes_alta == {"1W", "1D", "4h", "1h"}:
            return {"regime_direcional": "alta_forte", "lado": "long", "forca": "forte",
                    "interpretacao": "📈 Tendência de alta se consolidando"}

        # ── Baixa ──
        if timeframes_baixa == todos:
            return {"regime_direcional": "baixa_forte", "lado": "short", "forca": "forte",
                    "interpretacao": "📉 Tendência de baixa forte"}
        if timeframes_baixa == {"1D", "4h", "1h", "15m"}:
            return {"regime_direcional": "baixa_forte", "lado": "short", "forca": "forte",
                    "interpretacao": "📉 Tendência de baixa no médio prazo com possível continuação para o longo prazo"}
        if timeframes_baixa == {"4h", "1h", "15m"}:
            return {"regime_direcional": "baixa_moderada", "lado": "short", "forca": "moderada",
                    "interpretacao": "📉 Tendência de baixa no curto prazo com possível continuação para o médio prazo"}
        if timeframes_baixa == {"1h", "15m"}:
            return {"regime_direcional": "baixa_leve", "lado": "short", "forca": "leve",
                    "interpretacao": "🔻 Baixa leve no curto prazo"}
        if timeframes_baixa == {"1D"}:
            return {"regime_direcional": "possivel_reversao_baixa", "lado": "short", "forca": "moderada",
                    "interpretacao": "🔄 Possível reversão de tendência para baixa no médio prazo"}
        if timeframes_baixa == {"1D", "1W"}:
            return {"regime_direcional": "baixa_moderada", "lado": "short", "forca": "moderada",
                    "interpretacao": "🔄 Tendência macro de baixa preservada com correção no curto prazo"}

        if not timeframes_alta and not timeframes_baixa:
            return {"regime_direcional": "sem_tendencia_direcional", "lado": "neutro", "forca": "indefinida",
                    "interpretacao": "❌ Nenhum timeframe em tendência clara"}

        return {"regime_direcional": "transicao", "lado": "neutro", "forca": "indefinida",
                "interpretacao": "🟡 Zona de transição – sinais mistos"}

    else:
        # ── Ações americanas ──
        if timeframes_alta == {"1d", "5d", "1wk"}:
            return {"regime_direcional": "alta_forte", "lado": "long", "forca": "forte",
                    "interpretacao": "📈 Tendência de alta forte"}
        if timeframes_alta == {"1d", "5d"}:
            return {"regime_direcional": "alta_forte", "lado": "long", "forca": "forte",
                    "interpretacao": "📈 Tendência de alta no curto a médio prazo"}
        if timeframes_alta == {"5d"}:
            return {"regime_direcional": "alta_leve", "lado": "long", "forca": "leve",
                    "interpretacao": "📉 Alta leve recente"}
        if timeframes_alta == {"1d"}:
            return {"regime_direcional": "alta_leve", "lado": "long", "forca": "leve",
                    "interpretacao": "🔄 Possível reversão de tendência no médio prazo"}
        if timeframes_alta == {"1wk"}:
            return {"regime_direcional": "alta_moderada", "lado": "long", "forca": "moderada",
                    "interpretacao": "📉 Tendência de alta no longo prazo com correção recente"}
        if timeframes_alta == {"1d", "1wk"}:
            return {"regime_direcional": "alta_moderada", "lado": "long", "forca": "moderada",
                    "interpretacao": "🔄 Tendência macro preservada com correção no curto prazo"}
        if timeframes_alta == {"5d", "1wk"}:
            return {"regime_direcional": "alta_moderada", "lado": "long", "forca": "moderada",
                    "interpretacao": "📈 Tendência de alta no médio/longo prazo"}

        if timeframes_baixa == {"1d", "5d", "1wk"}:
            return {"regime_direcional": "baixa_forte", "lado": "short", "forca": "forte",
                    "interpretacao": "📉 Tendência de baixa forte"}
        if timeframes_baixa == {"1d", "5d"}:
            return {"regime_direcional": "baixa_forte", "lado": "short", "forca": "forte",
                    "interpretacao": "📉 Tendência de baixa no curto a médio prazo"}
        if timeframes_baixa == {"5d"}:
            return {"regime_direcional": "baixa_leve", "lado": "short", "forca": "leve",
                    "interpretacao": "🔻 Baixa leve recente"}
        if timeframes_baixa == {"1d"}:
            return {"regime_direcional": "baixa_leve", "lado": "short", "forca": "leve",
                    "interpretacao": "🔄 Possível reversão de tendência de baixa no médio prazo"}
        if timeframes_baixa == {"1wk"}:
            return {"regime_direcional": "baixa_moderada", "lado": "short", "forca": "moderada",
                    "interpretacao": "🔻 Tendência de baixa no longo prazo com correção recente"}
        if timeframes_baixa == {"1d", "1wk"}:
            return {"regime_direcional": "baixa_moderada", "lado": "short", "forca": "moderada",
                    "interpretacao": "🔄 Tendência macro de baixa preservada com correção no curto prazo"}

        if not timeframes_alta and not timeframes_baixa:
            return {"regime_direcional": "sem_tendencia_direcional", "lado": "neutro", "forca": "indefinida",
                    "interpretacao": "❌ Nenhum timeframe em tendência clara"}

        return {"regime_direcional": "transicao", "lado": "neutro", "forca": "indefinida",
                "interpretacao": "🟡 Zona de transição – sinais mistos"}


def interpretar_tendencia(estado: dict, tipo: str = "cripto") -> str:
    timeframes_alta = {tf for tf, s in estado.items() if s.get("tendencia_alta")}
    timeframes_baixa = {tf for tf, s in estado.items() if s.get("tendencia_baixa")}
    result = _classificar_direcao(timeframes_alta, timeframes_baixa, tipo)
    return result["interpretacao"]


def gerar_sinal(symbol: str) -> str:
    result = gerar_analise_completa(symbol)
    return result["direcao"]["interpretacao"]


def gerar_analise_completa(symbol: str) -> dict:
    tipo = _detectar_tipo(symbol)
    _btc = is_btc(symbol)

    try:
        # ── 1. Motor de Direção ──
        if tipo == "cripto":
            timeframes = analisar_confluencia(symbol)
        else:
            timeframes = analisar_confluencia_stock(symbol)

        tfs_alta = {tf for tf, s in timeframes.items() if s.get("tendencia_alta")}
        tfs_baixa = {tf for tf, s in timeframes.items() if s.get("tendencia_baixa")}

        prev_alta, prev_baixa = carregar_estado_direcional(symbol)
        direcao = _classificar_direcao(tfs_alta, tfs_baixa, tipo, prev_alta, prev_baixa)
        direcao["timeframes"] = timeframes

        # ── 0. Market Summary ──
        from src.data.market_summary import get_market_summary
        try:
            market_summary = get_market_summary(symbol, tipo)
        except Exception:
            market_summary = None

        try:
            salvar_estado_direcional(symbol, tfs_alta, tfs_baixa)
        except Exception:
            pass

        # ── 2. Motor de Volatilidade ──
        from src.volatility.volatility_engine import analisar_volatilidade
        from src.volatility.volatility_engine_v2 import analisar_volatilidade_v2
        volatilidade = analisar_volatilidade(symbol)
        volatilidade_v2 = analisar_volatilidade_v2(symbol, tipo)

        # ── 3. Motor de Decisão Operacional ──
        from src.decision.decision_engine import gerar_decisao_operacional
        decisao = gerar_decisao_operacional(direcao, volatilidade, _btc)

        # ── 3.5 Qualidade do RSI para Entrada ──
        from src.signals.rsi_entry_engine import analisar_rsi_por_timeframe
        rsi_entrada = analisar_rsi_por_timeframe(timeframes, tipo)

        # ── 4. Persistência ──
        try:
            salvar_sinal(symbol, tipo, direcao["interpretacao"])
        except Exception:
            pass

        tz_sp = pytz.timezone("America/Sao_Paulo")
        timestamp = datetime.now(tz_sp).strftime("%Y-%m-%d %H:%M:%S")

        return {
            "symbol": symbol,
            "tipo": tipo,
            "is_btc": _btc,
            "direcao": direcao,
            "volatilidade": volatilidade,
            "volatilidade_v2": volatilidade_v2,
            "decisao": decisao,
            "rsi_entrada": rsi_entrada,
            "market_summary": market_summary,
            "timestamp": timestamp,
        }
    except Exception as e:
        raise RuntimeError(f"Falha ao analisar {symbol}: {e}") from e


def gerar_analise_btc_completa() -> dict:
    return gerar_analise_completa("BTC/USDT")

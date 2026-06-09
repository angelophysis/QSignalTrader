from __future__ import annotations

import math

import numpy as np
import pandas as pd

from src.data.fetch_crypto import get_crypto_data
from src.data.yfinance_handler import YahooFinanceDataHandler
from src.indicators.technicals import add_atr
from src.volatility.implied_vol import buscar_dvol_btc
from src.volatility.volatility_config import is_btc

# ── Per-TF weights and roles ──
_CRYPTO_TFS = [
    ("15m", 1, "ruido / timing curto"),
    ("1h", 2, "confirmacao curta"),
    ("4h", 4, "principal para entrada"),
    ("1D", 3, "contexto macro"),
    ("1W", 1, "longo prazo"),
]

_STOCK_TFS = [
    ("1d", 4, "principal para entrada"),
    ("5d", 3, "confirmacao"),
    ("1wk", 2, "macro"),
]


def _safe(val):
    if val is None:
        return None
    if isinstance(val, np.generic):
        val = val.item()
    if isinstance(val, (int, float)):
        if math.isnan(val) or math.isinf(val):
            return None
        return float(val)
    return None


def _classificar_nivel_vol(atr_percentil: float | None) -> dict:
    if atr_percentil is None:
        return {"nivel": "indisponivel", "nivel_label": "Indisponivel"}
    if atr_percentil < 30:
        return {"nivel": "baixa", "nivel_label": "Baixa"}
    if atr_percentil <= 70:
        return {"nivel": "normal", "nivel_label": "Normal"}
    return {"nivel": "alta", "nivel_label": "Alta"}


def _classificar_movimento_vol(atr_pct: float | None, atr_ma20: float | None) -> dict:
    if atr_pct is None or atr_ma20 is None or atr_ma20 == 0:
        return {"movimento": "indisponivel", "movimento_label": "Indisponivel"}
    ratio = atr_pct / atr_ma20
    if ratio > 1.05:
        return {"movimento": "expandindo", "movimento_label": "Expandindo"}
    if ratio < 0.95:
        return {"movimento": "comprimindo", "movimento_label": "Comprimindo"}
    return {"movimento": "estavel", "movimento_label": "Estavel"}


_MENSAGENS = {
    ("baixa", "comprimindo"): "🟦 Volatilidade baixa e comprimindo",
    ("baixa", "estavel"): "🟨 Volatilidade baixa e estavel",
    ("baixa", "expandindo"): "🟨 Volatilidade baixa e expandindo",
    ("normal", "comprimindo"): "⚪ Volatilidade normal e comprimindo",
    ("normal", "estavel"): "⚪ Volatilidade normal e estavel",
    ("normal", "expandindo"): "🟨 Volatilidade normal e expandindo",
    ("alta", "comprimindo"): "🟪 Volatilidade alta e comprimindo",
    ("alta", "estavel"): "🟧 Volatilidade alta e estavel",
    ("alta", "expandindo"): "🚀 Volatilidade alta e expandindo",
}

_COMENTARIOS = {
    ("baixa", "comprimindo"): "Mercado quieto; preparar alertas para possivel rompimento, mas evitar entrada por impulso.",
    ("baixa", "estavel"): "Volatilidade baixa; movimento ainda sem aceleracao relevante.",
    ("baixa", "expandindo"): "Volatilidade comecando a acordar; observar confirmacao direcional para possivel breakout.",
    ("normal", "comprimindo"): "Volatilidade saudavel, mas perdendo forca; evitar entradas atrasadas.",
    ("normal", "estavel"): "Condicao de volatilidade equilibrada; seguir leitura direcional e gestao de risco padrao.",
    ("normal", "expandindo"): "Movimento ganhando energia; favorece entrada direcional se a direcao estiver clara.",
    ("alta", "comprimindo"): "Volatilidade ainda alta, mas comecando a esfriar; cuidado com entradas apos movimento esticado.",
    ("alta", "estavel"): "Volatilidade elevada; operar com stops mais largos e tamanho de posicao reduzido.",
    ("alta", "expandindo"): "Mercado acelerado; favorece momentum, mas exige controle rigoroso de risco.",
}


def _gerar_mensagem_v2(nivel: str, movimento: str) -> str:
    return _MENSAGENS.get((nivel, movimento), "⚪ Volatilidade indisponivel")


def _gerar_comentario(nivel: str, movimento: str) -> str:
    return _COMENTARIOS.get((nivel, movimento), "Dados insuficientes para leitura de volatilidade.")


def _analisar_tf_v2(df: pd.DataFrame, tf: str, peso: int, papel: str) -> dict:
    if df.empty or len(df) < 20:
        return {
            "timeframe": tf, "peso": peso, "papel": papel,
            "atr_percent": None, "atr_percentil": None,
            "nivel": "indisponivel", "movimento": "indisponivel",
            "mensagem": "⚪ Volatilidade indisponivel",
        }

    atr_df = add_atr(df.copy(), period=14)
    close = atr_df["close"]
    atr_col = atr_df["atr"]

    atr_pct_series = (atr_col / close) * 100
    latest_atr_pct = _safe(atr_pct_series.iloc[-1])

    percentile = None
    valid = atr_pct_series.dropna()
    if len(valid) >= 10 and latest_atr_pct is not None:
        rank = (valid < latest_atr_pct).sum()
        percentile = round(float(rank) / len(valid) * 100, 1)

    atr_ma20 = None
    if len(valid) >= 20:
        atr_ma20 = _safe(valid.rolling(20).mean().iloc[-1])

    nivel_info = _classificar_nivel_vol(percentile)
    mov_info = _classificar_movimento_vol(latest_atr_pct, atr_ma20)
    mensagem = _gerar_mensagem_v2(nivel_info["nivel"], mov_info["movimento"])

    return {
        "timeframe": tf,
        "peso": peso,
        "papel": papel,
        "atr_percent": round(latest_atr_pct, 4) if latest_atr_pct else None,
        "atr_percentil": percentile,
        "nivel": nivel_info["nivel"],
        "movimento": mov_info["movimento"],
        "mensagem": mensagem,
    }


def _agregar_v2(tf_results: list[dict]) -> dict:
    total_peso = 0
    score_nivel = 0.0
    score_mov = 0.0

    nivel_map = {"baixa": -1, "normal": 0, "alta": 1}
    mov_map = {"comprimindo": -1, "estavel": 0, "expandindo": 1}

    for r in tf_results:
        w = r["peso"]
        sn = nivel_map.get(r["nivel"], 0)
        sm = mov_map.get(r["movimento"], 0)
        score_nivel += sn * w
        score_mov += sm * w
        total_peso += w

    if total_peso > 0:
        score_nivel /= total_peso
        score_mov /= total_peso
    else:
        score_nivel = 0
        score_mov = 0

    if score_nivel <= -0.35:
        nivel_agr = "baixa"
    elif score_nivel >= 0.35:
        nivel_agr = "alta"
    else:
        nivel_agr = "normal"

    if score_mov <= -0.35:
        mov_agr = "comprimindo"
    elif score_mov >= 0.35:
        mov_agr = "expandindo"
    else:
        mov_agr = "estavel"

    return {
        "nivel_agregado": nivel_agr,
        "movimento_agregado": mov_agr,
        "score_nivel": round(score_nivel, 2),
        "score_movimento": round(score_mov, 2),
    }


def analisar_volatilidade_v2(symbol: str, tipo: str) -> dict:
    _btc = is_btc(symbol)
    tf_specs = _CRYPTO_TFS if tipo == "cripto" else _STOCK_TFS
    principal_tf = "4h" if tipo == "cripto" else "1d"

    tf_results = []
    for tf, peso, papel in tf_specs:
        try:
            if tipo == "cripto":
                df = get_crypto_data(symbol=symbol, timeframe=tf, limit=500)
            else:
                dh = YahooFinanceDataHandler(auto_adjust=True)
                interval = "1wk" if tf == "1wk" else "1d"
                period = "6mo" if tf in ("1d", "5d") else "1y"
                df = dh.fetch_ohlc(ticker=symbol, period=period, interval=interval)
            tf_results.append(_analisar_tf_v2(df, tf, peso, papel))
        except Exception:
            tf_results.append({
                "timeframe": tf, "peso": peso, "papel": papel,
                "atr_percent": None, "atr_percentil": None,
                "nivel": "indisponivel", "movimento": "indisponivel",
                "mensagem": "⚪ Volatilidade indisponivel",
            })

    agg = _agregar_v2(tf_results)
    mensagem = _gerar_mensagem_v2(agg["nivel_agregado"], agg["movimento_agregado"])
    comentario = _gerar_comentario(agg["nivel_agregado"], agg["movimento_agregado"])

    rv30 = None
    for r in tf_results:
        if r["timeframe"] in ("1D", "1d"):
            try:
                if tipo == "cripto":
                    df = get_crypto_data(symbol=symbol, timeframe=r["timeframe"], limit=500)
                else:
                    dh = YahooFinanceDataHandler(auto_adjust=True)
                    df = dh.fetch_ohlc(ticker=symbol, period="1y", interval="1d")
                log_ret = np.log(df["close"] / df["close"].shift(1)).dropna()
                if len(log_ret) >= 30:
                    rv30 = float(log_ret.rolling(30).std().iloc[-1] * math.sqrt(365))
            except Exception:
                pass
            break

    implicita = {"disponivel": False}
    if _btc:
        try:
            iv_data = buscar_dvol_btc()
            dvol = iv_data.get("dvol")
            if dvol is not None and rv30 is not None and rv30 > 0:
                rv30_pct = rv30 * 100
                iv_data["iv_rv_ratio"] = round(dvol / rv30_pct, 4)

            iv_rv = iv_data.get("iv_rv_ratio")
            if iv_rv is not None:
                if iv_rv < 0.90:
                    iv_leitura = "IV barata em relacao a volatilidade realizada; compra de volatilidade pode ser considerada se houver gatilho."
                elif iv_rv <= 1.20:
                    iv_leitura = "IV proxima da volatilidade realizada; escolha da estrutura deve depender mais da direcao e do timing."
                else:
                    iv_leitura = "IV relativamente cara em relacao a volatilidade realizada; preferir spreads em vez de compra seca de opcoes."
            else:
                iv_leitura = None

            implicita = {
                "disponivel": True,
                "dvol": dvol,
                "dvol_ma20": iv_data.get("dvol_ma20"),
                "iv_rank": iv_data.get("iv_rank"),
                "iv_percentile": iv_data.get("iv_percentile"),
                "iv_rv_ratio": iv_data.get("iv_rv_ratio"),
                "iv_rv": iv_rv,
                "leitura": iv_leitura,
            }
        except Exception:
            implicita = {"disponivel": False, "error": "Falha ao buscar DVOL"}

    return {
        "versao": "v2",
        "tipo": tipo,
        "symbol": symbol,
        "is_btc": _btc,
        "timeframe_principal": principal_tf,
        "nivel_agregado": agg["nivel_agregado"],
        "movimento_agregado": agg["movimento_agregado"],
        "mensagem": mensagem,
        "comentario_operacional": comentario,
        "score_nivel": agg["score_nivel"],
        "score_movimento": agg["score_movimento"],
        "timeframes": tf_results,
        "implicita_btc": implicita,
    }

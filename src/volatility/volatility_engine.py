from __future__ import annotations

from src.data.fetch_crypto import get_crypto_data
from src.data.yfinance_handler import YahooFinanceDataHandler
from src.volatility.implied_vol import calcular_metricas_iv
from src.volatility.realized_vol import calcular_volatilidade_realizada
from src.volatility.volatility_config import is_btc


def _calcular_score_expansao(r: dict, i: dict) -> int:
    score = 0

    atr_ratio = r.get("atr_percent_ratio")
    if atr_ratio is not None and atr_ratio > 1.0:
        score += 2

    rv_ratio = r.get("rv7_rv30_ratio")
    if rv_ratio is not None and rv_ratio > 1.25:
        score += 2

    bw_pct = r.get("bandwidth_percentile")
    bw_slope = r.get("bandwidth_slope_5")
    if bw_pct is not None and bw_pct < 20 and bw_slope is not None and bw_slope > 0:
        score += 2

    dvol = i.get("dvol")
    dvol_ma20 = i.get("dvol_ma20")
    dvol_slope = i.get("dvol_slope_3")
    if dvol is not None and dvol_ma20 is not None and dvol > dvol_ma20 and dvol_slope is not None and dvol_slope > 0:
        score += 2

    iv_rank = i.get("iv_rank")
    dvol_slope_7 = i.get("dvol_slope_7")
    if iv_rank is not None and iv_rank < 50 and dvol_slope_7 is not None and dvol_slope_7 > 0:
        score += 1

    iv_rv = i.get("iv_rv_ratio")
    if iv_rv is not None and iv_rv <= 1.0:
        score += 1

    return min(score, 10)


def _calcular_score_contracao(r: dict, i: dict) -> int:
    score = 0

    iv_rank = i.get("iv_rank")
    if iv_rank is not None and iv_rank > 70:
        score += 2

    iv_pct = i.get("iv_percentile")
    if iv_pct is not None and iv_pct > 70:
        score += 2

    dvol_slope_3 = i.get("dvol_slope_3")
    dvol_slope_7 = i.get("dvol_slope_7")
    if dvol_slope_7 is not None and dvol_slope_7 < 0:
        score += 2

    iv_rv = i.get("iv_rv_ratio")
    if iv_rv is not None and iv_rv > 1.25:
        score += 2

    atr_slope = r.get("atr_percent_slope_5")
    if atr_slope is not None and atr_slope < 0:
        score += 1

    bw_slope = r.get("bandwidth_slope_5")
    if bw_slope is not None and bw_slope < 0:
        score += 1

    return min(score, 10)


def _classificar_regime(score_exp: int, score_cont: int, r: dict, i: dict) -> str:
    bw_pct = r.get("bandwidth_percentile")
    atr_ratio = r.get("atr_percent_ratio")
    rv_ratio = r.get("rv7_rv30_ratio")
    atr_pct = r.get("atr_percent")

    iv_rank = i.get("iv_rank")
    dvol = i.get("dvol")
    dvol_slope = i.get("dvol_slope_3")

    has_iv = dvol is not None

    compressao = (
        bw_pct is not None and bw_pct < 20
        and atr_ratio is not None and atr_ratio < 1.0
        and rv_ratio is not None and rv_ratio <= 1.0
    )
    if has_iv and compressao:
        compressao = iv_rank is not None and iv_rank < 50 and compressao

    if compressao:
        return "🧨 Volatilidade comprimida com risco de expansão"

    if has_iv:
        contracao = (
            iv_rank is not None and iv_rank > 70
            and dvol_slope is not None and dvol_slope < 0
            and atr_pct is not None
        )
    else:
        contracao = (
            atr_ratio is not None and atr_ratio < 0.8
            and rv_ratio is not None and rv_ratio < 0.8
            and bw_pct is not None and bw_pct > 70
        )

    if contracao:
        return "🧊 Volatilidade elevada com probabilidade de contração"

    if has_iv:
        alta_sustentada = (
            dvol is not None and dvol > 60
            and iv_rank is not None and iv_rank > 60
            and atr_ratio is not None and atr_ratio > 1.0
            and rv_ratio is not None and rv_ratio >= 1.0
        )
    else:
        alta_sustentada = (
            atr_ratio is not None and atr_ratio > 1.2
            and rv_ratio is not None and rv_ratio >= 1.0
            and bw_pct is not None and bw_pct > 60
        )

    if alta_sustentada:
        return "🌋 Volatilidade alta e ainda sustentada"

    expansao = (
        atr_ratio is not None and atr_ratio > 1.0
        and rv_ratio is not None and rv_ratio > 1.0
    )
    if has_iv and expansao:
        expansao = (
            expansao
            and bw_pct is not None and bw_pct > 20
            and dvol_slope is not None and dvol_slope > 0
        )

    if expansao:
        return "🚀 Volatilidade em expansão"

    return "🌫 Zona de transição da volatilidade"


def _gerar_leitura_vol(regime: str) -> str:
    leituras = {
        "🧨 Volatilidade comprimida com risco de expansão": (
            "O ativo está em regime de compressão de volatilidade. "
            "Ainda não há expansão confirmada, mas o mercado pode estar acumulando energia para um movimento mais forte."
        ),
        "🚀 Volatilidade em expansão": (
            "O ativo está em regime de expansão de volatilidade. "
            "A amplitude dos movimentos está aumentando."
        ),
        "🌋 Volatilidade alta e ainda sustentada": (
            "O ativo está com volatilidade alta e ainda sustentada. "
            "O mercado segue em regime de maior amplitude."
        ),
        "🧊 Volatilidade elevada com probabilidade de contração": (
            "O ativo está com volatilidade elevada e sinais de possível contração. "
            "A amplitude dos movimentos pode estar perdendo força."
        ),
        "🌫 Zona de transição da volatilidade": (
            "O ativo está em zona de transição da volatilidade. "
            "Ainda não há leitura limpa sobre expansão ou contração."
        ),
    }
    return leituras.get(regime, "Leitura indisponível.")


def _sugerir_estrategias(regime: str) -> list[str]:
    estrategias = {
        "🧨 Volatilidade comprimida com risco de expansão": [
            "Long straddle",
            "Long strangle",
            "Compra de opções se houver gatilho técnico",
            "Estruturas de débito com risco limitado",
        ],
        "🚀 Volatilidade em expansão": [
            "Compra de volatilidade",
            "Long gamma",
            "Debit spreads direcionais",
            "Straddle/strangle se IV ainda não estiver excessivamente cara",
        ],
        "🌋 Volatilidade alta e ainda sustentada": [
            "Spreads definidos",
            "Estratégias com menor exposição líquida a Vega",
            "Evitar compra seca de opções muito caras",
            "Aguardar sinal mais claro antes de vender volatilidade",
        ],
        "🧊 Volatilidade elevada com probabilidade de contração": [
            "Iron condor",
            "Short strangle com proteção",
            "Credit spreads",
            "Calendar ou diagonal dependendo da estrutura a termo",
            "Venda de Vega com risco controlado",
        ],
        "🌫 Zona de transição da volatilidade": [
            "Reduzir tamanho",
            "Evitar operações puramente baseadas em volatilidade",
            "Esperar confirmação",
            "Usar estruturas definidas e baratas",
        ],
    }
    return estrategias.get(regime, [])


def analisar_volatilidade_btc(df_1d):
    return analisar_volatilidade("BTC/USDT")


def analisar_volatilidade(symbol: str) -> dict:
    _btc = is_btc(symbol)
    tipo = "cripto" if "/" in symbol else "acao"

    # ── Fetch data ──
    try:
        if tipo == "cripto":
            df = get_crypto_data(symbol=symbol, timeframe="1d", limit=500)
        else:
            dh = YahooFinanceDataHandler(auto_adjust=True)
            df = dh.fetch_ohlc(ticker=symbol, period="6mo", interval="1d")
    except Exception:
        return _vol_fallback(symbol, _btc)

    if df.empty or len(df) < 50:
        return _vol_fallback(symbol, _btc)

    # ── Realized volatility ──
    r = calcular_volatilidade_realizada(df)

    # ── Implied volatility (BTC only) ──
    if _btc:
        i = calcular_metricas_iv(r)
        confianca = "alta"
        score_exp = _calcular_score_expansao(r, i)
        score_cont = _calcular_score_contracao(r, i)
    else:
        i = {
            "dvol": None, "dvol_ma20": None, "dvol_ma50": None,
            "dvol_slope_3": None, "dvol_slope_7": None,
            "iv_rank": None, "iv_percentile": None, "iv_rv_ratio": None,
            "term_structure": None, "skew": None,
            "fallback": True, "error": "DVOL disponível apenas para BTC",
        }
        confianca = "media"
        raw_exp = _calcular_score_expansao(r, i)
        raw_cont = _calcular_score_contracao(r, i)
        score_exp = min(round(raw_exp / 6 * 10) if raw_exp > 0 else 0, 10)
        score_cont = min(round(raw_cont / 6 * 10) if raw_cont > 0 else 0, 10)

    regime = _classificar_regime(score_exp, score_cont, r, i)
    leitura = _gerar_leitura_vol(regime)

    result = {
        "symbol": symbol,
        "tipo": tipo,
        "is_btc": _btc,
        "regime": regime,
        "score_expansao": score_exp,
        "score_contracao": score_cont,
        "confianca_volatilidade": confianca,
        "metricas_realizadas": r,
        "metricas_implicitas": i,
        "leitura": leitura,
        "possiveis_estrategias": _sugerir_estrategias(regime),
    }
    return result


def _vol_fallback(symbol: str, _btc: bool) -> dict:
    return {
        "symbol": symbol,
        "tipo": "cripto" if "/" in symbol else "acao",
        "is_btc": _btc,
        "regime": "🌫 Zona de transição da volatilidade",
        "score_expansao": 0,
        "score_contracao": 0,
        "confianca_volatilidade": "baixa",
        "metricas_realizadas": {},
        "metricas_implicitas": {"fallback": True, "error": "Falha ao coletar dados"},
        "leitura": "Não foi possível calcular métricas de volatilidade.",
        "possiveis_estrategias": [],
    }

"""
QSignalTrader — Streamlit Interface
Online deployment on Streamlit Community Cloud.
"""
import streamlit as st
from src.signals.signal_engine import gerar_analise_completa
from src.data.market_summary import get_market_summary
from src.signals.radar_engine import executar_radar
from src.volatility.volatility_config import is_btc

st.set_page_config(page_title="QSignalTrader", layout="wide", page_icon="📊")

# ═══════════════════════════════════════════
# Cache
# ═══════════════════════════════════════════

@st.cache_data(ttl=900)
def _cached_analise(symbol: str) -> dict:
    return gerar_analise_completa(symbol)


@st.cache_data(ttl=900)
def _cached_market(symbol: str, tipo: str) -> dict:
    return get_market_summary(symbol, tipo)


@st.cache_data(ttl=900)
def _cached_radar(tipo: str) -> dict:
    return executar_radar(tipo, force=False)


# ═══════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════

def _fmt(val, dec=2):
    n = float(val) if val is not None else None
    if n is None or n != n:
        return "—"
    return f"{n:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_pct(val, dec=2):
    if val is None: return "—"
    n = float(val)
    if n != n: return "—"
    s = "+" if n > 0 else ""
    return f"{s}{n:,.{dec}f}%".replace(",", "X").replace(".", ",").replace("X", ".")


def _render_radar(data: dict, label: str):
    st.subheader(f"Radar {label}")
    st.caption(f"{data.get('total_aprovados', 0)} aprovados de "
               f"{data.get('total_analisados', 0)} analisados · "
               f"{data.get('execucao_segundos', '?')}s · ")
    aprovados = data.get("aprovados", [])
    if not aprovados:
        st.info("Nenhum ativo encontrado com RSI na zona ideal neste momento.")
        return

    rows = []
    for a in aprovados:
        var = float(a.get("variacao_percentual", 0)) if a.get("variacao_percentual") else 0
        rows.append({
            "Ativo": a["symbol"],
            "Preço": _fmt(a.get("preco_atual")),
            "Var.": _fmt_pct(a.get("variacao_percentual")),
            "RSI": a.get("rsi_principal"),
            "Tendência": a.get("tendencia", "—"),
            "Volatilidade": a.get("volatilidade", "—"),
            "Decisão": a.get("decisao", "—"),
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)

    with st.expander("Ativos fora da faixa"):
        rej = data.get("rejeitados", [])
        if rej:
            st.dataframe([{"Ativo": r["symbol"], "RSI": r["rsi_principal"], "Motivo": r["motivo"]} for r in rej],
                         use_container_width=True, hide_index=True)
        else:
            st.caption("Nenhum ativo rejeitado.")

    with st.expander("Erros"):
        errs = data.get("erros", [])
        if errs:
            st.dataframe([{"Ativo": e["symbol"], "Erro": e["erro"]} for e in errs],
                         use_container_width=True, hide_index=True)
        else:
            st.caption("Nenhum erro.")


# ═══════════════════════════════════════════
# UI
# ═══════════════════════════════════════════

st.title("QSignalTrader")
st.caption("Motor Quantitativo Multi-Ativo — Direção · Volatilidade · Decisão")

tab1, tab2 = st.tabs(["📊 Análise Individual", "🔎 Radar de Oportunidades"])

# ── Tab 1: Análise Individual ──
with tab1:
    with st.sidebar:
        st.subheader("Análise Individual")
        quick = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "AAPL", "TSLA", "NVDA", "SPY", "QQQ"]
        symbol = st.selectbox("Ativo", quick, index=0)
        custom = st.text_input("Ou digite um símbolo", placeholder="Ex: MSFT, ADA/USDT")
        if custom:
            symbol = custom.strip().upper()
        analisar = st.button("Analisar Ativo", use_container_width=True)
        force = st.checkbox("Forçar atualização (ignorar cache)")

    if analisar:
        if force:
            st.cache_data.clear()
        tipo = "cripto" if "/" in symbol else "acao"

        with st.spinner(f"Analisando {symbol}..."):
            try:
                data = _cached_analise(symbol)
                ms = _cached_market(symbol, data["tipo"])
            except Exception as e:
                st.error(f"Erro ao analisar {symbol}: {e}")
                st.stop()

        # ── Market Summary ──
        st.subheader("📈 Resumo de Mercado")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Preço", _fmt(ms.get("preco_atual")))
        delta_str = _fmt_pct(ms.get("variacao_24h_percent"))
        c2.metric("Variação", delta_str)
        c3.metric("Mínima", _fmt(ms.get("min_24h")))
        c4.metric("Máxima", _fmt(ms.get("max_24h")))
        st.caption(f"{ms.get('periodo', '')} · {ms.get('fonte', '')}")

        # ── Direção ──
        st.subheader("🧭 Motor de Direção")
        direcao = data["direcao"]
        st.info(direcao["interpretacao"])
        tfs = direcao.get("timeframes", {})
        if tfs:
            rows = []
            for tf_name, tf_data in tfs.items():
                rsi_v = tf_data.get("rsi")
                rows.append({
                    "TF": tf_name,
                    "EMAs Alinhadas": "✅" if tf_data.get("alinhamento_emas") else "❌",
                    "RSI": f"{rsi_v:.1f}" if rsi_v is not None else "—",
                    "RSI>58": "✅" if tf_data.get("rsi_forte") else ("🔻" if tf_data.get("rsi_fraco") else "❌"),
                    "ATR": _fmt(tf_data.get("atr")),
                    "Tendência": "✅ Alta" if tf_data.get("tendencia_alta") else ("🔻 Baixa" if tf_data.get("tendencia_baixa") else "❌"),
                })
            with st.expander("Timeframes"):
                st.dataframe(rows, use_container_width=True, hide_index=True)

        # ── RSI Entrada ──
        rsi_e = data.get("rsi_entrada")
        if rsi_e:
            st.subheader("📊 RSI de Entrada")
            msg = rsi_e.get("principal_mensagem", "—")
            estado = rsi_e.get("principal_estado")
            if estado == "zona_ideal":
                st.success(msg)
            elif estado == "esticado":
                st.warning(msg)
            else:
                st.info(msg)
            rsi_tfs = rsi_e.get("timeframes", {})
            if rsi_tfs:
                with st.expander("RSI por timeframe"):
                    rows_rsi = []
                    for tf_name, tf_d in rsi_tfs.items():
                        rows_rsi.append({
                            "TF": tf_name,
                            "RSI": f"{tf_d['rsi']:.1f}" if tf_d.get("rsi") is not None else "—",
                            "Estado": tf_d.get("mensagem", "—"),
                            "Peso": tf_d.get("peso", "—"),
                        })
                    st.dataframe(rows_rsi, use_container_width=True, hide_index=True)

        # ── Volatilidade v2 ──
        v2 = data.get("volatilidade_v2")
        if v2:
            st.subheader("🧪 Motor de Volatilidade")
            st.markdown(f"**{v2.get('mensagem', '—')}**")
            st.caption(v2.get("comentario_operacional", ""))
            st.caption(f"Scores: Nível {v2.get('score_nivel', '?')} · Movimento {v2.get('score_movimento', '?')}")

            with st.expander("Volatilidade por timeframe"):
                v2_tfs = v2.get("timeframes", [])
                if v2_tfs:
                    rows_v2 = []
                    for tf in v2_tfs:
                        rows_v2.append({
                            "TF": tf.get("timeframe"),
                            "ATR%": _fmt(tf.get("atr_percent"), 4),
                            "%ile": f"{tf.get('atr_percentil', 0):.0f}" if tf.get("atr_percentil") else "—",
                            "Nível": tf.get("nivel", "—"),
                            "Movimento": tf.get("movimento", "—"),
                            "Papel": tf.get("papel", "—"),
                        })
                    st.dataframe(rows_v2, use_container_width=True, hide_index=True)

            iv = v2.get("implicita_btc", {})
            if iv.get("disponivel"):
                st.caption(f"IV BTC: DVOL {iv.get('dvol', '?')} · IV Rank {iv.get('iv_rank', '?')} · "
                           f"IV% {iv.get('iv_percentile', '?')} · IV/RV {iv.get('iv_rv_ratio', '?')}")
                if iv.get("leitura"):
                    st.caption(iv["leitura"])

        # ── Decisão ──
        dec = data.get("decisao")
        if dec:
            st.subheader("📋 Decisão Operacional")
            lado = dec.get("lado", "neutro")
            if lado == "long":
                st.success(dec.get("decisao", "—"))
            elif lado == "short":
                st.error(dec.get("decisao", "—"))
            else:
                st.warning(dec.get("decisao", "—"))
            st.caption(dec.get("explicacao", ""))
            for a in dec.get("alertas", []):
                st.caption(f"• {a}")

            # ── Opções BTC ──
            if data.get("is_btc") and dec.get("opcoes_btc"):
                with st.expander("📋 Estratégias de Opções BTC"):
                    opt = dec["opcoes_btc"]
                    for s in opt.get("estrategias_prioritarias", []):
                        st.write(f"**{s['nome']}** — {s.get('tipo', '')}")
                        st.caption(f"Por que: {s.get('por_que_faz_sentido', '')}")
                        st.caption(f"Risco: {s.get('risco_principal', '')}")
                    if opt.get("estrategias_evitar"):
                        st.write("**Evitar:**")
                        for s in opt["estrategias_evitar"]:
                            st.caption(f"• {s}")

# ── Tab 2: Radar ──
with tab2:
    with st.sidebar:
        st.subheader("Radar")
        st.caption("Filtra ativos com RSI na zona ideal (56-66)")
        force_radar = st.checkbox("Forçar atualização do radar")

    st.subheader("Radar de Oportunidades")
    st.caption("RSI 4h (cripto) / RSI 1D (ações) entre 56 e 66")

    c1, c2 = st.columns(2)
    if c1.button("🔎 Radar Cripto", use_container_width=True):
        if force_radar:
            st.cache_data.clear()
        with st.spinner("Executando Radar Cripto..."):
            try:
                r = _cached_radar("cripto")
                _render_radar(r, "Cripto")
            except Exception as e:
                st.error(f"Erro: {e}")

    if c2.button("🔎 Radar Ações", use_container_width=True):
        if force_radar:
            st.cache_data.clear()
        with st.spinner("Executando Radar Ações..."):
            try:
                r = _cached_radar("acoes")
                _render_radar(r, "Ações")
            except Exception as e:
                st.error(f"Erro: {e}")

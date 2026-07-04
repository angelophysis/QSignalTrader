"""
QSignalTrader V2 — Radar de Criptos
"""
import streamlit as st

from src.v2.radar_lite import run_stock_radar_v2
from src.v2.crypto_radar_lite import run_crypto_radar_v2
from src.v2.crypto_asset_loader import load_crypto_assets
from src.v2.crypto_analysis import analyze_crypto_v2
from src.v2.config import CRYPTO_REGIME_LABELS, CRYPTO_STRATEGY_LABELS
from src.v2.table_formatting import clean_radar_table

st.set_page_config(page_title="Radar Criptos V2", page_icon="🪙", layout="wide")

st.markdown("""<style>
.v2-card{background:rgba(255,255,255,0.035);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:12px 14px;min-height:78px;overflow:hidden}
.v2-card-title{font-size:0.72rem;color:rgba(255,255,255,0.6);margin-bottom:6px;font-weight:600;text-transform:uppercase;letter-spacing:.4px}
.v2-card-value{font-size:1.1rem;line-height:1.25;font-weight:700;color:rgba(255,255,255,0.94);word-break:break-word}
.v2-card.good{border-color:rgba(46,204,113,0.3)} .v2-card.warn{border-color:rgba(241,196,15,0.3)} .v2-card.bad{border-color:rgba(231,76,60,0.3)}
.v2-badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:.68rem;font-weight:700;margin-top:4px}
.v2-badge.good{background:rgba(46,204,113,0.15);color:#2ecc71} .v2-badge.warn{background:rgba(241,196,15,0.15);color:#f1c40f} .v2-badge.bad{background:rgba(231,76,60,0.15);color:#ff6b6b}
.v2-section{font-size:.78rem;font-weight:700;color:rgba(255,255,255,0.7);text-transform:uppercase;letter-spacing:.5px;margin-top:20px;margin-bottom:10px}
.v2-summary-box{background:rgba(255,255,255,0.03);border-left:3px solid rgba(46,204,113,0.5);border-radius:10px;padding:12px 14px;margin-top:8px;font-size:.88rem;line-height:1.5}
.v2-score-card{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:10px 12px;text-align:center;min-height:72px}
.v2-score-val{font-size:1.3rem;font-weight:800;color:rgba(255,255,255,0.94)}
.v2-score-label{font-size:.65rem;color:rgba(255,255,255,0.5);text-transform:uppercase;letter-spacing:.4px}
.v2-plan-note{margin-top:6px;font-size:.78rem;color:rgba(255,255,255,0.58);line-height:1.35}
</style>""", unsafe_allow_html=True)

st.title("🪙 QSignalTrader V2 — Criptos")
st.caption("Ativos do arquivo radar_cripto.txt → Radar 4h → Análise completa individual")

_LABEL_MAP = {
    **{k: v for k, v in CRYPTO_REGIME_LABELS.items()},
    **{k: v for k, v in CRYPTO_STRATEGY_LABELS.items()},
    "COMPRAR_FORTE": "Comprar forte", "COMPRAR_PARCIAL": "Comprar parcial",
    "AGUARDAR_GATILHO": "Aguardar gatilho", "OBSERVAR": "Observar", "EVITAR": "Evitar",
    "AUMENTAR": "Aumentar", "MANTER": "Manter", "MANTER_COM_CAUTELA": "Manter com cautela",
    "REDUZIR": "Reduzir", "SAIR": "Sair",
    "ALTA": "Alta", "MEDIA": "Média", "BAIXA": "Baixa",
    "FORTE": "Forte", "FRACA": "Fraca", "BOA": "Boa", "RUIM": "Ruim",
    "NEUTRA": "Neutra", "LIDER": "Líder", "BENCHMARK": "Benchmark",
    "OTIMA": "Ótima", "PERIGOSA": "Perigosa", "ACEITAVEL": "Aceitável",
    "CONTROLADO": "Controlado", "EXTREMO": "Extremo",
    "MUITO_FRACA": "Muito fraca", "SAUDAVEL": "Saudável",
    "TRANSICAO": "Transição", "BAIXA_FORTE": "Baixa forte",
    "EXCELENTE": "Excelente", "INDEFINIDO": "Indefinido",
    "CRYPTO_": "", "CRYPTO": "",
}
_LABEL_MAP = {k: v for k, v in _LABEL_MAP.items() if v and k != "CRYPTO"}


def _h(label: str | None) -> str:
    if not label: return "—"
    return _LABEL_MAP.get(label, label.replace("_", " ").replace("CRYPTO ", "").title())


def _fmt_crypto_price(val) -> str:
    if not isinstance(val, (int, float)): return "—"
    if val >= 1000: return f"$ {val:,.2f}"
    if val >= 1: return f"$ {val:,.2f}"
    if val >= 0.01: return f"$ {val:.4f}"
    return f"$ {val:.6f}"


def _card(title: str, value: str, tone: str = "neutral") -> None:
    st.markdown(f'<div class="v2-card {tone}"><div class="v2-card-title">{title}</div><div class="v2-card-value">{value}</div></div>', unsafe_allow_html=True)


def _score_tone(val) -> str:
    if isinstance(val, (int, float)) and val >= 70: return "good"
    if isinstance(val, (int, float)) and val >= 50: return "warn"
    return "bad" if isinstance(val, (int, float)) else "neutral"


def _action_tone(action: str) -> str:
    a = str(action or "")
    if a in ("COMPRAR_FORTE", "COMPRAR_PARCIAL", "AUMENTAR", "MANTER"): return "good"
    if a in ("AGUARDAR_GATILHO", "OBSERVAR", "MANTER_COM_CAUTELA"): return "warn"
    if a in ("EVITAR", "REDUZIR", "SAIR"): return "bad"
    return "neutral"


def _score_card(label: str, score_val, cls_label: str | None = None) -> None:
    tone = _score_tone(score_val)
    v = f"{score_val:.0f}" if isinstance(score_val, (int, float)) else "—"
    badge = f'<span class="v2-badge {tone}">{_h(cls_label)}</span>' if cls_label else ""
    st.markdown(f'<div class="v2-score-card"><div class="v2-score-label">{label}</div><div class="v2-score-val">{v}</div>{badge}</div>', unsafe_allow_html=True)


def _plan_card(title: str, value: str, note: str = "", tone: str = "neutral") -> None:
    note_html = f'<div class="v2-plan-note">{note}</div>' if note else ""
    st.markdown(f'<div class="v2-card {tone}"><div class="v2-card-title">{title}</div><div class="v2-card-value">{value}</div>{note_html}</div>', unsafe_allow_html=True)


# ═══════════════ Load ═══════════════
asset_data = load_crypto_assets()
default_tickers = asset_data["assets"]
tab1, tab2 = st.tabs(["📡 Radar", "🔍 Análise Individual"])


# ═══════════════ Render Analysis ═══════════════
def _render_analysis(symbol):
    try:
        with st.spinner(f"Analisando {symbol}..."):
            analysis = analyze_crypto_v2(symbol)
        if "error" in analysis:
            st.error(analysis["error"])
            return
    except Exception as exc:
        st.error(f"Erro: {exc}")
        with st.expander("Detalhes"): st.exception(exc)
        return

    qs = analysis.get("qsignal_score") or {}
    regime = analysis.get("regime") or {}
    strategy = analysis.get("strategy") or {}
    trend = analysis.get("trend") or {}
    location = analysis.get("location") or {}
    risk = analysis.get("risk") or {}
    btc_rs = analysis.get("btc_relative_strength") or {}
    momentum = analysis.get("momentum") or {}
    formatted = analysis.get("formatted") or {}

    c1, c2, c3, c4 = st.columns([1.2, 1.2, 0.8, 0.8])
    with c1: _card("Regime", _h(regime.get("regime")))
    with c2: _card("Estratégia", _h(strategy.get("strategy")))
    with c3: _card("QSignal Score", f"{qs.get('qsignal_crypto_score', '—')}/100", _score_tone(qs.get("qsignal_crypto_score")))
    with c4: _card("Preço", _fmt_crypto_price(analysis.get("preco_atual")))

    c1, c2, c3 = st.columns(3)
    with c1: _card("Confiança", _h(regime.get("confidence")))
    with c2: _card("Gatilho", _fmt_crypto_price(strategy.get("trigger_level")) if isinstance(strategy.get("trigger_level"), (int, float)) else "—")
    with c3: _card("Invalidação", _fmt_crypto_price(strategy.get("invalidation_level")) if isinstance(strategy.get("invalidation_level"), (int, float)) else "—")

    st.markdown('<div class="v2-section">Componentes do Score</div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: _score_card("Trend", trend.get("trend_score"), trend.get("classification"))
    with c2: _score_card("Momentum", momentum.get("momentum_score"), momentum.get("classification"))
    with c3: _score_card("Location", location.get("location_score"), location.get("classification"))
    with c4: _score_card("BTC RS", btc_rs.get("btc_relative_strength_score"), btc_rs.get("classification"))
    with c5: _score_card("Risk", risk.get("risk_score"), risk.get("classification"))
    with c6:
        dq = qs.get("component_scores", {}).get("data_quality")
        _score_card("Qualidade", dq)

    st.markdown('<div class="v2-section">Suportes &amp; Resistências</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        supports = analysis.get("supports", []) or []
        if supports:
            st.dataframe([{"Nível": s.get("label"), "Preço": _fmt_crypto_price(s.get("price")), "Força": f"{s.get('strength', '—')}", "Dist": f"{s.get('distance_pct', 0):.1f}%"} for s in supports], use_container_width=True, hide_index=True)
        else: st.caption("Níveis insuficientes para suportes.")
    with c2:
        resistances = analysis.get("resistances", []) or []
        if resistances:
            st.dataframe([{"Nível": r.get("label"), "Preço": _fmt_crypto_price(r.get("price")), "Força": f"{r.get('strength', '—')}", "Dist": f"{r.get('distance_pct', 0):.1f}%"} for r in resistances], use_container_width=True, hide_index=True)
        else: st.caption("Níveis insuficientes para resistências.")

    # Plano Operacional
    act_no = strategy.get("action_without_position", "")
    act_with = strategy.get("action_with_position", "")
    trig_val = strategy.get("trigger_level")
    inval_val = strategy.get("invalidation_level")

    trig_label = _fmt_crypto_price(trig_val) if isinstance(trig_val, (int, float)) else "Nenhum gatilho ativo"
    trig_note = "Confirmação desejável para entrada." if isinstance(trig_val, (int, float)) else "Sinais insuficientes para gatilho operacional."
    inv_label = _fmt_crypto_price(inval_val) if isinstance(inval_val, (int, float)) else "Nenhuma invalidação definida"
    inv_note = "Perda desse nível enfraquece a leitura. Em cripto, considerar volatilidade." if isinstance(inval_val, (int, float)) else ""

    st.markdown('<div class="v2-section">Plano Operacional</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1: _plan_card("Gatilho", trig_label, trig_note)
    with c2: _plan_card("Invalidação", inv_label, inv_note)
    c1, c2 = st.columns(2)
    with c1: _plan_card("Sem posição", _h(act_no), "", _action_tone(act_no))
    with c2: _plan_card("Com posição", _h(act_with), "", _action_tone(act_with))

    if strategy.get("main_reason"):
        st.markdown(f'<div class="v2-summary-box">{strategy["main_reason"]}</div>', unsafe_allow_html=True)

    if formatted:
        st.markdown('<div class="v2-section">Leitura</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="v2-summary-box">{formatted.get("summary", "—")}</div>', unsafe_allow_html=True)
        if formatted.get("operational_plan"): st.caption(formatted["operational_plan"])
        c1, c2 = st.columns(2)
        with c1:
            st.caption("**A favor**")
            for r in (formatted.get("bullish_points", analysis.get("reasons", [])))[:5]: st.caption(f"✅ {r}")
        with c2:
            st.caption("**Contra**")
            for w in (formatted.get("bearish_points", analysis.get("warnings", [])))[:5]: st.caption(f"⚠️ {w}")

    errs = analysis.get("errors") or []
    warns = analysis.get("warnings") or []
    if warns:
        with st.expander("Warnings"): 
            for w in warns: st.caption(f"⚠️ {w}")
    if errs:
        with st.expander("Erros técnicos"):
            for e in errs: st.caption(f"• {e.get('module', '?')}: {e.get('error', str(e))}")


# ═══════════════ TAB 1: Radar ═══════════════
with tab1:
    with st.sidebar:
        st.subheader("Radar Cripto")
        st.caption(f"Fonte: {asset_data['source']} ({asset_data['count']} ativos)")
        use_manual = st.checkbox("Usar lista manual")
        if use_manual:
            manual = st.text_area("Lista manual", "BTC/USDT\nETH/USDT\nSOL/USDT")
            tickers = [t.strip().upper() for t in manual.splitlines() if t.strip()]
        else:
            tickers = default_tickers
        min_score = st.slider("Score mínimo", 30, 80, 40, 5)
        max_show = st.slider("Máximo de criptos", 5, 50, 30, 5)
        force = st.checkbox("Forçar atualização")
        run = st.button("🔎 Rodar Radar Cripto", use_container_width=True)

    if not run:
        st.info("Clique em **Rodar Radar Cripto** para analisar ativos de `radar_cripto.txt`.")
    else:
        if force: st.cache_data.clear()
        with st.spinner(f"Analisando {len(tickers)} criptos..."):
            try:
                result = run_crypto_radar_v2(symbols=tickers, min_score=min_score, max_tickers=max_show)
            except Exception as e:
                st.error(f"Erro: {e}"); st.stop()

        diag = result.get("diagnostics", {})
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Carregados", diag.get("loaded", 0)); c2.metric("Processados", diag.get("processed", 0))
        c3.metric("Aprovados", diag.get("approved", 0)); c4.metric("Rejeitados", diag.get("rejected", 0))
        c5.metric("Erros", diag.get("errors", 0))

        candidates = result.get("candidates")
        rejected = result.get("rejected")
        errors_df = result.get("errors")

        if candidates is not None and not candidates.empty:
            display_df = clean_radar_table(candidates)
            st.subheader(f"Candidatos — {len(candidates)} criptos com score ≥ {min_score}")
            try:
                st.dataframe(display_df, use_container_width=True, hide_index=True,
                             column_config={"Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d")})
            except Exception:
                st.dataframe(display_df, use_container_width=True, hide_index=True)
            ticker_sel = st.selectbox("Selecionar para análise detalhada", candidates["Symbol"].tolist())
            if st.button("🔍 Analisar Cripto Selecionada"): _render_analysis(ticker_sel)
        else:
            st.info(f"Nenhuma cripto atingiu score ≥ {min_score}.")
            if rejected is not None and not rejected.empty:
                st.subheader("Top rejeitados abaixo do corte")
                top_rej = rejected.head(10)
                st.dataframe(clean_radar_table(top_rej), use_container_width=True, hide_index=True)
                ticker_sel = st.selectbox("Selecionar para análise detalhada", top_rej["Symbol"].tolist())
                if st.button("🔍 Analisar mesmo assim"): _render_analysis(ticker_sel)

        if rejected is not None and not rejected.empty:
            with st.expander(f"Rejeitados ({len(rejected)})"):
                st.dataframe(clean_radar_table(rejected), use_container_width=True, hide_index=True)
        if errors_df is not None and not errors_df.empty:
            with st.expander(f"Erros ({len(errors_df)})"): st.dataframe(errors_df, use_container_width=True, hide_index=True)


# ═══════════════ TAB 2: Análise Individual ═══════════════
with tab2:
    st.subheader("Análise Individual Cripto V2")
    st.caption("Digite um símbolo ou escolha da lista.")
    c1, c2 = st.columns([1, 1])
    with c1: manual_sym = st.text_input("Digite um símbolo", placeholder="BTC/USDT, ETH/USDT, SOL/USDT")
    with c2: select_sym = st.selectbox("Ou escolha da lista", [""] + default_tickers) if default_tickers else ""
    sym_to_analyze = manual_sym.strip().upper() if manual_sym.strip() else select_sym

    if sym_to_analyze and st.button("🔍 Analisar Cripto", use_container_width=True):
        try:
            _render_analysis(sym_to_analyze)
        except Exception as exc:
            st.error(f"Erro: {exc}")
            with st.expander("Detalhes"): st.exception(exc)

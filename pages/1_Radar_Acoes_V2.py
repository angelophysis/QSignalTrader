"""
QSignalTrader V2 — Radar de Ações
"""
import streamlit as st

from src.v2.config import DEFAULT_MIN_SCORE, DEFAULT_MAX_TICKERS, RADAR_MODES, IBOVESPA_TICKERS
from src.v2.radar_lite import run_stock_radar_v2
from src.v2.stock_analysis import analyze_stock_v2
from src.v2.asset_loader import load_stock_assets

st.set_page_config(page_title="Radar Ações V2", page_icon="📊", layout="wide")

st.title("📊 QSignalTrader V2 — Ações")
st.caption("Ativos do arquivo radar_acoes.txt → Filtro leve → Candidatos → Análise detalhada individual")

tab1, tab2 = st.tabs(["📡 Radar", "🔍 Análise Individual"])

# ── Load assets ──
asset_data = load_stock_assets()
default_tickers = asset_data["assets"]


# ═══════════════════════════════════════════════
# Shared: render individual analysis
# ═══════════════════════════════════════════════
def _render_analysis(ticker):
    try:
        with st.spinner(f"Analisando {ticker}..."):
            analysis = analyze_stock_v2(ticker)

        if "error" in analysis:
            st.error(analysis["error"])
            return
    except Exception as exc:
        st.error(f"Erro ao analisar {ticker}: {exc}")
        with st.expander("Detalhes técnicos"):
            st.exception(exc)
        return

    qs = analysis.get("qsignal_score") or {}
    regime = analysis.get("regime") or {}
    strategy = analysis.get("strategy") or {}
    trend = analysis.get("trend") or {}
    location = analysis.get("location") or {}
    risk = analysis.get("risk") or {}
    rs = analysis.get("relative_strength") or {}
    momentum = analysis.get("momentum") or {}

    c1, c2, c3 = st.columns(3)
    c1.metric("Regime", str(regime.get("regime", "—")))
    c2.metric("Estratégia", str(strategy.get("strategy", "—")))
    c3.metric("QSignalScore", f"{qs.get('qsignal_stock_score', '—')}/100")

    c1, c2, c3, c4 = st.columns(4)
    preco_str = f"R$ {analysis.get('preco_atual', 0):.2f}" if isinstance(analysis.get('preco_atual'), (int, float)) else "—"
    c1.metric("Preço", preco_str)
    c2.metric("Confiança", str(regime.get("confidence", "—")))
    c3.metric("Sem posição", str(strategy.get("action_without_position", "—")))
    c4.metric("Com posição", str(strategy.get("action_with_position", "—")))

    st.subheader("Componentes do Score")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Trend", f"{trend.get('trend_score', '—')}", delta=str(trend.get("classification", "")))
    c2.metric("Momentum", f"{momentum.get('momentum_score', '—')}", delta=str(momentum.get("classification", "")))
    c3.metric("Location", f"{location.get('location_score', '—')}", delta=str(location.get("classification", "")))
    c4.metric("RS", f"{rs.get('relative_strength_score', '—')}", delta=str(rs.get("classification", "")))
    c5.metric("Risk", f"{risk.get('risk_score', '—')}", delta=str(risk.get("classification", "")))
    c6.metric("Qualidade", f"{qs.get('component_scores', {}).get('data_quality', '—')}")

    st.subheader("Suportes & Resistências")
    c1, c2 = st.columns(2)
    with c1:
        supports = analysis.get("supports", []) or []
        if supports:
            st.dataframe([{"Nível": s.get("label", "—"), "Preço": f"{s.get('price', 0):.2f}" if s.get('price') else "—",
                            "Força": f"{s.get('strength', '—')}/100", "Dist": f"{s.get('distance_pct', 0):.1f}%"}
                           for s in supports], use_container_width=True, hide_index=True)
        else:
            st.caption("Níveis insuficientes para suportes.")
    with c2:
        resistances = analysis.get("resistances", []) or []
        if resistances:
            st.dataframe([{"Nível": r.get("label", "—"), "Preço": f"{r.get('price', 0):.2f}" if r.get('price') else "—",
                            "Força": f"{r.get('strength', '—')}/100", "Dist": f"{r.get('distance_pct', 0):.1f}%"}
                           for r in resistances], use_container_width=True, hide_index=True)
        else:
            st.caption("Níveis insuficientes para resistências.")

    trigger_val = strategy.get("trigger_level")
    inval_val = strategy.get("invalidation_level")
    if trigger_val or inval_val:
        c1, c2 = st.columns(2)
        c1.metric("Gatilho", f"{trigger_val:.2f}" if isinstance(trigger_val, (int, float)) else "—")
        c2.metric("Invalidação", f"{inval_val:.2f}" if isinstance(inval_val, (int, float)) else "—")

    formatted = analysis.get("formatted", {})
    if formatted:
        st.subheader("Leitura")
        st.info(formatted.get("summary", "—"))
        st.caption(formatted.get("operational_plan", ""))

    c1, c2 = st.columns(2)
    with c1:
        st.caption("**Motivos a favor**")
        for r in (formatted.get("bullish_points", analysis.get("reasons", [])))[:6]:
            st.caption(f"✅ {r}")
    with c2:
        st.caption("**Atenções**")
        for w in (formatted.get("bearish_points", analysis.get("warnings", [])))[:6]:
            st.caption(f"⚠️ {w}")


# ═══════════════════════════════════════════════
# TAB 1: Radar
# ═══════════════════════════════════════════════
with tab1:
    with st.sidebar:
        st.subheader("Configuração do Radar")
        st.caption(f"Fonte: {asset_data['source']} ({asset_data['count']} ativos)")

        use_manual = st.checkbox("Usar lista manual nesta execução")
        if use_manual:
            manual = st.text_area("Lista manual (um por linha)", "AAPL\nMSFT\nNVDA\nTSLA\nPETR4.SA")
            tickers = [t.strip().upper() for t in manual.splitlines() if t.strip()]
        else:
            tickers = default_tickers

        mode = st.selectbox("Modo de Radar", ["Todos"] + list(RADAR_MODES.values()))
        mode_filter = None if mode == "Todos" else [k for k, v in RADAR_MODES.items() if v == mode][0]
        min_score = st.slider("Score mínimo", 40, 90, DEFAULT_MIN_SCORE, 5)
        max_show = st.slider("Máximo de ações", 5, 100, DEFAULT_MAX_TICKERS, 5)
        force = st.checkbox("Forçar atualização (ignorar cache)")
        run = st.button("🔎 Rodar Radar", use_container_width=True)

    if not run:
        st.info("Clique em **Rodar Radar** para analisar os ativos configurados em `radar_acoes.txt`.")
        if not tickers:
            st.warning("Nenhum ativo carregado. Edite `radar_acoes.txt` ou use a lista manual.")
    else:
        if force:
            st.cache_data.clear()

        with st.spinner(f"Analisando {len(tickers)} ações..."):
            try:
                result = run_stock_radar_v2(
                    tickers=tickers, min_score=min_score,
                    mode_filter=mode_filter, max_tickers=max_show,
                )
            except Exception as e:
                st.error(f"Erro no radar: {e}")
                st.stop()

        diag = result.get("diagnostics", {})
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Carregados", diag.get("loaded", 0))
        c2.metric("Processados", diag.get("processed", 0))
        c3.metric("Aprovados", diag.get("approved", 0))
        c4.metric("Rejeitados", diag.get("rejected", 0))
        c5.metric("Erros", diag.get("errors", 0))

        candidates = result.get("candidates")
        rejected = result.get("rejected")
        errors_df = result.get("errors")

        if candidates is not None and not candidates.empty:
            st.subheader(f"Candidatos — {len(candidates)} ações com score ≥ {min_score}")
            st.dataframe(candidates, use_container_width=True, hide_index=True,
                         column_config={"RadarLiteScore": st.column_config.ProgressColumn(format="%d", min_value=0, max_value=100)})

            ticker_sel = st.selectbox("Selecionar para análise detalhada", candidates["Ticker"].tolist())
            if st.button("🔍 Analisar Ação Selecionada"):
                _render_analysis(ticker_sel)
        else:
            st.info(f"Nenhuma ação atingiu o score mínimo ({min_score}).")
            if rejected is not None and not rejected.empty:
                st.subheader("Top rejeitados abaixo do corte")
                top_rej = rejected.head(10)
                st.dataframe(top_rej, use_container_width=True, hide_index=True)
                ticker_sel = st.selectbox("Selecionar para análise detalhada", top_rej["Ticker"].tolist())
                if st.button("🔍 Analisar mesmo assim"):
                    _render_analysis(ticker_sel)

        if rejected is not None and not rejected.empty:
            with st.expander(f"Todos os rejeitados ({len(rejected)})"):
                st.dataframe(rejected, use_container_width=True, hide_index=True)

        if errors_df is not None and not errors_df.empty:
            with st.expander(f"Erros ({len(errors_df)})"):
                st.dataframe(errors_df, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════
# TAB 2: Análise Individual
# ═══════════════════════════════════════════════
with tab2:
    st.subheader("Análise Individual V2")
    st.caption("Digite qualquer ticker ou escolha um ativo do arquivo para análise completa.")

    c1, c2 = st.columns([1, 1])
    with c1:
        manual_ticker = st.text_input("Digite um ticker", placeholder="Ex: AAPL, PETR4.SA, MSFT")
    with c2:
        if default_tickers:
            select_ticker = st.selectbox("Ou escolha da lista", [""] + default_tickers)
        else:
            select_ticker = ""

    ticker_to_analyze = manual_ticker.strip().upper() if manual_ticker.strip() else select_ticker

    if ticker_to_analyze and st.button("🔍 Analisar Ativo", use_container_width=True):
        try:
            _render_analysis(ticker_to_analyze)
        except Exception as exc:
            st.error(f"Erro ao processar análise de {ticker_to_analyze}. A aplicação continua funcionando.")
            with st.expander("Detalhes técnicos"):
                st.exception(exc)

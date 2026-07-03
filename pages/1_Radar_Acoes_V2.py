"""
QSignalTrader V2 — Radar de Ações
"""
import streamlit as st

from src.v2.config import (
    BREAKOUT_MAX_DIST_FROM_20D_HIGH,
    DEFAULT_MIN_SCORE,
    DEFAULT_MAX_TICKERS,
    IBOVESPA_TICKERS,
    US_TICKERS,
    RADAR_MODES,
)
from src.v2.radar_lite import run_stock_radar_v2
from src.v2.stock_analysis import analyze_stock_v2

st.set_page_config(page_title="Radar Ações V2", page_icon="📊", layout="wide")

st.title("📊 QSignalTrader V2 — Radar de Ações")
st.caption("Filtro leve → Score → Modos → Análise detalhada sob demanda")

# ── Sidebar ──
with st.sidebar:
    st.subheader("Configuração do Radar")
    universe = st.selectbox("Universo", ["Ibovespa", "US", "Personalizado"])
    if universe == "Ibovespa":
        tickers = IBOVESPA_TICKERS
    elif universe == "US":
        tickers = US_TICKERS
    else:
        custom = st.text_area("Lista personalizada (um por linha)", "AAPL\nMSFT\nNVDA\nTSLA")
        tickers = [t.strip().upper() for t in custom.splitlines() if t.strip()]

    mode = st.selectbox("Modo de Radar", ["Todos"] + list(RADAR_MODES.values()))
    mode_filter = None if mode == "Todos" else [k for k, v in RADAR_MODES.items() if v == mode][0]

    min_score = st.slider("Score mínimo", 40, 90, DEFAULT_MIN_SCORE, 5)
    max_show = st.slider("Máximo de ações", 5, 100, DEFAULT_MAX_TICKERS, 5)
    force = st.checkbox("Forçar atualização (ignorar cache)")

    run = st.button("🔎 Rodar Radar", use_container_width=True)

# ── Main ──
if run:
    if force:
        st.cache_data.clear()

    with st.spinner(f"Analisando {len(tickers)} ações..."):
        try:
            df = run_stock_radar_v2(
                tickers=tickers,
                min_score=min_score,
                mode_filter=mode_filter,
                max_tickers=max_show,
            )
        except Exception as e:
            st.error(f"Erro no radar: {e}")
            st.stop()

    if df.empty:
        st.info("Nenhuma ação encontrada com os critérios atuais.")
    else:
        st.subheader(f"Resultados — {len(df)} ações com score ≥ {min_score}")
        st.dataframe(df, use_container_width=True, hide_index=True,
                     column_config={
                         "RadarLiteScore": st.column_config.ProgressColumn(format="%d", min_value=0, max_value=100),
                         "Preco": st.column_config.NumberColumn(format="R$ %.2f"),
                     })

        # ── Detalhes ──
        ticker_sel = st.selectbox("Selecionar ação para análise detalhada", df["Ticker"].tolist())
        if st.button("🔍 Analisar Ação Selecionada"):
            with st.spinner(f"Analisando {ticker_sel}..."):
                analysis = analyze_stock_v2(ticker_sel)

            if "error" in analysis:
                st.error(analysis["error"])
            else:
                # ── Top summary cards ──
                qs = analysis.get("qsignal_score", {})
                regime = analysis.get("regime", {})
                strategy = analysis.get("strategy", {})
                trend = analysis.get("trend", {})
                location = analysis.get("location", {})
                risk = analysis.get("risk", {})
                rs = analysis.get("relative_strength", {})

                c1, c2, c3 = st.columns(3)
                c1.metric("Regime", regime.get("regime", "—"))
                c2.metric("Estratégia", strategy.get("strategy", "—"))
                c3.metric("QSignalScore", f"{qs.get('qsignal_stock_score', '—')}/100")

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Preço", f"R$ {analysis['preco_atual']:.2f}" if analysis.get("preco_atual") else "—")
                c2.metric("Confiança", regime.get("confidence", "—"))
                c3.metric("Sem posição", strategy.get("action_without_position", "—"))
                c4.metric("Com posição", strategy.get("action_with_position", "—"))

                # ── Score components ──
                st.subheader("Componentes do Score")
                comps = qs.get("component_scores", {})
                c1, c2, c3, c4, c5, c6 = st.columns(6)
                c1.metric("Trend", f"{trend.get('trend_score', '—')}", delta=trend.get("classification", ""))
                c2.metric("Momentum", f"{analysis['momentum'].get('momentum_score', '—')}", delta=analysis["momentum"].get("classification", ""))
                c3.metric("Location", f"{location.get('location_score', '—')}", delta=location.get("classification", ""))
                c4.metric("RS", f"{rs.get('relative_strength_score', '—')}", delta=rs.get("classification", ""))
                c5.metric("Risk", f"{risk.get('risk_score', '—')}", delta=risk.get("classification", ""))
                c6.metric("Qualidade", f"{comps.get('data_quality', '—')}")

                # ── S/R ──
                st.subheader("Suportes & Resistências")
                c1, c2 = st.columns(2)
                with c1:
                    supports = analysis.get("supports", [])
                    if supports:
                        st.caption("**Suportes**")
                        st.dataframe([{"Nível": s.get("label"), "Preço": f"{s['price']:.2f}",
                                        "Força": f"{s.get('strength', '—')}/100", "Dist": f"{s.get('distance_pct', 0):.1f}%"}
                                       for s in supports], use_container_width=True, hide_index=True)
                with c2:
                    resistances = analysis.get("resistances", [])
                    if resistances:
                        st.caption("**Resistências**")
                        st.dataframe([{"Nível": r.get("label"), "Preço": f"{r['price']:.2f}",
                                        "Força": f"{r.get('strength', '—')}/100", "Dist": f"{r.get('distance_pct', 0):.1f}%"}
                                       for r in resistances], use_container_width=True, hide_index=True)

                # ── Trigger / Invalidation ──
                if strategy.get("trigger_level") or strategy.get("invalidation_level"):
                    c1, c2 = st.columns(2)
                    c1.metric("Gatilho", f"{strategy['trigger_level']:.2f}" if strategy.get("trigger_level") else "—")
                    c2.metric("Invalidação", f"{strategy['invalidation_level']:.2f}" if strategy.get("invalidation_level") else "—")

                # ── Formatted output ──
                formatted = analysis.get("formatted", {})
                if formatted:
                    st.subheader("Leitura")
                    st.info(formatted.get("summary", "—"))
                    st.caption(formatted.get("operational_plan", ""))

                # ── Reasons / Warnings ──
                c1, c2 = st.columns(2)
                with c1:
                    st.caption("**Motivos a favor**")
                    pts = formatted.get("bullish_points", analysis.get("reasons", []))
                    for r in pts[:6]:
                        st.caption(f"✅ {r}")
                with c2:
                    st.caption("**Atenções**")
                    pts2 = formatted.get("bearish_points", analysis.get("warnings", []))
                    for w in pts2[:6]:
                        st.caption(f"⚠️ {w}")
                    for w in analysis.get("warnings", []):
                        st.caption(f"⚠️ {w}")

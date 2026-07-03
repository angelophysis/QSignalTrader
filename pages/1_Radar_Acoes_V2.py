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
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Preço", f"R$ {analysis['preco_atual']:.2f}" if analysis.get("preco_atual") else "—")
                c2.metric("RadarLiteScore", f"{analysis.get('radar_lite_score', '—')}/100")
                c3.metric("Status", analysis.get("status", "—"))
                c4.metric("Modo", ", ".join(analysis.get("radar_modes", [])) or "—")

                mom = analysis.get("momentum", {})
                st.subheader("Momentum")
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Score", f"{mom.get('momentum_score', '—')}/100")
                c2.metric("Classificação", mom.get("classification", "—"))
                c3.metric("RSI", f"{mom.get('rsi', '—')}")
                c4.metric("RSI Δ3", f"{mom.get('rsi_delta_3', '—')}")
                c5.metric("ROC10", f"{mom.get('roc_10', '—')}%")

                # Suportes
                st.subheader("Suportes")
                supports = analysis.get("supports", [])
                if supports:
                    sup_rows = []
                    for s in supports:
                        sup_rows.append({
                            "Nível": s.get("label", "—"),
                            "Preço": f"{s['price']:.2f}",
                            "Força": f"{s.get('strength', '—')}/100",
                            "Distância": f"{s.get('distance_pct', 0):.1f}%",
                            "Fontes": ", ".join(s.get("sources", [])[:4]),
                        })
                    st.dataframe(sup_rows, use_container_width=True, hide_index=True)
                else:
                    st.caption("Nenhum suporte encontrado.")

                # Resistências
                st.subheader("Resistências")
                resistances = analysis.get("resistances", [])
                if resistances:
                    res_rows = []
                    for r in resistances:
                        res_rows.append({
                            "Nível": r.get("label", "—"),
                            "Preço": f"{r['price']:.2f}",
                            "Força": f"{r.get('strength', '—')}/100",
                            "Distância": f"{r.get('distance_pct', 0):.1f}%",
                            "Fontes": ", ".join(r.get("sources", [])[:4]),
                        })
                    st.dataframe(res_rows, use_container_width=True, hide_index=True)
                else:
                    st.caption("Nenhuma resistência encontrada.")

                # Leitura
                st.subheader("Leitura")
                st.info(analysis.get("leitura", "—"))

                # Reasons / Warnings
                c1, c2 = st.columns(2)
                with c1:
                    st.caption("**Motivos a favor**")
                    for r in analysis.get("reasons", []):
                        st.caption(f"✅ {r}")
                with c2:
                    st.caption("**Atenções**")
                    for w in analysis.get("warnings", []):
                        st.caption(f"⚠️ {w}")

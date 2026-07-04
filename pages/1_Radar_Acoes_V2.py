"""
QSignalTrader V2 — Radar de Ações
"""
import streamlit as st

from src.v2.config import DEFAULT_MIN_SCORE, DEFAULT_MAX_TICKERS, RADAR_MODES
from src.v2.radar_lite import run_stock_radar_v2
from src.v2.stock_analysis import analyze_stock_v2
from src.v2.asset_loader import load_stock_assets
from src.v2.table_formatting import clean_radar_table

st.set_page_config(page_title="Radar Ações V2", page_icon="📊", layout="wide")

# ═══════════════════════ CSS ═══════════════════════
st.markdown("""
<style>
.v2-card {
    background: rgba(255,255,255,0.035);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 12px 14px;
    min-height: 78px;
    overflow: hidden;
}
.v2-card-title {
    font-size: 0.72rem;
    color: rgba(255,255,255,0.6);
    margin-bottom: 6px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}
.v2-card-value {
    font-size: 1.1rem;
    line-height: 1.25;
    font-weight: 700;
    color: rgba(255,255,255,0.94);
    word-break: break-word;
}
.v2-card.good { border-color: rgba(46,204,113,0.3); }
.v2-card.warn { border-color: rgba(241,196,15,0.3); }
.v2-card.bad { border-color: rgba(231,76,60,0.3); }
.v2-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 0.68rem;
    font-weight: 700;
    margin-top: 4px;
}
.v2-badge.good { background: rgba(46,204,113,0.15); color: #2ecc71; }
.v2-badge.warn { background: rgba(241,196,15,0.15); color: #f1c40f; }
.v2-badge.bad { background: rgba(231,76,60,0.15); color: #ff6b6b; }
.v2-badge.neutral { background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.55); }
.v2-section {
    font-size: 0.78rem;
    font-weight: 700;
    color: rgba(255,255,255,0.7);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-top: 20px;
    margin-bottom: 10px;
}
.v2-summary-box {
    background: rgba(255,255,255,0.03);
    border-left: 3px solid rgba(46,204,113,0.5);
    border-radius: 10px;
    padding: 12px 14px;
    margin-top: 8px;
    font-size: 0.88rem;
    line-height: 1.5;
}
.v2-score-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
    padding: 10px 12px;
    text-align: center;
    min-height: 72px;
}
.v2-score-val {
    font-size: 1.3rem;
    font-weight: 800;
    color: rgba(255,255,255,0.94);
}
.v2-score-label {
    font-size: 0.65rem;
    color: rgba(255,255,255,0.5);
    text-transform: uppercase;
    letter-spacing: 0.4px;
}
.v2-plan-note {
    margin-top: 6px;
    font-size: 0.78rem;
    color: rgba(255,255,255,0.58);
    line-height: 1.35;
}
</style>
""", unsafe_allow_html=True)

st.title("📊 QSignalTrader V2 — Ações")
st.caption("Ativos do arquivo radar_acoes.txt → Filtro leve → Candidatos → Análise detalhada individual")

tab1, tab2 = st.tabs(["📡 Radar", "🔍 Análise Individual"])

asset_data = load_stock_assets()
default_tickers = asset_data["assets"]

# ═══════════════════════ Helpers ═══════════════════════
_LABEL_MAP = {
    "PULLBACK_DE_ALTA": "Pullback de alta", "BULL_FORTE": "Bull forte",
    "BULL_SAUDAVEL": "Bull saudável", "BREAKOUT_SETUP": "Breakout setup",
    "BREAKOUT_CONFIRMADO": "Breakout confirmado", "RECUPERACAO": "Recuperação",
    "DISTRIBUICAO": "Distribuição", "BEAR_FORTE": "Bear forte",
    "LATERALIZACAO": "Lateralização", "INDEFINIDO": "Indefinido",
    "NO_TRADE": "No trade", "TREND_CONTINUATION": "Continuação de tendência",
    "PULLBACK_BUY": "Compra no pullback", "BREAKOUT_CONFIRMATION": "Confirmação de breakout",
    "RECOVERY_WATCH": "Monitorar recuperação", "DEFENSIVE_MODE": "Modo defensivo",
    "COMPRAR_FORTE": "Comprar forte", "COMPRAR_PARCIAL": "Comprar parcial",
    "AGUARDAR_GATILHO": "Aguardar gatilho", "OBSERVAR": "Observar", "EVITAR": "Evitar",
    "AUMENTAR": "Aumentar", "MANTER": "Manter", "MANTER_COM_CAUTELA": "Manter com cautela",
    "REDUZIR": "Reduzir", "SAIR": "Sair",
    "ALTA": "Alta", "MEDIA": "Média", "BAIXA": "Baixa",
    "FORTE": "Forte", "FRACO": "Fraco", "OTIMA": "Ótima", "BOA": "Boa",
    "NEUTRA": "Neutra", "RUIM": "Ruim", "CONTROLADO": "Controlado",
    "ACEITAVEL": "Aceitável", "LIDER": "Líder", "PERIGOSA": "Perigosa",
    "EXTREMO": "Extremo", "MUITO_FRACA": "Muito fraca",
    "SAUDAVEL": "Saudável", "TRANSICAO": "Transição",
    "BAIXA_FORTE": "Baixa forte", "EXCELENTE": "Excelente",
    "BOM_CANDIDATO": "Bom candidato", "PRIORIDADE_ALTA": "Prioridade alta",
}


def _h(label: str | None) -> str:
    if not label:
        return "—"
    return _LABEL_MAP.get(label, label.replace("_", " ").title())


def _fmt_price(ticker: str, val) -> str:
    if not isinstance(val, (int, float)):
        return "—"
    sym = "R$" if (ticker or "").upper().endswith(".SA") else "$"
    return f"{sym} {val:,.2f}"


def _card(title: str, value: str, tone: str = "neutral") -> None:
    st.markdown(
        f'<div class="v2-card {tone}"><div class="v2-card-title">{title}</div>'
        f'<div class="v2-card-value">{value}</div></div>',
        unsafe_allow_html=True,
    )


def _score_tone(val) -> str:
    if not isinstance(val, (int, float)):
        return "neutral"
    if val >= 70:
        return "good"
    if val >= 50:
        return "warn"
    return "bad"


def _action_tone(action: str) -> str:
    a = str(action or "")
    if a in ("COMPRAR_FORTE", "COMPRAR_PARCIAL", "AUMENTAR", "MANTER"):
        return "good"
    if a in ("AGUARDAR_GATILHO", "OBSERVAR", "MANTER_COM_CAUTELA"):
        return "warn"
    if a in ("EVITAR", "REDUZIR", "SAIR"):
        return "bad"
    return "neutral"


def _score_card(label: str, score_val, cls_label: str | None = None) -> None:
    tone = _score_tone(score_val)
    v = f"{score_val:.0f}" if isinstance(score_val, (int, float)) else "—"
    badge = f'<span class="v2-badge {tone}">{_h(cls_label)}</span>' if cls_label else ""
    st.markdown(
        f'<div class="v2-score-card"><div class="v2-score-label">{label}</div>'
        f'<div class="v2-score-val">{v}</div>{badge}</div>',
        unsafe_allow_html=True,
    )


def _plan_card(title: str, value: str, note: str = "", tone: str = "neutral") -> None:
    note_html = f'<div class="v2-plan-note">{note}</div>' if note else ""
    st.markdown(
        f'<div class="v2-card {tone}"><div class="v2-card-title">{title}</div>'
        f'<div class="v2-card-value">{value}</div>{note_html}</div>',
        unsafe_allow_html=True,
    )


def _trigger_desc(strat, trigger_val, momentum, location, risk, ticker) -> tuple[str, str]:
    strat_name = strat.get("strategy", "")
    if isinstance(trigger_val, (int, float)):
        return (_fmt_price(ticker, trigger_val),
                "Confirmação desejável: fechamento acima do gatilho com volume e momentum.")
    if strat_name in ("NO_TRADE", "DEFENSIVE_MODE"):
        return ("Nenhum gatilho ativo", "Estratégia atual não favorece entrada. Aguardar mudança de cenário.")
    m = momentum.get("momentum_score", 0)
    l = location.get("location_score", 0)
    r = risk.get("risk_score", 0)
    reasons = []
    if isinstance(m, (int, float)) and m < 50:
        reasons.append("momentum fraco")
    if isinstance(l, (int, float)) and l < 50:
        reasons.append("localização desfavorável")
    if isinstance(r, (int, float)) and r < 50:
        reasons.append("risco elevado")
    if reasons:
        return ("Nenhum gatilho ativo", f"Motivo: {', '.join(reasons)}.")
    return ("Nenhum gatilho ativo", "Sinais insuficientes para definir um gatilho operacional.")


def _invalidation_desc(action_with, inval_val, ticker) -> tuple[str, str]:
    if isinstance(inval_val, (int, float)):
        desc = "Perda desse nível enfraquece a leitura atual. "
        if action_with == "MANTER_COM_CAUTELA":
            desc += "Para quem já está posicionado, serve como alerta para reavaliar."
        elif action_with == "REDUZIR":
            desc += "Se perdido, a leitura favorece redução de exposição."
        elif action_with == "SAIR":
            desc += "Se perdido, a leitura favorece saída."
        elif action_with == "MANTER":
            desc += "Enquanto preservado, a estrutura principal segue válida."
        return (_fmt_price(ticker, inval_val), desc)
    return ("Nenhuma invalidação definida", "O sistema não encontrou suporte técnico confiável para invalidação.")


def _no_position_desc(action: str) -> tuple[str, str]:
    m = {
        "COMPRAR_FORTE": ("Comprar forte", "Leitura favorável para entrada, respeitando gestão de risco."),
        "COMPRAR_PARCIAL": ("Comprar parcial", "Entrada parcial pode fazer sentido, evitando alocação total de uma vez."),
        "AGUARDAR_GATILHO": ("Aguardar gatilho", "Aguardar confirmação técnica antes de entrar."),
        "OBSERVAR": ("Observar", "Ativo merece acompanhamento, mas ainda sem entrada clara."),
        "EVITAR": ("Evitar", "Não há entrada técnica clara no momento."),
    }
    label, desc = m.get(action, (_h(action), "Sem orientação operacional definida."))
    return (label, desc)


def _with_position_desc(action: str) -> tuple[str, str]:
    m = {
        "AUMENTAR": ("Aumentar", "Leitura favorece aumento gradual, desde que risco continue controlado."),
        "MANTER": ("Manter", "Posição pode ser mantida enquanto a estrutura técnica seguir válida."),
        "MANTER_COM_CAUTELA": ("Manter com cautela", "Manter, mas acompanhar invalidação e enfraquecimento do momentum."),
        "REDUZIR": ("Reduzir", "Leitura sugere reduzir exposição para controlar risco."),
        "SAIR": ("Sair", "Leitura sugere zerar ou sair da posição."),
    }
    label, desc = m.get(action, (_h(action), "Sem orientação operacional definida."))
    return (label, desc)


def _build_operational_summary(strategy, momentum, location, risk, qsignal) -> str:
    sn = strategy.get("strategy", "")
    mn = momentum.get("momentum_score", 0)
    qs = qsignal.get("qsignal_stock_score", 0)
    if sn == "NO_TRADE":
        if isinstance(mn, (int, float)) and mn < 50:
            return "O sistema não encontrou confirmação suficiente para nova entrada. O momentum ainda está fraco, por isso a leitura sem posição favorece evitar. Para quem já está posicionado, a orientação é acompanhar a invalidação e manter cautela."
        return "A ação tem estrutura razoável, mas o sistema não encontrou confirmação suficiente para entrada. Aguardar melhora dos sinais técnicos."
    if sn in ("TREND_CONTINUATION", "PULLBACK_BUY"):
        return "A leitura favorece entrada, pois o conjunto de tendência, localização e risco está aceitável. Ainda assim, o ideal é respeitar o nível de invalidação indicado."
    if sn in ("BREAKOUT_CONFIRMATION", "BREAKOUT_SETUP"):
        return "A leitura ainda depende de confirmação do breakout. O ativo merece acompanhamento, mas a entrada fica condicionada ao gatilho indicado."
    if sn == "RECOVERY_WATCH":
        return "Recuperação em andamento. A leitura é cautelosa porque ainda não há tendência confirmada. Tamanho reduzido e atenção ao gatilho são recomendados."
    if sn == "DEFENSIVE_MODE":
        return "Cenário desfavorável para compras. A leitura favorece proteger capital e aguardar condições melhores."
    return "A leitura operacional depende da confirmação dos sinais técnicos. Acompanhar gatilho e invalidação."


def _render_operational_plan(analysis: dict, ticker: str) -> None:
    strategy = analysis.get("strategy") or {}
    momentum = analysis.get("momentum") or {}
    location = analysis.get("location") or {}
    risk = analysis.get("risk") or {}
    qs = analysis.get("qsignal_score") or {}

    trigger_val = strategy.get("trigger_level")
    inval_val = strategy.get("invalidation_level")
    act_no = strategy.get("action_without_position", "")
    act_with = strategy.get("action_with_position", "")

    trig_label, trig_note = _trigger_desc(strategy, trigger_val, momentum, location, risk, ticker)
    inv_label, inv_note = _invalidation_desc(act_with, inval_val, ticker)
    np_label, np_note = _no_position_desc(act_no)
    wp_label, wp_note = _with_position_desc(act_with)

    st.markdown('<div class="v2-section">Plano Operacional</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        _plan_card("Gatilho", trig_label, trig_note)
    with c2:
        _plan_card("Invalidação", inv_label, inv_note)

    c1, c2 = st.columns(2)
    with c1:
        _plan_card("Sem posição", np_label, np_note, _action_tone(act_no))
    with c2:
        _plan_card("Com posição", wp_label, wp_note, _action_tone(act_with))

    summary = _build_operational_summary(strategy, momentum, location, risk, qs)
    st.markdown(f'<div class="v2-summary-box">{summary}</div>', unsafe_allow_html=True)


# ═══════════════════════ Render Analysis ═══════════════════════
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
    formatted = analysis.get("formatted") or {}

    # ── Top cards ──
    c1, c2, c3, c4 = st.columns([1.2, 1.2, 0.8, 0.8])
    with c1:
        _card("Regime", _h(regime.get("regime")))
    with c2:
        _card("Estratégia", _h(strategy.get("strategy")))
    with c3:
        _card("QSignal Score", f"{qs.get('qsignal_stock_score', '—')}/100", _score_tone(qs.get("qsignal_stock_score")))
    with c4:
        _card("Preço", _fmt_price(ticker, analysis.get("preco_atual")))

    c1, c2, c3 = st.columns(3)
    with c1:
        _card("Confiança", _h(regime.get("confidence")))
    with c2:
        _card("Gatilho", _fmt_price(ticker, strategy.get("trigger_level")) if isinstance(strategy.get("trigger_level"), (int, float)) else "—")
    with c3:
        _card("Invalidação", _fmt_price(ticker, strategy.get("invalidation_level")) if isinstance(strategy.get("invalidation_level"), (int, float)) else "—")

    # ── Componentes do Score ──
    st.markdown('<div class="v2-section">Componentes do Score</div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        _score_card("Trend", trend.get("trend_score"), trend.get("classification"))
    with c2:
        _score_card("Momentum", momentum.get("momentum_score"), momentum.get("classification"))
    with c3:
        _score_card("Location", location.get("location_score"), location.get("classification"))
    with c4:
        _score_card("RS", rs.get("relative_strength_score"), rs.get("classification"))
    with c5:
        _score_card("Risk", risk.get("risk_score"), risk.get("classification"))
    with c6:
        dq = qs.get("component_scores", {}).get("data_quality")
        _score_card("Qualidade", dq)

    # ── Suportes & Resistências ──
    st.markdown('<div class="v2-section">Suportes &amp; Resistências</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        supports = analysis.get("supports", []) or []
        if supports:
            st.dataframe(
                [{"Nível": s.get("label"), "Preço": f"{s.get('price', 0):.2f}" if s.get("price") else "—",
                  "Força": f"{s.get('strength', '—')}", "Dist": f"{s.get('distance_pct', 0):.1f}%"}
                 for s in supports],
                use_container_width=True, hide_index=True,
            )
        else:
            st.caption("Níveis insuficientes para suportes.")
    with c2:
        resistances = analysis.get("resistances", []) or []
        if resistances:
            st.dataframe(
                [{"Nível": r.get("label"), "Preço": f"{r.get('price', 0):.2f}" if r.get("price") else "—",
                  "Força": f"{r.get('strength', '—')}", "Dist": f"{r.get('distance_pct', 0):.1f}%"}
                 for r in resistances],
                use_container_width=True, hide_index=True,
            )
        else:
            st.caption("Níveis insuficientes para resistências.")

    # ── Plano operacional ──
    _render_operational_plan(analysis, ticker)

    # ── Leitura ──
    if formatted:
        st.markdown('<div class="v2-section">Leitura</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="v2-summary-box">{formatted.get("summary", "—")}</div>', unsafe_allow_html=True)
        if formatted.get("operational_plan"):
            st.caption(formatted["operational_plan"])

        c1, c2 = st.columns(2)
        with c1:
            st.caption("**A favor**")
            for r in (formatted.get("bullish_points", analysis.get("reasons", [])))[:5]:
                st.caption(f"✅ {r}")
        with c2:
            st.caption("**Contra**")
            for w in (formatted.get("bearish_points", analysis.get("warnings", [])))[:5]:
                st.caption(f"⚠️ {w}")

    # ── Errors / Warnings expanders ──
    errs = analysis.get("errors") or []
    warns = analysis.get("warnings") or []
    if warns:
        with st.expander("Warnings da análise"):
            for w in warns:
                st.caption(f"⚠️ {w}")
    if errs:
        with st.expander("Erros técnicos capturados"):
            for e in errs:
                st.caption(f"• {e.get('module', '?')}: {e.get('error', str(e))}")


# ═══════════════════════ TAB 1: Radar ═══════════════════════
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
                result = run_stock_radar_v2(tickers=tickers, min_score=min_score,
                                            mode_filter=mode_filter, max_tickers=max_show)
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
            display_df = clean_radar_table(candidates)
            st.subheader(f"Candidatos — {len(candidates)} ações com score ≥ {min_score}")
            try:
                st.dataframe(display_df, use_container_width=True, hide_index=True,
                             column_config={"Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d")})
            except Exception:
                st.dataframe(display_df, use_container_width=True, hide_index=True)
            ticker_sel = st.selectbox("Selecionar para análise detalhada", candidates["Ticker"].tolist())
            if st.button("🔍 Analisar Ação Selecionada"):
                _render_analysis(ticker_sel)
        else:
            st.info(f"Nenhuma ação atingiu o score mínimo ({min_score}).")
            if rejected is not None and not rejected.empty:
                st.subheader("Top rejeitados abaixo do corte")
                top_rej = rejected.head(10)
                st.dataframe(clean_radar_table(top_rej), use_container_width=True, hide_index=True)
                ticker_sel = st.selectbox("Selecionar para análise detalhada", top_rej["Ticker"].tolist())
                if st.button("🔍 Analisar mesmo assim"):
                    _render_analysis(ticker_sel)

        if rejected is not None and not rejected.empty:
            with st.expander(f"Todos os rejeitados ({len(rejected)})"):
                st.dataframe(clean_radar_table(rejected), use_container_width=True, hide_index=True)
        if errors_df is not None and not errors_df.empty:
            with st.expander(f"Erros ({len(errors_df)})"):
                st.dataframe(errors_df, use_container_width=True, hide_index=True)


# ═══════════════════════ TAB 2: Análise Individual ═══════════════════════
with tab2:
    st.subheader("Análise Individual V2")
    st.caption("Digite qualquer ticker ou escolha um ativo do arquivo para análise completa.")
    c1, c2 = st.columns([1, 1])
    with c1:
        manual_ticker = st.text_input("Digite um ticker", placeholder="Ex: AAPL, PETR4.SA, MSFT")
    with c2:
        select_ticker = st.selectbox("Ou escolha da lista", [""] + default_tickers) if default_tickers else ""
    ticker_to_analyze = manual_ticker.strip().upper() if manual_ticker.strip() else select_ticker

    if ticker_to_analyze and st.button("🔍 Analisar Ativo", use_container_width=True):
        try:
            _render_analysis(ticker_to_analyze)
        except Exception as exc:
            st.error(f"Erro ao processar análise de {ticker_to_analyze}. A aplicação continua funcionando.")
            with st.expander("Detalhes técnicos"):
                st.exception(exc)

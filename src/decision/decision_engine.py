from __future__ import annotations


def gerar_decisao_operacional(direcao: dict, volatilidade: dict, is_btc: bool) -> dict:
    regime_dir = direcao.get("regime_direcional", "transicao")
    regime_vol = volatilidade.get("regime", "🌫 Zona de transição da volatilidade")
    lado_dir = direcao.get("lado", "neutro")

    chave_vol = _mapear_regime_vol(regime_vol)
    decisao = _matriz_decisao(regime_dir, chave_vol)

    result = {
        "decisao": decisao["decisao"],
        "decisao_key": decisao["decisao_key"],
        "lado": _definir_lado(decisao["decisao_key"], lado_dir),
        "nivel": decisao["nivel"],
        "confianca": decisao["confianca"],
        "explicacao": decisao["explicacao"],
        "alertas": decisao["alertas"],
        "opcoes_btc": None,
    }

    if is_btc:
        try:
            from src.volatility.options_strategy_engine import sugerir_estrategias_btc
            result["opcoes_btc"] = sugerir_estrategias_btc(
                direcao.get("interpretacao", ""),
                regime_vol,
                volatilidade.get("score_expansao", 0),
                volatilidade.get("score_contracao", 0),
            )
        except Exception:
            pass

    return result


def _mapear_regime_vol(regime: str) -> str:
    if "comprimida" in regime.lower():
        return "compressao"
    if "expansão" in regime.lower():
        return "expansao"
    if "alta" in regime.lower() and "sustentada" in regime.lower():
        return "alta_sustentada"
    if "contração" in regime.lower():
        return "contracao"
    return "transicao"


def _definir_lado(decisao_key: str, lado_dir: str) -> str:
    if decisao_key in ("entrar_comprado", "entrar_comprado_antecipado", "entrar_comprado_risco_definido"):
        return "long"
    if decisao_key in ("entrar_vendido", "entrar_vendido_antecipado", "entrar_vendido_risco_definido"):
        return "short"
    if decisao_key in ("manter", "reduzir_ou_sair"):
        return lado_dir
    return "neutro"


def _matriz_decisao(regime_dir: str, regime_vol: str) -> dict:
    key = (regime_dir, regime_vol)
    return _DECISION_MATRIX.get(key, _DEFAULT_DECISION)


_D = lambda d, dk, n, c, e, a: {
    "decisao": d, "decisao_key": dk, "nivel": n, "confianca": c, "explicacao": e, "alertas": a,
}


# ── Decision Matrix ──
_DECISION_MATRIX: dict = {}

# alta_forte x vol
_DECISION_MATRIX[("alta_forte", "compressao")] = _D(
    "🟢 Entrada comprada antecipada favorecida", "entrar_comprado_antecipado",
    "entrada", "alta",
    "Direção positiva com volatilidade ainda comprimida. A compressão pode anteceder movimento forte.",
    ["Confirmar alinhamento em todos os timeframes", "Aguardar rompimento de resistência próxima"],
)
_DECISION_MATRIX[("alta_forte", "expansao")] = _D(
    "🟢 Entrada comprada favorecida", "entrar_comprado",
    "entrada", "alta",
    "Direção clara de alta com volatilidade em expansão. Ambiente favorável para posição comprada.",
    ["Gerenciar risco com stop abaixo do último pivô de baixa", "Evitar excesso de alavancagem"],
)
_DECISION_MATRIX[("alta_forte", "alta_sustentada")] = _D(
    "🟡 Entrada comprada apenas com risco definido", "entrar_comprado_risco_definido",
    "entrada", "media",
    "Direção positiva, mas volatilidade já elevada. Evitar exposição excessiva.",
    ["Reduzir tamanho da posição", "Usar ordens de stop mais apertadas"],
)
_DECISION_MATRIX[("alta_forte", "contracao")] = _D(
    "🟠 Manter, mas evitar nova entrada comprada", "manter",
    "manutencao", "media",
    "Direção ainda positiva, mas a contração de volatilidade pode indicar perda de energia.",
    ["Não adicionar posição", "Apertar stop se houver sinal de reversão"],
)
_DECISION_MATRIX[("alta_forte", "transicao")] = _D(
    "🟢 Entrada comprada favorecida", "entrar_comprado",
    "entrada", "media",
    "Tendência de alta definida. A volatilidade em transição não invalida a direção.",
    ["Monitorar mudança no regime de volatilidade"],
)

# alta_moderada x vol
_DECISION_MATRIX[("alta_moderada", "compressao")] = _D(
    "🟢 Entrada comprada antecipada favorecida", "entrar_comprado_antecipado",
    "entrada", "alta",
    "Tendência de alta em desenvolvimento com volatilidade comprimida.",
    ["Aguardar confirmação do timeframe diário", "Entrada em tamanho moderado"],
)
_DECISION_MATRIX[("alta_moderada", "expansao")] = _D(
    "🟢 Entrada comprada favorecida", "entrar_comprado",
    "entrada", "alta",
    "Tendência de alta se fortalecendo com volatilidade favorável.",
    ["Stop móvel conforme tendência se desenvolve"],
)
_DECISION_MATRIX[("alta_moderada", "alta_sustentada")] = _D(
    "🟡 Entrada comprada apenas com risco definido", "entrar_comprado_risco_definido",
    "entrada", "media",
    "Direção positiva, mas volatilidade elevada exige cautela na entrada.",
    ["Tamanho reduzido", "Stop bem definido abaixo de suporte"],
)
_DECISION_MATRIX[("alta_moderada", "contracao")] = _D(
    "🟠 Manter, mas evitar nova entrada comprada", "manter",
    "manutencao", "media",
    "Direção positiva com volatilidade contraindo. Aguardar antes de adicionar.",
    ["Não aumentar posição", "Stop mais próximo do preço atual"],
)

# alta_leve x vol
_DECISION_MATRIX[("alta_leve", "compressao")] = _D(
    "🟡 Entrada somente com confirmação", "entrar_com_confirmacao",
    "entrada", "media",
    "Alta ainda leve; compressão pode preceder movimento. Entrar apenas após confirmação.",
    ["Esperar candle de força no diário", "Usar tamanho menor que o usual"],
)
_DECISION_MATRIX[("alta_leve", "expansao")] = _D(
    "🟡 Entrada pequena com confirmação", "entrar_com_confirmacao",
    "entrada", "media",
    "Alta inicial com volatilidade reagindo. Tamanho reduzido até tendência se firmar.",
    ["Posição de 1/3 do tamanho normal", "Stop mais largo para evitar ruído"],
)
_DECISION_MATRIX[("alta_leve", "alta_sustentada")] = _D(
    "🟡 Entrada somente com confirmação", "entrar_com_confirmacao",
    "entrada", "baixa",
    "Alta leve com volatilidade já elevada. Relação risco/retorno desfavorável para entrada agressiva.",
    ["Aguardar pullback para entrada", "Reduzir expectativa de retorno"],
)
_DECISION_MATRIX[("alta_leve", "contracao")] = _D(
    "⚪ Ficar de fora", "ficar_de_fora",
    "ausencia", "media",
    "Alta leve com contração de volatilidade. Pouca convicção para entrada direcional.",
    ["Aguardar cenário mais claro", "Monitorar sem posição"],
)

# baixa_forte x vol
_DECISION_MATRIX[("baixa_forte", "compressao")] = _D(
    "🔴 Entrada vendida/short antecipada favorecida", "entrar_vendido_antecipado",
    "entrada", "alta",
    "Direção negativa com volatilidade ainda comprimida. Compressão pode anteceder movimento de queda.",
    ["Confirmar alinhamento baixista em todos os timeframes", "Stop acima da última resistência"],
)
_DECISION_MATRIX[("baixa_forte", "expansao")] = _D(
    "🔴 Entrada vendida/short favorecida", "entrar_vendido",
    "entrada", "alta",
    "Direção clara de baixa com volatilidade em expansão. Ambiente favorável para posição vendida.",
    ["Gerenciar risco com stop acima do último pivô de alta", "Evitar excesso de alavancagem"],
)
_DECISION_MATRIX[("baixa_forte", "alta_sustentada")] = _D(
    "🟡 Entrada short apenas com risco definido", "entrar_vendido_risco_definido",
    "entrada", "media",
    "Direção negativa, mas volatilidade já elevada. Evitar exposição excessiva.",
    ["Reduzir tamanho da posição", "Usar ordens de stop mais apertadas"],
)
_DECISION_MATRIX[("baixa_forte", "contracao")] = _D(
    "🟠 Manter short, mas evitar nova entrada vendida", "manter",
    "manutencao", "media",
    "Direção ainda negativa, mas a contração de volatilidade pode indicar perda de energia na queda.",
    ["Não adicionar posição vendida", "Apertar stop se houver sinal de reversão para cima"],
)

# baixa_moderada x vol
_DECISION_MATRIX[("baixa_moderada", "compressao")] = _D(
    "🔴 Entrada vendida/short antecipada favorecida", "entrar_vendido_antecipado",
    "entrada", "alta",
    "Tendência de baixa em desenvolvimento com volatilidade comprimida.",
    ["Aguardar confirmação do timeframe diário", "Entrada em tamanho moderado"],
)
_DECISION_MATRIX[("baixa_moderada", "expansao")] = _D(
    "🔴 Entrada vendida/short favorecida", "entrar_vendido",
    "entrada", "alta",
    "Tendência de baixa se fortalecendo com volatilidade favorável.",
    ["Stop móvel conforme tendência se desenvolve"],
)

# baixa_leve x vol
_DECISION_MATRIX[("baixa_leve", "expansao")] = _D(
    "🟡 Entrada short pequena com confirmação", "entrar_com_confirmacao",
    "entrada", "media",
    "Baixa inicial com volatilidade reagindo. Tamanho reduzido até tendência se firmar.",
    ["Posição de 1/3 do tamanho normal", "Stop mais largo para evitar ruído"],
)

# possivel_reversao x vol
_DECISION_MATRIX[("possivel_reversao_alta", "compressao")] = _D(
    "🟡 Entrada somente com confirmação", "entrar_com_confirmacao",
    "entrada", "media",
    "Possível reversão altista com volatilidade comprimida. Entrar apenas após confirmação.",
    ["Esperar candle de confirmação no diário", "Stop abaixo da mínima recente"],
)
_DECISION_MATRIX[("possivel_reversao_baixa", "compressao")] = _D(
    "🟡 Entrada somente com confirmação", "entrar_com_confirmacao",
    "entrada", "media",
    "Possível reversão baixista com volatilidade comprimida. Entrar apenas após confirmação.",
    ["Esperar candle de confirmação no diário", "Stop acima da máxima recente"],
)

# sem_tendencia x vol
_DECISION_MATRIX[("sem_tendencia_direcional", "compressao")] = _D(
    "🧨 Aguardar rompimento", "aguardar_rompimento",
    "ausencia", "media",
    "Volatilidade comprimida pode anteceder movimento, mas a direção ainda não confirmou.",
    ["Monitorar rompimento de range", "Preparar ordens de entrada para ambos os lados"],
)
_DECISION_MATRIX[("sem_tendencia_direcional", "expansao")] = _D(
    "🟡 Aguardar direção ou operar apenas com confirmação", "aguardar_rompimento",
    "ausencia", "baixa",
    "Volatilidade em expansão sem direção clara. Movimento pode ser errático.",
    ["Evitar entradas antecipadas", "Operar apenas rompimentos confirmados"],
)
_DECISION_MATRIX[("sem_tendencia_direcional", "contracao")] = _D(
    "⚪ Ficar de fora", "ficar_de_fora",
    "ausencia", "alta",
    "Sem direção definida e volatilidade contraindo. Cenário de baixa oportunidade.",
    ["Aguardar cenário mais claro", "Preservar capital"],
)
_DECISION_MATRIX[("sem_tendencia_direcional", "alta_sustentada")] = _D(
    "⚪ Ficar de fora para direcional", "ficar_de_fora",
    "ausencia", "alta",
    "Volatilidade elevada sem direção. Alto risco para posições direcionais.",
    ["Evitar entradas direcionais", "Se operar, apenas com risco muito definido"],
)

# transicao x vol
_DECISION_MATRIX[("transicao", "compressao")] = _D(
    "🧨 Aguardar rompimento", "aguardar_rompimento",
    "ausencia", "media",
    "Direção em transição com volatilidade comprimida. Aguardar definição.",
    ["Monitorar sem posição", "Identificar nível-chave de rompimento"],
)
_DECISION_MATRIX[("transicao", "expansao")] = _D(
    "🟡 Entrada somente após confirmação direcional", "entrar_com_confirmacao",
    "entrada", "baixa",
    "Direção indefinida com volatilidade em expansão. Alto risco sem confirmação.",
    ["Esperar candle direcional claro", "Usar tamanho reduzido"],
)
_DECISION_MATRIX[("transicao", "transicao")] = _D(
    "⚪ Ficar de fora", "ficar_de_fora",
    "ausencia", "alta",
    "Tanto direção quanto volatilidade em transição. Cenário sem leitura limpa.",
    ["Aguardar", "Não abrir novas posições"],
)

_DEFAULT_DECISION = _D(
    "🟡 Aguardar confirmação", "entrar_com_confirmacao",
    "entrada", "baixa",
    "Cenário sem mapeamento direto. Agir com cautela e aguardar definição do mercado.",
    ["Aguardar leitura mais clara", "Reduzir tamanho se já posicionado"],
)

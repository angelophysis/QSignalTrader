from __future__ import annotations


def classificar_direcao(interpretacao: str) -> str:
    if "📈 Tendência de alta forte" in interpretacao or "📈 Tendência de alta se consolidando" in interpretacao:
        return "alta_forte"
    if "📈" in interpretacao and ("médio" in interpretacao or "longo" in interpretacao or "curto prazo" in interpretacao):
        return "alta_moderada"
    if "📉 Alta leve" in interpretacao:
        return "alta_leve"
    if "🔄 Possível reversão" in interpretacao or "🔄 Tendência macro" in interpretacao:
        return "reversao_possivel"
    if "❌ Nenhum timeframe" in interpretacao:
        return "sem_tendencia"
    return "transicao"


def _st(nome, tambem_chamado, tipo, quando_estudar, por_que, risco):
    return {
        "nome": nome,
        "tambem_chamado": tambem_chamado,
        "tipo": tipo,
        "quando_estudar": quando_estudar,
        "por_que_faz_sentido": por_que,
        "risco_principal": risco,
    }


# ─── Fallback por regime de volatilidade (quando direção não tem mapeamento específico) ───
_VOL_FALLBACK = {
    "🧨 Volatilidade comprimida com risco de expansão": {
        "classificacao": "Volatilidade comprimida — direção não claramente classificada",
        "estrategias_prioritarias": [
            _st("Long Straddle", None, "Não direcional comprado em volatilidade",
                "Compressão de volatilidade sem direção confirmada.",
                "Captura movimento independente da direção; IV baixa mantém custo reduzido.",
                "Custo de dois prêmios; deterioração por theta se o movimento demorar."),
            _st("Long Strangle", None, "Não direcional comprado em volatilidade com menor custo",
                "Alternativa de custo reduzido ao straddle.",
                "Menor desembolso; breakeven mais distante mas captura grandes movimentos.",
                "Requer movimento ainda mais forte que o straddle."),
        ],
        "estrategias_secundarias": [],
        "estrategias_evitar": ["Iron Condor", "Venda de volatilidade antes da expansão"],
    },
    "🚀 Volatilidade em expansão": {
        "classificacao": "Volatilidade em expansão — direção não claramente classificada",
        "estrategias_prioritarias": [
            _st("Long Strangle", None, "Não direcional comprado em volatilidade",
                "Volatilidade expandindo com direção incerta — melhor não apostar direção.",
                "Captura o movimento de volatilidade sem precisar acertar direção.",
                "Custo de dois prêmios; requer movimento forte para lucro."),
            _st("Call/Put Debit Spread pequeno", None, "Direcional com risco definido e tamanho reduzido",
                "Se houver leve preferência direcional.",
                "Risco definido com exposição controlada.",
                "Lucro máximo limitado ao spread."),
        ],
        "estrategias_secundarias": [],
        "estrategias_evitar": ["Short Straddle", "Short Strangle", "Venda descoberta de volatilidade"],
    },
    "🌋 Volatilidade alta e ainda sustentada": {
        "classificacao": "Volatilidade alta sustentada — direção não claramente classificada",
        "estrategias_prioritarias": [
            _st("Iron Condor conservador", None, "Não direcional de venda de volatilidade",
                "Volatilidade alta oferece prêmios atrativos para estruturas neutras.",
                "Theta trabalha a favor; ampla faixa de lucro com strikes bem afastados.",
                "Risco definido pelas asas; gaps fortes podem gerar perdas."),
            _st("Credit Spreads OTM", None, "Venda de prêmio com risco definido",
                "Aproveitar prêmios elevados com strikes fora do dinheiro.",
                "Alta probabilidade de sucesso com gestão de risco adequada.",
                "Lucro máximo limitado ao crédito recebido."),
        ],
        "estrategias_secundarias": [],
        "estrategias_evitar": ["Compra seca de opções muito caras", "Long Straddle com IV alta"],
    },
    "🧊 Volatilidade elevada com probabilidade de contração": {
        "classificacao": "Volatilidade elevada em contração — direção não claramente classificada",
        "estrategias_prioritarias": [
            _st("Iron Condor", None, "Não direcional de venda de volatilidade",
                "IV elevada em queda: cenário ideal para venda de prêmio neutro.",
                "Theta e Vega trabalham a favor simultaneamente.",
                "Risco definido pelas asas."),
            _st("Credit Spreads OTM", None, "Venda de prêmio com risco definido",
                "Colocar strikes bem fora do dinheiro em ambiente de volatilidade cara.",
                "Alta probabilidade de sucesso com IV caindo.",
                "Lucro máximo limitado ao crédito."),
        ],
        "estrategias_secundarias": [],
        "estrategias_evitar": ["Long Straddle", "Long Strangle", "Compra seca de opções"],
    },
    "🌫 Zona de transição da volatilidade": {
        "classificacao": "Volatilidade indefinida — direção não claramente classificada",
        "estrategias_prioritarias": [],
        "estrategias_secundarias": [
            _st("Operações de tamanho reduzido", None, "Qualquer estrutura com risco muito limitado",
                "Indefinição total: melhor manter exposição mínima.",
                "Preservar capital enquanto aguarda leitura mais clara.",
                "Baixa probabilidade de cenário favorável com leitura indefinida."),
        ],
        "estrategias_evitar": ["Estratégias alavancadas", "Venda descoberta", "Compras grandes de prêmio"],
    },
}


STRATEGY_MATRIX: dict = {}  # populated below


def _register(dir_key, vol_key, matriz):
    STRATEGY_MATRIX[(dir_key, vol_key)] = matriz


# ─── 5.1 Alta forte + volatilidade em expansão ───
_register("alta_forte", "🚀 Volatilidade em expansão", {
    "classificacao": "Viés altista com volatilidade em expansão",
    "estrategias_prioritarias": [
        _st("Bull Call Spread", "Call Debit Spread",
            "Direcional altista com risco definido",
            "Viés de alta e expectativa de movimento, com desejo de limitar custo e risco.",
            "A direção favorece alta e a volatilidade em expansão pode beneficiar estruturas compradas em prêmio.",
            "Perda limitada ao débito pago; risco de queda de volatilidade se a entrada ocorrer com IV já muito alta."),
        _st("Long Call", "Compra de Call",
            "Direcional altista com exposição longa a Vega",
            "Convicção forte na direção e expectativa de continuidade do movimento.",
            "Captura direção e pode se beneficiar de expansão adicional da volatilidade implícita.",
            "Custo total do prêmio; sensível a queda de IV e passagem do tempo."),
        _st("Call Ratio Spread", None,
            "Direcional altista com risco assimétrico",
            "Quando o trader compreende bem os riscos de razão e deseja montar estrutura com custo reduzido.",
            "Reduz ou elimina custo de entrada mantendo viés direcional positivo.",
            "Risco na ponta vendida se o movimento for muito forte; exige gestão ativa."),
    ],
    "estrategias_secundarias": [
        _st("Long Straddle", None,
            "Não direcional comprado em volatilidade",
            "Expectativa de movimento forte sem certeza da direção exata.",
            "Captura grandes movimentos em qualquer direção durante expansão de volatilidade.",
            "Custo elevado de dois prêmios; necessita movimento significativo para lucro."),
        _st("Long Strangle", None,
            "Não direcional comprado em volatilidade com menor custo",
            "Similar ao straddle mas com menor desembolso inicial.",
            "Ponto de equilíbrio mais distante reduz custo, mas ainda captura expansão.",
            "Requer movimento ainda maior que o straddle para atingir lucro."),
    ],
    "estrategias_evitar": [
        "Iron Condor",
        "Short Strangle descoberto",
        "Venda agressiva de volatilidade",
    ],
})

# ─── 5.2 Alta forte + volatilidade comprimida ───
_register("alta_forte", "🧨 Volatilidade comprimida com risco de expansão", {
    "classificacao": "Viés altista com volatilidade comprimida",
    "estrategias_prioritarias": [
        _st("Bull Call Spread", "Call Debit Spread",
            "Direcional altista com risco definido",
            "Viés de alta e volatilidade ainda baixa, com desejo de participar sem custo excessivo.",
            "Estrutura de débito limitada; a IV baixa favorece a compra do spread antes da expansão.",
            "Perda limitada ao débito; se a IV já começar a subir, o spread pode ser ajustado."),
        _st("Long Call", "Compra de Call",
            "Direcional altista puro",
            "Alta convicção na direção e expectativa de que a volatilidade irá expandir.",
            "IV comprimida significa prêmios relativamente baratos para compra.",
            "Custo total do prêmio se o movimento não ocorrer ou demorar."),
        _st("Long Strangle com viés altista", None,
            "Compra de volatilidade com skew direcional",
            "Quando se espera movimento forte mas o timing exato é incerto.",
            "Posicionamento antes da expansão com prêmios mais baixos.",
            "Duplo custo de prêmio; necessita movimento significativo."),
    ],
    "estrategias_secundarias": [
        _st("Long Straddle", None,
            "Não direcional comprado em volatilidade",
            "Expectativa de explosão de volatilidade com direção ainda não totalmente confirmada.",
            "IV baixa reduz custo de montagem do straddle.",
            "Custo elevado; deterioração por theta se o movimento demorar."),
    ],
    "estrategias_evitar": [
        "Iron Condor",
        "Credit Spread muito próximo do preço",
        "Venda de volatilidade antes da expansão",
    ],
})

# ─── 5.3 Alta forte + volatilidade elevada com contração ───
_register("alta_forte", "🧊 Volatilidade elevada com probabilidade de contração", {
    "classificacao": "Viés altista com volatilidade elevada em possível contração",
    "estrategias_prioritarias": [
        _st("Put Credit Spread", "Bull Put Spread",
            "Venda de volatilidade com viés altista",
            "Direção positiva e volatilidade cara favorecendo venda de prêmio.",
            "Recebe crédito; a queda de IV e a direção favorável trabalham a favor.",
            "Perda limitada ao spread menos crédito; risco de reversão forte para baixo."),
        _st("Call Debit Spread", "Bull Call Spread",
            "Direcional altista com exposição reduzida a Vega",
            "Manter viés direcional positivo com menor exposição à volatilidade implícita.",
            "Risco definido; o spread mitiga parcialmente o efeito da queda de IV na call comprada.",
            "Lucro máximo limitado; ainda sofre algum impacto de Vega na perna comprada."),
        _st("Diagonal Call Spread", None,
            "Direcional com componente de tempo",
            "Quando há viés de alta e a estrutura a termo da volatilidade favorece o spread.",
            "Combina theta positivo na perna vendida curta com exposição direcional na perna longa.",
            "Complexidade de gestão; sensível a mudanças na estrutura a termo."),
    ],
    "estrategias_secundarias": [
        _st("Calendar Call Spread", None,
            "Estratégia de tempo com viés direcional",
            "Aproveitar possível contango ou backwardation na estrutura a termo.",
            "Vende volatilidade de curto prazo enquanto mantém exposição de longo prazo.",
            "Lucro limitado; requer gestão ativa e compreensão da estrutura a termo."),
    ],
    "estrategias_evitar": [
        "Long Call seco",
        "Long Straddle",
        "Long Strangle",
    ],
})

# ─── 5.4 Alta forte + volatilidade alta e sustentada ───
_register("alta_forte", "🌋 Volatilidade alta e ainda sustentada", {
    "classificacao": "Viés altista com volatilidade alta e sustentada",
    "estrategias_prioritarias": [
        _st("Call Debit Spread", "Bull Call Spread",
            "Direcional altista com risco definido",
            "Volatilidade alta: estruturas de débito com spread reduzem exposição ao prêmio caro.",
            "Limita o custo da entrada mantendo exposição direcional positiva.",
            "Lucro máximo limitado ao spread."),
        _st("Put Credit Spread conservador", "Bull Put Spread OTM",
            "Venda de volatilidade com risco definido e viés altista",
            "Volatilidade ainda elevada oferece prêmios atrativos para venda.",
            "Theta e possível contração futura de IV trabalham a favor.",
            "Risco de gap para baixo além do strike vendido."),
        _st("Diagonal Call Spread", None,
            "Estratégia de tempo com viés altista",
            "Aproveitar a alta volatilidade vendendo opções curtas caras e mantendo calls longas.",
            "Combina theta positivo com exposição direcional controlada.",
            "Complexidade de ajustes; requer compreensão de Vega e Theta."),
    ],
    "estrategias_secundarias": [
        _st("Long Call (somente com forte convicção)", "Compra de Call seletiva",
            "Direcional puro com exposição a Vega",
            "Apenas se IV/RV ainda estiver em nível aceitável e houver catalisador claro.",
            "Captura total do movimento direcional.",
            "Prêmio caro; alta sensibilidade a queda de volatilidade."),
    ],
    "estrategias_evitar": [
        "Short Strangle descoberto",
        "Iron Condor muito apertado",
        "Compra seca de opções muito caras sem catalisador",
    ],
})

# ─── Alta moderada (similar a alta forte, com menor agressividade) ───
_ALTA_MODERADA_FALLBACK = {
    "classificacao": "Viés altista moderado",
    "estrategias_prioritarias": [
        _st("Bull Call Spread", "Call Debit Spread",
            "Direcional altista com risco definido",
            "Viés de alta com tendência se formando; usar tamanho moderado.",
            "Risco definido e custo controlado; boa relação risco-retorno para tendências em desenvolvimento.",
            "Lucro máximo limitado ao spread; perda limitada ao débito pago."),
        _st("Put Credit Spread OTM", "Bull Put Spread",
            "Venda de volatilidade com viés altista",
            "Tendência positiva com volatilidade permitindo venda de prêmio.",
            "Theta trabalha a favor; boa probabilidade de sucesso com gestão adequada.",
            "Risco de gap para baixo além do strike vendido."),
    ],
    "estrategias_secundarias": [],
    "estrategias_evitar": ["Iron Condor", "Short Strangle descoberto"],
}

for _vol_key in ["🧨 Volatilidade comprimida com risco de expansão", "🚀 Volatilidade em expansão",
                   "🌋 Volatilidade alta e ainda sustentada", "🧊 Volatilidade elevada com probabilidade de contração",
                   "🌫 Zona de transição da volatilidade"]:
    _register("alta_moderada", _vol_key, _ALTA_MODERADA_FALLBACK)

# ─── 5.5 Alta leve + volatilidade em expansão ───
_register("alta_leve", "🚀 Volatilidade em expansão", {
    "classificacao": "Alta inicial com volatilidade em expansão",
    "estrategias_prioritarias": [
        _st("Call Debit Spread pequeno", "Bull Call Spread conservador",
            "Direcional altista com tamanho reduzido",
            "A direção ainda está no início; tamanho menor reduz risco enquanto a tendência se confirma.",
            "Risco definido e limitado; permite participar sem exposição excessiva.",
            "Lucro máximo limitado."),
        _st("Long Strangle pequeno", None,
            "Compra de volatilidade com tamanho reduzido",
            "Direção ainda não está madura, mas volatilidade está reagindo.",
            "Não direcional com custo controlado; captura expansão sem precisar acertar direção.",
            "Requer movimento significativo para compensar dois prêmios."),
    ],
    "estrategias_secundarias": [],
    "estrategias_evitar": [
        "Posições grandes em Long Call",
        "Venda de volatilidade antes da tendência se firmar",
    ],
})

# ─── 5.6 Possível reversão + volatilidade comprimida ───
_register("reversao_possivel", "🧨 Volatilidade comprimida com risco de expansão", {
    "classificacao": "Possível reversão altista com volatilidade comprimida",
    "estrategias_prioritarias": [
        _st("Long Straddle", None,
            "Não direcional comprado em volatilidade",
            "Direção não totalmente confirmada, mas compressão de volatilidade pode anteceder movimento forte.",
            "Captura o movimento independente da direção; IV baixa mantém custo de entrada reduzido.",
            "Custo de dois prêmios; deterioração por theta se o movimento demorar."),
        _st("Long Strangle", None,
            "Não direcional comprado em volatilidade com menor custo",
            "Alternativa de menor custo ao straddle quando a direção ainda não está clara.",
            "Menor desembolso inicial com exposição similar à expansão de volatilidade.",
            "Breakeven mais distante; requer movimento mais forte para lucro."),
        _st("Call Debit Spread condicionado", "Bull Call Spread após gatilho",
            "Direcional altista condicionado à confirmação",
            "Usar apenas se houver confirmação técnica da reversão.",
            "Entrada após confirmação reduz risco de falsa reversão.",
            "Pode perder parte do movimento inicial esperando confirmação."),
    ],
    "estrategias_secundarias": [],
    "estrategias_evitar": [
        "Put Credit Spread agressivo",
        "Venda de volatilidade antes da confirmação da direção",
    ],
})

# ─── 5.7 Sem tendência + volatilidade comprimida ───
_register("sem_tendencia", "🧨 Volatilidade comprimida com risco de expansão", {
    "classificacao": "Sem tendência clara com volatilidade comprimida",
    "estrategias_prioritarias": [
        _st("Long Straddle", None,
            "Não direcional comprado em volatilidade",
            "Compressão de volatilidade sem direção definida — o mercado pode explodir para qualquer lado.",
            "Posicionamento agnóstico à direção antes de possível expansão.",
            "Custo elevado de dois prêmios; necessita movimento forte."),
        _st("Long Strangle", None,
            "Não direcional comprado em volatilidade com menor custo",
            "Alternativa de custo reduzido ao straddle.",
            "Menor desembolso; breakeven mais distante mas ainda captura grandes movimentos.",
            "Requer movimento ainda mais forte que o straddle."),
        _st("Calendar Spread", None,
            "Estratégia de tempo e volatilidade",
            "Se a IV de curto prazo estiver relativamente barata vs longo prazo.",
            "Vende volatilidade cara de curto prazo e compra barata de longo prazo.",
            "Lucro limitado; requer gestão ativa e compreensão da estrutura a termo."),
    ],
    "estrategias_secundarias": [],
    "estrategias_evitar": [
        "Call direcional ou Put direcional sem confirmação",
        "Put Credit Spread direcional",
        "Iron Condor — risco de expansão repentina",
    ],
})

# ─── 5.8 Sem tendência + volatilidade elevada com contração ───
_register("sem_tendencia", "🧊 Volatilidade elevada com probabilidade de contração", {
    "classificacao": "Sem tendência clara com volatilidade elevada em possível contração",
    "estrategias_prioritarias": [
        _st("Iron Condor", None,
            "Não direcional de venda de volatilidade com risco definido",
            "Ausência de direção e IV elevada em queda — cenário ideal para venda de prêmio.",
            "Theta trabalha a favor; contração de IV reduz valor das opções vendidas.",
            "Risco definido pelo spread das asas; gaps fortes podem gerar perdas."),
        _st("Short Strangle com proteção", "Strangle com asas de proteção",
            "Venda de volatilidade com hedge",
            "Similar ao Iron Condor mas com estrutura diferente de proteção.",
            "Captura prêmio elevado com proteção contra movimentos extremos.",
            "Margem e risco de gap; exige gestão ativa de risco."),
        _st("Credit Spreads OTM", "Put Credit Spread e Call Credit Spread",
            "Venda de prêmio com risco definido",
            "Colocar strikes fora do dinheiro em ambiente de volatilidade cara.",
            "Alta probabilidade de sucesso com IV elevada e em queda.",
            "Lucro máximo limitado ao crédito recebido."),
    ],
    "estrategias_secundarias": [
        _st("Iron Butterfly", None,
            "Não direcional de curto prazo com risco definido",
            "Quando se espera contração rápida e o ativo ficar próximo do preço atual.",
            "Lucro máximo se o ativo ficar exatamente no strike central.",
            "Faixa de lucro estreita; sensível a pequenos movimentos."),
    ],
    "estrategias_evitar": [
        "Long Straddle",
        "Long Strangle",
        "Compra seca de opções",
    ],
})

# ─── 5.9 Transição + transição ───
_register("transicao", "🌫 Zona de transição da volatilidade", {
    "classificacao": "Direção e volatilidade em zona de transição",
    "estrategias_prioritarias": [],
    "estrategias_secundarias": [
        _st("Operações de tamanho reduzido", None,
            "Qualquer estrutura com risco muito limitado",
            "Indefinição total: melhor manter exposição mínima.",
            "Preservar capital enquanto aguarda leitura mais clara do mercado.",
            "Risco controlado, mas baixa probabilidade de cenário favorável."),
        _st("Calendar Spread (se houver assimetria)", None,
            "Estratégia de tempo condicional",
            "Apenas se houver diferença clara na estrutura a termo da volatilidade.",
            "Pequena vantagem de carry sem aposta direcional forte.",
            "Lucro limitado; requer confirmação da estrutura a termo."),
    ],
    "estrategias_evitar": [
        "Estratégias alavancadas",
        "Venda descoberta de opções",
        "Compras grandes de prêmio sem catalisador",
    ],
})


def sugerir_estrategias_btc(interpretacao: str, regime_vol: str, score_exp: int = 0, score_cont: int = 0) -> dict:
    dir_key = classificar_direcao(interpretacao)
    matriz = STRATEGY_MATRIX.get((dir_key, regime_vol))

    if matriz is None:
        matriz = _VOL_FALLBACK.get(regime_vol, {
            "classificacao": "Cenário não mapeado detalhadamente",
            "estrategias_prioritarias": [],
            "estrategias_secundarias": [
                _st("Estruturas de risco definido", None, "Abordagem conservadora",
                    "Cenário sem mapeamento específico — prudência recomendada.",
                    "Preserva flexibilidade para ajustar quando o cenário ficar mais claro.",
                    "Pequena exposição significa pequeno retorno potencial."),
            ],
            "estrategias_evitar": ["Estratégias agressivas sem leitura clara"],
        })

    return {
        "classificacao": matriz["classificacao"],
        "estrategias_prioritarias": matriz.get("estrategias_prioritarias", []),
        "estrategias_secundarias": matriz.get("estrategias_secundarias", []),
        "estrategias_evitar": matriz.get("estrategias_evitar", []),
        "observacao": "Análise educativa, não recomendação financeira.",
    }

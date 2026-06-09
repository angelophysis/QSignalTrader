let currentSymbol = '';
let currentTipo = '';

const FETCH_TIMEOUT = 120000;
const FETCH_TIMEOUT_BTC = 300000;

document.getElementById('searchBtn').addEventListener('click', () => {
    const symbol = document.getElementById('symbolInput').value.trim();
    if (symbol) analisar(symbol);
});

document.getElementById('symbolInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        const symbol = document.getElementById('symbolInput').value.trim();
        if (symbol) analisar(symbol);
    }
});

document.querySelectorAll('.quick-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const symbol = btn.dataset.symbol;
        document.getElementById('symbolInput').value = symbol;
        analisar(symbol);
    });
});

document.getElementById('refreshHistory').addEventListener('click', carregarHistorico);

document.getElementById('btnRadarCripto').addEventListener('click', () => executarRadar('cripto', false));
document.getElementById('btnRadarAcoes').addEventListener('click', () => executarRadar('acoes', false));
document.getElementById('btnRadarForce').addEventListener('click', () => {
    const lastTipo = document.getElementById('radarTitle').textContent.includes('Cripto') ? 'cripto' : 'acoes';
    executarRadar(lastTipo, true);
});

function showLoading(msg) {
    const el = document.getElementById('loading');
    el.querySelector('span').textContent = msg || 'Analisando...';
    el.classList.remove('hidden');
    document.getElementById('error').classList.add('hidden');
    document.getElementById('results').classList.add('hidden');
}

function hideLoading() {
    document.getElementById('loading').classList.add('hidden');
}

function showError(msg) {
    const el = document.getElementById('error');
    el.textContent = msg;
    el.classList.remove('hidden');
    hideLoading();
}

function fetchWithTimeout(url, options = {}, timeoutMs = FETCH_TIMEOUT) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    return fetch(url, { ...options, signal: controller.signal }).finally(() => clearTimeout(timeout));
}

async function analisar(symbol) {
    showLoading('Buscando dados de mercado...');
    currentSymbol = symbol;

    const isBtc = symbol.toUpperCase().replace(/[/\s-]/g, '') === 'BTCUSDT' || symbol.toUpperCase().trim() === 'BTC';
    const timeout = isBtc ? FETCH_TIMEOUT_BTC : FETCH_TIMEOUT;

    try {
        const resp = await fetchWithTimeout(`/api/sinal?symbol=${encodeURIComponent(symbol)}`, {}, timeout);
        const data = await resp.json();

        if (!resp.ok || data.ok === false) {
            throw new Error(data.error || `Erro ${resp.status}`);
        }

        renderAnalise(data);
        if (data.market_summary) {
            renderMarketSummary(data);
        } else {
            document.getElementById('marketSummaryPanel').classList.add('hidden');
        }
        if (data.volatilidade) {
            renderVolatilidade(data);
        } else {
            document.getElementById('btcVolPanel').classList.add('hidden');
        }
        if (data.decisao) {
            renderDecisao(data);
        } else {
            document.getElementById('decisaoCard').classList.add('hidden');
        }
        if (data.rsi_entrada) {
            renderRsiEntry(data);
        } else {
            document.getElementById('rsiEntryPanel').classList.add('hidden');
        }
        if (data.decisao && data.decisao.opcoes_btc) {
            renderOptionsStrategiesFromDecision(data);
        } else {
            document.getElementById('btcOptionsStrategiesPanel').classList.add('hidden');
        }
        hideLoading();
        document.getElementById('results').classList.remove('hidden');
    } catch (err) {
        if (err.name === 'AbortError') {
            showError(`Timeout: a análise de ${symbol} excedeu ${timeout / 1000}s. O mercado pode estar instável.`);
        } else {
            showError(`Erro ao analisar ${symbol}: ${err.message}`);
        }
    }
}

function renderMarketSummary(data) {
    const ms = data.market_summary;
    if (!ms) return;
    const panel = document.getElementById('marketSummaryPanel');
    panel.classList.remove('hidden');

    const fmt = (v, dec) => {
        const n = Number(v);
        return Number.isFinite(n) ? new Intl.NumberFormat('pt-BR', { minimumFractionDigits: dec, maximumFractionDigits: dec }).format(n) : '—';
    };

    document.getElementById('mktPreco').textContent = fmt(ms.preco_atual, 2);

    const varEl = document.getElementById('mktVar');
    const v = Number(ms.variacao_24h_percent);
    varEl.classList.remove('mkt-positive', 'mkt-negative', 'mkt-neutral');
    if (Number.isFinite(v)) {
        varEl.textContent = `${v > 0 ? '+' : ''}${fmt(Math.abs(v), 2)}%`;
        varEl.classList.add(v > 0 ? 'mkt-positive' : v < 0 ? 'mkt-negative' : 'mkt-neutral');
    } else {
        varEl.textContent = '—';
        varEl.classList.add('mkt-neutral');
    }

    document.getElementById('mktMin').textContent = fmt(ms.min_24h, 2);
    document.getElementById('mktMax').textContent = fmt(ms.max_24h, 2);
    document.getElementById('mktPeriodo').textContent = `${ms.periodo || ''} · Fonte: ${ms.fonte || ''}`;
}

function renderAnalise(data) {
    const dir = data.direcao || data;
    currentTipo = data.tipo || dir.tipo;

    // Summary card
    document.getElementById('summarySymbol').textContent = data.symbol;
    const tipoBadge = document.getElementById('summaryTipo');
    tipoBadge.textContent = currentTipo;
    tipoBadge.className = `badge ${currentTipo}`;
    document.getElementById('summaryInterpretacao').textContent = dir.interpretacao || '--';
    document.getElementById('summaryTimestamp').textContent = `Última análise: ${data.timestamp || '--'}`;

    // Timeframe table
    const tfBody = document.getElementById('tfBody');
    tfBody.innerHTML = '';

    const timeframes = dir.timeframes || {};
    const tfOrder = currentTipo === 'cripto'
        ? ['15m', '1h', '4h', '1D', '1W']
        : ['1d', '5d', '1wk'];

    for (const tf of tfOrder) {
        const s = timeframes[tf];
        if (!s) continue;

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${tf}</strong></td>
            <td>${s.alinhamento_emas ? '✅' : '❌'}</td>
            <td>${s.rsi !== null ? s.rsi : '—'}</td>
            <td>${s.rsi_forte ? '✅' : s.rsi_fraco ? '🔻' : '❌'}</td>
            <td>${s.atr !== null ? s.atr : '—'}</td>
            <td class="${s.tendencia_alta ? 'status-alta' : s.tendencia_baixa ? 'status-baixa-red' : 'status-baixa'}">
                ${s.tendencia_alta ? '✅ Alta' : s.tendencia_baixa ? '🔻 Baixa' : '❌'}
            </td>
        `;
        tfBody.appendChild(tr);
    }

    carregarHistorico();
}

function renderVolatilidade(data) {
    const vol = data.volatilidade_v2 || data.volatilidade;
    const panel = document.getElementById('btcVolPanel');
    panel.classList.remove('hidden');

    const isBtc = vol.is_btc;
    document.getElementById('volTitle').textContent = isBtc ? '🧪 Volatilidade BTC' : '🧪 Volatilidade';

    if (data.volatilidade_v2) {
        renderVolatilidadeV2(data);
        return;
    }

    // Fallback v1
    document.getElementById('volRegime').textContent = vol.regime || '--';
    document.getElementById('volMensagem').textContent = '';
    document.getElementById('volComentario').textContent = vol.leitura || '';
    document.getElementById('volTfBody').innerHTML = '';
    document.getElementById('volImplicita').innerHTML = '';

    const estratDiv = document.getElementById('volEstrategias');
    estratDiv.innerHTML = '';
    if (isBtc && vol.possiveis_estrategias && vol.possiveis_estrategias.length > 0) {
        estratDiv.innerHTML = '<span class="label" style="margin-bottom:0.5rem;display:block;">Possíveis estruturas para estudo:</span>';
        const ul = document.createElement('ul');
        ul.className = 'vol-estrategias-list';
        for (const e of vol.possiveis_estrategias) {
            const li = document.createElement('li');
            li.textContent = e;
            ul.appendChild(li);
        }
        estratDiv.appendChild(ul);
    }
}

function renderVolatilidadeV2(data) {
    const vol = data.volatilidade_v2;
    const isBtc = vol.is_btc;

    document.getElementById('volRegime').textContent =
        `N: ${vol.score_nivel ?? '--'} / M: ${vol.score_movimento ?? '--'}`;

    document.getElementById('volMensagem').textContent = vol.mensagem || '';
    document.getElementById('volComentario').textContent = vol.comentario_operacional || '';

    // Per-TF table
    const tfs = vol.timeframes || [];
    const tbody = document.getElementById('volTfBody');
    tbody.innerHTML = '';
    for (const tf of tfs) {
        const nivelClass =
            tf.nivel === 'alta' ? 'status-baixa-red' :
            tf.nivel === 'baixa' ? 'decisao-aguardar' :
            tf.nivel === 'normal' ? 'status-alta' : 'status-none';

        const movClass =
            tf.movimento === 'expandindo' ? 'status-baixa-red' :
            tf.movimento === 'comprimindo' ? 'decisao-confirmacao' : 'status-none';

        const pesoLabel = tf.peso >= 4 ? '⭐ ' + tf.papel : tf.papel;

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${tf.timeframe}</strong></td>
            <td>${tf.atr_percent !== null ? tf.atr_percent.toFixed(2) + '%' : '—'}</td>
            <td>${tf.atr_percentil !== null ? tf.atr_percentil.toFixed(0) : '—'}</td>
            <td class="${nivelClass}">${tf.nivel || '—'}</td>
            <td class="${movClass}">${tf.movimento || '—'}</td>
            <td style="font-size:0.75rem;color:var(--text-muted);">${pesoLabel}</td>
        `;
        tbody.appendChild(tr);
    }

    // BTC implied vol
    const impDiv = document.getElementById('volImplicita');
    const imp = vol.implicita_btc || {};
    if (isBtc && imp.disponivel) {
        impDiv.innerHTML = `<strong>Volatilidade Implícita BTC</strong>&nbsp;&nbsp;` +
            `DVOL: ${imp.dvol ?? '—'} | IV Rank: ${imp.iv_rank ?? '—'} | ` +
            `IV %ile: ${imp.iv_percentile ?? '—'} | IV/RV: ${imp.iv_rv_ratio ?? '—'}` +
            (imp.leitura ? `<br><span style="font-size:0.8rem;color:var(--text-muted);">${imp.leitura}</span>` : '');
    } else {
        impDiv.innerHTML = '';
    }

    // Strategies (BTC only)
    const estratDiv = document.getElementById('volEstrategias');
    estratDiv.innerHTML = '';
    if (isBtc && vol.possiveis_estrategias && vol.possiveis_estrategias.length > 0) {
        estratDiv.innerHTML = '<span class="label" style="margin-bottom:0.5rem;display:block;">Possíveis estruturas para estudo:</span>';
        const ul = document.createElement('ul');
        ul.className = 'vol-estrategias-list';
        for (const e of vol.possiveis_estrategias) {
            const li = document.createElement('li');
            li.textContent = e;
            ul.appendChild(li);
        }
        estratDiv.appendChild(ul);
    }
}

function renderDecisao(data) {
    const dec = data.decisao;
    const panel = document.getElementById('decisaoCard');
    panel.classList.remove('hidden');

    document.getElementById('decisaoTexto').textContent = dec.decisao || '--';
    document.getElementById('decisaoTexto').className = 'interpretacao ' + getDecisaoColorClass(dec.decisao_key);
    document.getElementById('decisaoConfianca').textContent = (dec.lado || '--').toUpperCase();
    document.getElementById('decisaoConfianca').className = 'badge ' + (dec.lado === 'long' ? 'cripto' : dec.lado === 'short' ? 'acao' : 'vol-regime');
    document.getElementById('decisaoExplicacao').textContent = dec.explicacao || '';

    const alertasDiv = document.getElementById('decisaoAlertas');
    alertasDiv.innerHTML = '';
    if (dec.alertas && dec.alertas.length > 0) {
        const ul = document.createElement('ul');
        ul.className = 'vol-estrategias-list';
        for (const a of dec.alertas) {
            const li = document.createElement('li');
            li.textContent = a;
            ul.appendChild(li);
        }
        alertasDiv.appendChild(ul);
    }
}

function getDecisaoColorClass(key) {
    if (!key) return '';
    if (key.startsWith('entrar_comprado')) return 'decisao-long';
    if (key.startsWith('entrar_vendido')) return 'decisao-short';
    if (key.includes('confirmacao')) return 'decisao-confirmacao';
    if (key.includes('rompimento')) return 'decisao-aguardar';
    if (key === 'ficar_de_fora') return 'decisao-fora';
    if (key === 'manter') return 'decisao-manter';
    return '';
}

function renderOptionsStrategiesFromDecision(data) {
    const opts = data.decisao.opcoes_btc;
    const panel = document.getElementById('btcOptionsStrategiesPanel');
    panel.classList.remove('hidden');

    document.getElementById('optionsClassificacao').textContent = opts.classificacao || '';

    renderStrategyList(document.getElementById('optionsPrioritarias'), 'Estratégias prioritárias', opts.estrategias_prioritarias);
    renderStrategyList(document.getElementById('optionsSecundarias'), 'Estratégias secundárias', opts.estrategias_secundarias);

    const evitarDiv = document.getElementById('optionsEvitar');
    if (opts.estrategias_evitar && opts.estrategias_evitar.length > 0) {
        const items = opts.estrategias_evitar.map(e => typeof e === 'string' ? { nome: e, tipo: '', por_que_faz_sentido: '', risco_principal: '' } : e);
        renderStrategyList(evitarDiv, 'Evitar ou usar com cuidado', items);
    } else {
        evitarDiv.innerHTML = '';
    }

    document.getElementById('optionsDisclaimer').textContent = opts.observacao || '';
}

function renderRsiEntry(data) {
    const rsi = data.rsi_entrada;
    const panel = document.getElementById('rsiEntryPanel');
    panel.classList.remove('hidden');

    document.getElementById('rsiEntryPrincipal').textContent = rsi.principal_mensagem || '--';

    const tfs = rsi.timeframes || {};
    const tfOrder = Object.keys(tfs);
    const tbody = document.getElementById('rsiEntryBody');
    tbody.innerHTML = '';

    for (const tf of tfOrder) {
        const s = tfs[tf];
        let estadoClass = 'status-baixa';
        if (s.estado === 'zona_ideal') estadoClass = 'status-alta';
        else if (s.estado === 'esticado') estadoClass = 'decisao-confirmacao';
        else if (s.estado === 'forca_insuficiente') estadoClass = 'status-baixa';
        else if (s.estado === 'indisponivel') estadoClass = 'status-none';

        const pesoLabel = s.peso === 'principal' ? '⭐ Principal' :
                          s.peso === 'macro' ? '📈 Macro' : 'Secundário';

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${tf}</strong></td>
            <td>${s.rsi !== null && s.rsi !== undefined ? s.rsi.toFixed(1) : '—'}</td>
            <td class="${estadoClass}">${s.mensagem || '—'}</td>
            <td>${pesoLabel}</td>
        `;
        tbody.appendChild(tr);
    }
}

function renderStrategyList(container, title, strategies) {
    if (!strategies || strategies.length === 0) {
        container.innerHTML = '';
        return;
    }
    let html = `<h3 class="strategy-section-title">${title}</h3>`;
    for (const s of strategies) {
        html += `<div class="strategy-card">
            <h4>${s.nome}</h4>`;
        if (s.tambem_chamado) {
            html += `<p class="strategy-alias">Também chamado: ${s.tambem_chamado}</p>`;
        }
        html += `<p><span class="strategy-meta-label">Tipo:</span> ${s.tipo}</p>`;
        if (s.quando_estudar) {
            html += `<p><span class="strategy-meta-label">Quando estudar:</span> ${s.quando_estudar}</p>`;
        }
        html += `<p><span class="strategy-meta-label">Por que faz sentido:</span> ${s.por_que_faz_sentido}</p>
            <p><span class="strategy-meta-label">Risco principal:</span> ${s.risco_principal}</p>
        </div>`;
    }
    container.innerHTML = html;
}

async function executarRadar(tipo, force) {
    const statusEl = document.getElementById('radarStatus');
    const resultsEl = document.getElementById('radarResults');
    statusEl.classList.remove('hidden');
    statusEl.textContent = `Executando Radar ${tipo === 'cripto' ? 'Cripto' : 'Ações'}...`;
    resultsEl.classList.add('hidden');

    try {
        const endpoint = tipo === 'cripto' ? '/api/radar/cripto' : '/api/radar/acoes';
        const url = force ? `${endpoint}?force=true` : endpoint;
        const resp = await fetchWithTimeout(url, {}, 600000);
        const data = await resp.json();

        if (!resp.ok || data.ok === false) {
            throw new Error(data.error || `Erro ${resp.status}`);
        }

        renderRadarResult(data, tipo);
        statusEl.textContent = '';
        statusEl.classList.add('hidden');
    } catch (err) {
        statusEl.textContent = `Erro: ${err.message}`;
    }
}

function renderRadarResult(data, tipo) {
    document.getElementById('radarTitle').textContent = `Radar ${tipo === 'cripto' ? 'Cripto' : 'Ações'}`;
    const resultsEl = document.getElementById('radarResults');
    resultsEl.classList.remove('hidden');

    const fmtVal = (v, dec) => {
        const n = Number(v);
        return Number.isFinite(n) ? new Intl.NumberFormat('pt-BR', { minimumFractionDigits: dec, maximumFractionDigits: dec }).format(n) : '—';
    };

    const tbody = document.getElementById('radarBody');
    tbody.innerHTML = '';

    if (data.aprovados && data.aprovados.length > 0) {
        for (const a of data.aprovados) {
            const varClass = Number(a.variacao_percentual) > 0 ? 'mkt-positive' : Number(a.variacao_percentual) < 0 ? 'mkt-negative' : 'mkt-neutral';
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${a.symbol}</strong></td>
                <td>${fmtVal(a.preco_atual, 2)}</td>
                <td class="${varClass}">${Number.isFinite(Number(a.variacao_percentual)) ? (Number(a.variacao_percentual) > 0 ? '+' : '') + fmtVal(Math.abs(Number(a.variacao_percentual)), 2) + '%' : '—'}</td>
                <td>${a.rsi_principal ?? '—'}</td>
                <td style="font-size:0.8rem;">${a.tendencia || '—'}</td>
                <td style="font-size:0.78rem;">${a.volatilidade || '—'}</td>
                <td style="font-size:0.8rem;">${a.decisao || '—'}</td>
            `;
            tbody.appendChild(tr);
        }
    } else {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:1rem;">Nenhum ativo encontrado com RSI na zona ideal neste momento.</td></tr>';
    }

    const cacheInfo = data.cache_hit ? ' (cache)' : '';
    document.getElementById('radarSummary').textContent =
        `${data.total_aprovados} aprovados de ${data.total_analisados} analisados · ${data.execucao_segundos ?? '?'}s · ${data.criterio}${cacheInfo}`;
}

async function carregarHistorico() {
    const limit = document.getElementById('historyLimit').value;
    try {
        const resp = await fetch(`/api/historico?limit=${limit}`);
        const data = await resp.json();
        const tbody = document.getElementById('historyBody');
        tbody.innerHTML = '';
        for (const row of data) {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${row.timestamp}</td>
                <td><strong>${row.ativo}</strong></td>
                <td><span class="badge ${row.tipo}">${row.tipo}</span></td>
                <td>${row.interpretacao}</td>
            `;
            tbody.appendChild(tr);
        }
    } catch (err) {
        console.error('Erro ao carregar histórico:', err);
    }
}

// Load initial history
carregarHistorico();

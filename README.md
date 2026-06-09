# QSignalTrader

Sistema de análise técnica para geração de sinais de tendência em criptoativos e ações americanas, com foco em position trade.

## Metodologia

- **EMAs**: 8, 21, 50, 100 e 200 períodos
- **RSI**: Período 14, validação de tendência forte com RSI > 58
- **ATR**: Período 14
- **Pivôs de Fibonacci**: Pivot, R1/R2/R3, S1/S2/S3
- **Confluência entre múltiplos timeframes**

### Criptoativos

Timeframes: 15m, 1h, 4h, 1D, 1W — dados via CCXT (Binance)

### Ações Americanas

Timeframes: 1d, 5d, 1wk — dados via Yahoo Finance

## Instalação

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Executar Interface Web

```bash
python main.py
```

Ou diretamente:

```bash
uvicorn web.app:app --reload --host 127.0.0.1 --port 8000
```

Acessar: http://127.0.0.1:8000

## Executar Interface Streamlit (Online)

```bash
pip install streamlit
streamlit run app_streamlit.py
```

### Deploy no Streamlit Community Cloud

1. Subir o projeto para GitHub
2. Acessar [share.streamlit.io](https://share.streamlit.io)
3. New app → selecionar repositório e branch
4. Main file path: `app_streamlit.py`
5. Deploy

### Editar Listas de Radar

Os arquivos `radar_cripto.txt` e `radar_acoes.txt` ficam na raiz do projeto.
Edite diretamente (uma linha por ativo, ignore linhas com `#`).

### Cache

Todas as funções de análise usam cache com TTL de 15 minutos (900s).
Use o checkbox "Forçar atualização" na sidebar para ignorar o cache.

Os radares rodam apenas sob demanda (clique no botão), nunca automaticamente.

## Estrutura

```
QSignalTrader/
├── src/
│   ├── data/
│   │   ├── fetch_crypto.py      # Coleta de dados cripto via CCXT
│   │   └── yfinance_handler.py  # Coleta de dados de ações via Yahoo Finance
│   ├── indicators/
│   │   └── technicals.py        # EMAs, RSI, ATR, Fibonacci Pivots
│   ├── strategy/
│   │   └── multi_tf_analysis.py # Análise multi-timeframe
│   ├── signals/
│   │   ├── signal_engine.py     # Interpretação de tendência / geração de sinais
│   │   └── logger.py            # Registro de sinais e volatilidade em SQLite
│   ├── volatility/
│   │   ├── volatility_config.py # Configurações e utilidades BTC
│   │   ├── realized_vol.py      # Métricas de volatilidade realizada
│   │   ├── implied_vol.py       # Métricas de volatilidade implícita (DVOL Deribit)
│   │   └── volatility_engine.py # Motor de volatilidade (scores + regimes)
│   └── utils/
│       └── dates.py
├── web/
│   ├── app.py                   # FastAPI
│   ├── static/
│   │   ├── style.css
│   │   └── app.js
│   └── templates/
│       └── index.html
├── logs/
│   └── sinais.db                # Banco SQLite (criado automaticamente)
├── main.py
├── requirements.txt
└── README.md
```

## Endpoints da API

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/` | Painel web |
| GET | `/api/sinal?symbol=BTC/USDT` | Análise completa (JSON), inclui volatilidade p/ BTC |
| GET | `/api/ohlcv?symbol=BTC/USDT&timeframe=1h` | Dados OHLCV + indicadores para gráfico |
| GET | `/api/historico?limit=25&ativo=BTC/USDT&tipo=cripto` | Histórico de sinais |
| GET | `/api/btc/volatilidade` | Motor de volatilidade BTC |
| GET | `/api/btc/analise-completa` | Direção + volatilidade + leitura combinada BTC |
| GET | `/api/btc/historico-volatilidade?limit=25` | Histórico de análises de volatilidade BTC |

## Motor de Volatilidade BTC

O sistema inclui um motor de volatilidade específico para BTC/USDT, voltado para análise de opções.

### Métricas de Volatilidade Realizada
- **ATR Percentual**: ATR / close * 100, com média móvel 50, ratio e slope
- **Bollinger BandWidth**: (upper - lower) / MA, com percentil (252 períodos) e slope
- **Realized Volatility (RV)**: RV7, RV30, RV90 anualizadas, com razões RV7/RV30 e RV30/RV90

### Métricas de Volatilidade Implícita
- **DVOL**: Volatilidade implícita do BTC via Deribit (proxy de IV)
- **IV Rank**: (DVOL atual - DVOL min) / (DVOL max - DVOL min) * 100
- **IV Percentile**: % de dias com DVOL abaixo do nível atual
- **IV/RV Ratio**: Relação entre volatilidade implícita e realizada

### Regimes de Volatilidade
- 🧨 Volatilidade comprimida com risco de expansão
- 🚀 Volatilidade em expansão
- 🌋 Volatilidade alta e ainda sustentada
- 🧊 Volatilidade elevada com probabilidade de contração
- 🌫 Zona de transição da volatilidade

O motor é ativado automaticamente ao analisar BTC/USDT no painel web.

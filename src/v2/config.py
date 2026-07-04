from __future__ import annotations

RSI_TREND_MIN = 52
RSI_TREND_MAX = 66
RSI_PULLBACK_MIN = 42
RSI_PULLBACK_MAX = 55
RSI_BREAKOUT_MIN = 55
RSI_BREAKOUT_MAX = 72
RSI_RECOVERY_CROSS = 45

W_RSI_ZONE = 25
W_MOMENTUM_TURN = 25
W_TREND_FILTER = 20
W_EXTENSION_RISK = 15
W_VOLUME = 10
W_DATA_QUALITY = 5

MAX_DISTANCE_EMA21_PCT = 8.0
BREAKOUT_MAX_DIST_FROM_20D_HIGH = 3.0
MIN_VOL_REL_BREAKOUT = 1.2

DEFAULT_PERIOD = "1y"
DEFAULT_MIN_SCORE = 60
DEFAULT_MAX_TICKERS = 50

SWING_WINDOW = 3
CLUSTER_PCT = 1.0
MAX_LEVELS_EACH_SIDE = 3

IBOVESPA_TICKERS = [
    "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA",
    "WEGE3.SA", "PRIO3.SA", "ABEV3.SA", "RENT3.SA", "SUZB3.SA",
    "ELET3.SA", "EQTL3.SA", "RADL3.SA", "B3SA3.SA", "GGBR4.SA",
]

US_TICKERS = [
    "AAPL", "MSFT", "NVDA", "TSLA", "META", "AMZN", "GOOGL",
]

RADAR_MODES = {
    "TENDENCIA_SAUDAVEL": "Tendência Saudável",
    "PULLBACK_DE_ALTA": "Pullback de Alta",
    "BREAKOUT_SETUP": "Breakout Setup",
    "RECUPERACAO_INICIAL": "Recuperação Inicial",
}

STATUS_THRESHOLDS = {
    (85, 100): "PRIORIDADE_ALTA",
    (75, 84): "BOM_CANDIDATO",
    (60, 74): "CANDIDATO_OBSERVAVEL",
    (40, 59): "MONITORAR_FRACO",
    (0, 39): "IGNORAR",
}

QSIGNAL_WEIGHTS = {
    "trend": 0.30,
    "momentum": 0.25,
    "location": 0.20,
    "relative_strength": 0.10,
    "risk": 0.10,
    "data_quality": 0.05,
}

QSIGNAL_CLASS_MAP = [(85, "EXCELENTE"), (70, "BOM"), (55, "OBSERVAVEL"), (40, "FRACO"), (0, "RUIM")]

TREND_STRONG = 80
TREND_HEALTHY = 60
MOMENTUM_STRONG = 80
MOMENTUM_FAVORABLE = 60
LOCATION_GOOD = 70
RISK_ACCEPTABLE = 60
RS_GOOD = 60

EMA_SHORT = 21
EMA_MEDIUM = 50
EMA_LONG = 200

NEAR_SUPPORT_PCT = 3.0
NEAR_RESISTANCE_PCT = 3.0
MIN_REWARD_RISK_GOOD = 2.0
MIN_REWARD_RISK_ACCEPTABLE = 1.3

REGIME_LABELS = {
    "BULL_FORTE": "Bull Forte",
    "BULL_SAUDAVEL": "Bull Saudável",
    "PULLBACK_DE_ALTA": "Pullback de Alta",
    "BREAKOUT_SETUP": "Breakout Setup",
    "BREAKOUT_CONFIRMADO": "Breakout Confirmado",
    "LATERALIZACAO": "Lateralização",
    "RECUPERACAO": "Recuperação",
    "DISTRIBUICAO": "Distribuição",
    "BEAR_FORTE": "Bear Forte",
    "INDEFINIDO": "Indefinido",
}

STRATEGY_LABELS = {
    "TREND_CONTINUATION": "Continuação de Tendência",
    "PULLBACK_BUY": "Compra em Pullback",
    "BREAKOUT_CONFIRMATION": "Confirmação de Breakout",
    "RECOVERY_WATCH": "Observar Recuperação",
    "DEFENSIVE_MODE": "Modo Defensivo",
    "NO_TRADE": "Fora / Aguardar",
}

ACTION_NO_POSITION = ["COMPRAR_PARCIAL", "AGUARDAR_GATILHO", "OBSERVAR", "EVITAR"]
ACTION_WITH_POSITION = ["AUMENTAR", "MANTER", "MANTER_COM_CAUTELA", "REDUZIR", "SAIR"]

# ── Crypto V2 ──
QSIGNAL_CRYPTO_WEIGHTS = {
    "trend": 0.25, "momentum": 0.30, "location": 0.15,
    "btc_relative_strength": 0.15, "risk": 0.10, "data_quality": 0.05,
}

CRYPTO_REGIME_LABELS = {
    "CRYPTO_BULL_FORTE": "Bull forte", "CRYPTO_BULL_SAUDAVEL": "Bull saudável",
    "CRYPTO_PULLBACK_DE_ALTA": "Pullback de alta", "CRYPTO_BREAKOUT_SETUP": "Breakout setup",
    "CRYPTO_BREAKOUT_CONFIRMADO": "Breakout confirmado", "CRYPTO_ALTCOIN_LIDER": "Altcoin líder",
    "CRYPTO_RECUPERACAO": "Recuperação", "CRYPTO_DISTRIBUICAO": "Distribuição",
    "CRYPTO_BEAR_FORTE": "Bear forte", "CRYPTO_CAPITULACAO": "Capitulação",
    "CRYPTO_LATERALIZACAO": "Lateralização", "CRYPTO_INDEFINIDO": "Indefinido",
}

CRYPTO_STRATEGY_LABELS = {
    "CRYPTO_TREND_CONTINUATION": "Continuação de tendência",
    "CRYPTO_PULLBACK_BUY": "Compra no pullback",
    "CRYPTO_BREAKOUT_CONFIRMATION": "Confirmação de breakout",
    "CRYPTO_ALTCOIN_LEADER": "Altcoin líder",
    "CRYPTO_RECOVERY_WATCH": "Monitorar recuperação",
    "CRYPTO_DEFENSIVE_MODE": "Modo defensivo",
    "CRYPTO_NO_TRADE": "No trade",
}

CRYPTO_RADAR_RSI_MIN = 56
CRYPTO_RADAR_RSI_MAX = 66
CRYPTO_ATR_NORMAL_MAX = 8.0
CRYPTO_ATR_HIGH = 12.0
CRYPTO_CLUSTER_PCT = 1.5

from __future__ import annotations

import os
import re
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_RADAR_CRYPTO_FILE = _PROJECT_ROOT / "radar_cripto.txt"

_KNOWN_PAIRS = {
    "BTC": "BTC/USDT", "BTCUSDT": "BTC/USDT", "BTC-USD": "BTC/USDT",
    "ETH": "ETH/USDT", "ETHUSDT": "ETH/USDT", "ETH-USD": "ETH/USDT",
    "SOL": "SOL/USDT", "SOLUSDT": "SOL/USDT", "SOL-USD": "SOL/USDT",
    "BNB": "BNB/USDT", "BNBUSDT": "BNB/USDT",
    "XRP": "XRP/USDT", "XRPUSDT": "XRP/USDT",
    "ADA": "ADA/USDT", "ADAUSDT": "ADA/USDT",
    "DOGE": "DOGE/USDT", "DOGEUSDT": "DOGE/USDT",
    "AVAX": "AVAX/USDT", "AVAXUSDT": "AVAX/USDT",
    "LINK": "LINK/USDT", "LINKUSDT": "LINK/USDT",
    "DOT": "DOT/USDT", "DOTUSDT": "DOT/USDT",
    "MATIC": "MATIC/USDT", "MATICUSDT": "MATIC/USDT",
    "NEAR": "NEAR/USDT", "NEARUSDT": "NEAR/USDT",
    "ATOM": "ATOM/USDT", "ATOMUSDT": "ATOM/USDT",
    "UNI": "UNI/USDT", "UNIUSDT": "UNI/USDT",
    "LTC": "LTC/USDT", "LTCUSDT": "LTC/USDT",
    "BCH": "BCH/USDT", "BCHUSDT": "BCH/USDT",
    "FIL": "FIL/USDT", "FILUSDT": "FIL/USDT",
    "APT": "APT/USDT", "APTUSDT": "APT/USDT",
    "ARB": "ARB/USDT", "ARBUSDT": "ARB/USDT",
    "OP": "OP/USDT", "OPUSDT": "OP/USDT",
    "SUI": "SUI/USDT", "SUIUSDT": "SUI/USDT",
    "INJ": "INJ/USDT", "INJUSDT": "INJ/USDT",
    "TON": "TON/USDT", "TONUSDT": "TON/USDT",
    "TRX": "TRX/USDT", "TRXUSDT": "TRX/USDT",
    "AAVE": "AAVE/USDT", "AAVEUSDT": "AAVE/USDT",
    "FET": "FET/USDT", "FETUSDT": "FET/USDT",
    "RNDR": "RNDR/USDT", "RNDRUSDT": "RNDR/USDT",
    "TIA": "TIA/USDT", "TIAUSDT": "TIA/USDT",
    "SEI": "SEI/USDT", "SEIUSDT": "SEI/USDT",
    "RUNE": "RUNE/USDT", "RUNEUSDT": "RUNE/USDT",
}


def _normalize_crypto(symbol: str) -> str:
    s = symbol.strip().upper().replace(" ", "")
    if s in _KNOWN_PAIRS:
        return _KNOWN_PAIRS[s]
    if "/" in s:
        return s
    if s.endswith("USDT"):
        base = s[:-4]
        return f"{base}/USDT"
    if s.endswith("USD"):
        base = s[:-3]
        return f"{base}/USDT"
    return f"{s}/USDT"


def load_crypto_assets() -> dict:
    assets = []
    source = "radar_cripto.txt"
    warnings = []
    errors = []

    if _RADAR_CRYPTO_FILE.exists():
        raw = _RADAR_CRYPTO_FILE.read_text(encoding="utf-8")
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            sym = _normalize_crypto(line)
            if sym and sym not in assets:
                assets.append(sym)
        if not assets:
            warnings.append("radar_cripto.txt está vazio")
    else:
        warnings.append("radar_cripto.txt não encontrado")
        defaults = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
        assets = defaults
        source = "fallback (padrão)"

    env_val = os.getenv("QTRADER_CRYPTOS", "")
    if env_val:
        for p in re.split(r"[,;]", env_val):
            p = p.strip().strip('"').strip("'")
            if p:
                sym = _normalize_crypto(p)
                if sym and sym not in assets:
                    assets.append(sym)
        if env_val:
            source += " + env"

    stock_patterns = re.compile(r"^(AAPL|MSFT|NVDA|TSLA|META|AMZN|GOOGL|SPY|QQQ|PETR\d|VALE\d|ITUB\d|WEGE\d|PRIO\d)", re.IGNORECASE)
    filtered = [a for a in assets if not stock_patterns.match(a.replace("/", ""))]

    return {
        "assets": filtered,
        "source": source,
        "count": len(filtered),
        "warnings": warnings,
        "errors": errors,
    }

from __future__ import annotations

import os
import re
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_RADAR_STOCKS_FILE = _PROJECT_ROOT / "radar_acoes.txt"
_CRYPTO_PATTERNS = re.compile(r"/USDT|/USD|BTCUSD|ETHUSD|SOLUSD|PERP", re.IGNORECASE)


def load_stock_assets() -> dict:
    assets = []
    source = "radar_acoes.txt"
    warnings = []
    errors = []

    # 1. Try radar_acoes.txt (V1 source)
    if _RADAR_STOCKS_FILE.exists():
        raw = _RADAR_STOCKS_FILE.read_text(encoding="utf-8")
        parsed = _parse_asset_list(raw)
        assets.extend(parsed)
        if not parsed:
            warnings.append("radar_acoes.txt está vazio")
    else:
        warnings.append("radar_acoes.txt não encontrado")

    # 2. Fallback: environment variable
    env_val = os.getenv("QTRADER_STOCKS", "")
    if env_val:
        parsed_env = _parse_asset_list(env_val)
        for a in parsed_env:
            if a not in assets:
                assets.append(a)
        if parsed_env:
            source += " + env"

    # 3. Filter crypto pairs
    filtered = []
    crypto_dropped = []
    for a in assets:
        if _CRYPTO_PATTERNS.search(a):
            crypto_dropped.append(a)
        else:
            filtered.append(a)
    if crypto_dropped:
        warnings.append(f"{len(crypto_dropped)} pares cripto ignorados")

    return {
        "assets": filtered,
        "source": source,
        "count": len(filtered),
        "warnings": warnings,
        "errors": errors,
    }


def _parse_asset_list(raw: str) -> list[str]:
    if not raw or not raw.strip():
        return []

    # Try JSON-like: ["AAPL", "MSFT"]
    stripped = raw.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        stripped = stripped[1:-1]

    # Split by comma, semicolon, or newline
    parts = re.split(r"[;,]", stripped)
    if len(parts) <= 1:
        parts = stripped.splitlines()

    assets = []
    for p in parts:
        p = p.strip().strip('"').strip("'")
        if p:
            assets.append(p.upper())
    return list(dict.fromkeys(assets))  # dedup keeping order

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.fetch_crypto import fetch_crypto_data_with_metadata
from src.indicators.technicals import add_rsi

DEFAULT_SYMBOLS = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "ZEC/USDT",
    "LINK/USDT",
    "AAVE/USDT",
    "DOGE/USDT",
    "AVAX/USDT",
    "NEAR/USDT",
    "INJ/USDT",
]


def _read_symbols(path: str | None) -> list[str]:
    if not path:
        return DEFAULT_SYMBOLS
    text = Path(path).read_text(encoding="utf-8")
    symbols = []
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            symbols.append(line)
    return symbols


def _rsi(df):
    df = add_rsi(df)
    value = df["rsi"].iloc[-1]
    if value != value:
        return None
    return round(float(value), 1)


def _format_row(values: list[str], widths: list[int]) -> str:
    return " | ".join(value.ljust(width) for value, width in zip(values, widths))


def diagnose(symbols: list[str], timeframe: str, limit: int) -> list[list[str]]:
    rows = []
    for symbol in symbols:
        try:
            result = fetch_crypto_data_with_metadata(
                symbol=symbol, timeframe=timeframe, limit=limit
            )
            rows.append(
                [
                    symbol,
                    "OK",
                    result.exchange,
                    result.market_type,
                    result.resolved_symbol,
                    str(result.candles),
                    str(_rsi(result.df)),
                    "",
                ]
            )
        except Exception as exc:
            attempts = getattr(exc, "attempts", [])
            last = attempts[-1] if attempts else {}
            rows.append(
                [
                    symbol,
                    "FALHOU",
                    str(last.get("exchange") or ""),
                    str(last.get("market_type") or ""),
                    str(last.get("symbol") or ""),
                    "0",
                    "",
                    str(last.get("error") or exc)[:160],
                ]
            )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnostica fontes OHLCV cripto.")
    parser.add_argument("--symbols-file", help="Arquivo com um simbolo por linha.")
    parser.add_argument("--timeframe", default="4h")
    parser.add_argument("--limit", type=int, default=120)
    args = parser.parse_args()

    headers = [
        "Ativo",
        "Status",
        "Exchange",
        "Market Type",
        "Simbolo resolvido",
        "Candles",
        "RSI",
        "Motivo se falhou",
    ]
    rows = diagnose(_read_symbols(args.symbols_file), args.timeframe, args.limit)
    widths = [
        max(len(str(row[i])) for row in [headers] + rows)
        for i in range(len(headers))
    ]
    print(_format_row(headers, widths))
    print(_format_row(["-" * width for width in widths], widths))
    for row in rows:
        print(_format_row(row, widths))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

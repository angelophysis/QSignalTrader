from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import ccxt
import pandas as pd

CRYPTO_TIMEOUT_MS = 8000
CACHE_VERSION = "crypto_sources_v3"

_CRYPTO_EXCHANGES = ["okx", "bybit", "kraken", "binance"]


@dataclass(frozen=True)
class CryptoSource:
    exchange: str
    market_type: str
    ccxt_id: str
    default_type: str | None = None

    @property
    def label(self) -> str:
        return f"{self.exchange}/{self.market_type}"


@dataclass
class CryptoFetchResult:
    df: pd.DataFrame
    exchange: str
    market_type: str
    resolved_symbol: str
    requested_symbol: str
    candles: int
    fallback_used: bool
    attempts: list[dict[str, Any]]


@dataclass
class CryptoTickerResult:
    ticker: dict[str, Any]
    exchange: str
    market_type: str
    resolved_symbol: str
    requested_symbol: str
    fallback_used: bool
    attempts: list[dict[str, Any]]


class CryptoDataError(RuntimeError):
    def __init__(self, message: str, attempts: list[dict[str, Any]]):
        super().__init__(message)
        self.attempts = attempts


CRYPTO_SOURCES: tuple[CryptoSource, ...] = (
    CryptoSource("okx", "spot", "okx", "spot"),
    CryptoSource("bybit", "spot", "bybit", "spot"),
    CryptoSource("kraken", "spot", "kraken"),
    CryptoSource("okx", "swap", "okx", "swap"),
    CryptoSource("bybit", "swap", "bybit", "swap"),
    CryptoSource("binance", "spot", "binance", "spot"),
    CryptoSource("binanceusdm", "swap", "binanceusdm"),
)

_exchange_instances: dict[tuple[str, str], Any] = {}
_markets_loaded: set[tuple[str, str]] = set()


def get_crypto_source_labels() -> list[str]:
    return [source.label for source in CRYPTO_SOURCES]


def _source_key(source: CryptoSource) -> tuple[str, str]:
    return (source.ccxt_id, source.market_type)


def _get_source(exchange_name: str = "okx", market_type: str = "spot") -> CryptoSource:
    for source in CRYPTO_SOURCES:
        if source.exchange == exchange_name and source.market_type == market_type:
            return source
        if source.ccxt_id == exchange_name and source.market_type == market_type:
            return source
    default_type = market_type if market_type in {"spot", "swap"} else None
    return CryptoSource(exchange_name, market_type, exchange_name, default_type)


def _get_exchange(exchange_name: str = "okx", market_type: str = "spot"):
    source = _get_source(exchange_name, market_type)
    key = _source_key(source)
    if key not in _exchange_instances:
        exchange_class = getattr(ccxt, source.ccxt_id)
        config: dict[str, Any] = {
            "enableRateLimit": True,
            "timeout": CRYPTO_TIMEOUT_MS,
        }
        if source.default_type:
            config["options"] = {"defaultType": source.default_type}
        _exchange_instances[key] = exchange_class(config)
    return _exchange_instances[key]


def _load_markets(exchange, source: CryptoSource) -> dict:
    key = _source_key(source)
    if key in _markets_loaded and exchange.markets:
        return exchange.markets

    try:
        markets = exchange.load_markets()
    except TypeError as exc:
        if source.ccxt_id != "okx" or "NoneType" not in str(exc):
            raise
        raw_markets = exchange.fetch_markets()
        valid_markets = [
            market
            for market in raw_markets
            if market.get("id") and market.get("symbol")
        ]
        exchange.set_markets(valid_markets)
        markets = exchange.markets

    _markets_loaded.add(key)
    return markets


def _split_symbol(symbol: str) -> tuple[str, str]:
    clean = symbol.strip().upper()
    clean = clean.split(":")[0]
    if "/" in clean:
        base, quote = clean.split("/", 1)
        return base.strip(), quote.strip()

    for quote in ("USDT", "USDC", "USD"):
        if clean.endswith(quote) and len(clean) > len(quote):
            return clean[: -len(quote)], quote
    return clean, "USDT"


def _quote_candidates(preferred_quote: str) -> list[str]:
    quotes = []
    for quote in (preferred_quote, "USDT", "USD", "USDC"):
        if quote and quote not in quotes:
            quotes.append(quote)
    return quotes


def _symbol_candidates(symbol: str, market_type: str) -> list[str]:
    base, quote = _split_symbol(symbol)
    candidates = []
    for quote_candidate in _quote_candidates(quote):
        if market_type == "swap":
            candidates.append(f"{base}/{quote_candidate}:{quote_candidate}")
        candidates.append(f"{base}/{quote_candidate}")
    return candidates


def _market_matches(market: dict, market_type: str) -> bool:
    if market_type == "swap":
        return bool(market.get("swap") or market.get("type") == "swap")
    return bool(market.get("spot") or market.get("type") == "spot")


def _format_attempt_error(exc: Exception) -> str:
    msg = str(exc).replace("\n", " ").strip()
    return msg[:240]


def _ohlcv_to_dataframe(ohlcv: list) -> pd.DataFrame:
    df = pd.DataFrame(
        ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df


def _ordered_sources(exchange_name: str | None = None) -> list[CryptoSource]:
    if not exchange_name or exchange_name == "okx":
        return list(CRYPTO_SOURCES)

    preferred = [
        source
        for source in CRYPTO_SOURCES
        if source.exchange == exchange_name or source.ccxt_id == exchange_name
    ]
    return preferred + [source for source in CRYPTO_SOURCES if source not in preferred]


def fetch_crypto_data_with_metadata(
    symbol: str = "BTC/USDT",
    exchange_name: str = "okx",
    timeframe: str = "1h",
    limit: int = 100,
) -> CryptoFetchResult:
    attempts: list[dict[str, Any]] = []
    normalized_timeframe = timeframe.lower()
    sources = _ordered_sources(exchange_name)

    for source_index, source in enumerate(sources):
        exchange = None
        try:
            exchange = _get_exchange(source.ccxt_id, source.market_type)
            markets = _load_markets(exchange, source)
        except Exception as exc:
            attempts.append(
                {
                    "exchange": source.exchange,
                    "market_type": source.market_type,
                    "symbol": None,
                    "stage": "load_markets",
                    "error_type": type(exc).__name__,
                    "error": _format_attempt_error(exc),
                }
            )
            continue

        matched_symbol = None
        for candidate in _symbol_candidates(symbol, source.market_type):
            market = markets.get(candidate)
            if market and _market_matches(market, source.market_type):
                matched_symbol = candidate
                break

        if not matched_symbol:
            attempts.append(
                {
                    "exchange": source.exchange,
                    "market_type": source.market_type,
                    "symbol": None,
                    "stage": "resolve_symbol",
                    "error_type": "SymbolNotAvailable",
                    "error": f"{symbol} indisponivel em {source.label}",
                }
            )
            continue

        try:
            ohlcv = exchange.fetch_ohlcv(
                matched_symbol, normalized_timeframe, limit=limit
            )
            df = _ohlcv_to_dataframe(ohlcv)
            if df.empty:
                raise ValueError("OHLCV vazio")
            return CryptoFetchResult(
                df=df,
                exchange=source.exchange,
                market_type=source.market_type,
                resolved_symbol=matched_symbol,
                requested_symbol=symbol,
                candles=len(df),
                fallback_used=source_index > 0 or matched_symbol != symbol.strip().upper(),
                attempts=attempts,
            )
        except Exception as exc:
            attempts.append(
                {
                    "exchange": source.exchange,
                    "market_type": source.market_type,
                    "symbol": matched_symbol,
                    "stage": "fetch_ohlcv",
                    "error_type": type(exc).__name__,
                    "error": _format_attempt_error(exc),
                }
            )

    last = attempts[-1] if attempts else {}
    reason = last.get("error") or "nenhuma fonte cripto disponivel"
    raise CryptoDataError(
        f"Todas as fontes cripto falharam para {symbol} ({timeframe}): {reason}",
        attempts,
    )


def fetch_crypto_ticker_with_metadata(
    symbol: str = "BTC/USDT",
    exchange_name: str = "okx",
) -> CryptoTickerResult:
    attempts: list[dict[str, Any]] = []
    sources = _ordered_sources(exchange_name)

    for source_index, source in enumerate(sources):
        try:
            exchange = _get_exchange(source.ccxt_id, source.market_type)
            markets = _load_markets(exchange, source)
        except Exception as exc:
            attempts.append(
                {
                    "exchange": source.exchange,
                    "market_type": source.market_type,
                    "symbol": None,
                    "stage": "load_markets",
                    "error_type": type(exc).__name__,
                    "error": _format_attempt_error(exc),
                }
            )
            continue

        matched_symbol = None
        for candidate in _symbol_candidates(symbol, source.market_type):
            market = markets.get(candidate)
            if market and _market_matches(market, source.market_type):
                matched_symbol = candidate
                break

        if not matched_symbol:
            attempts.append(
                {
                    "exchange": source.exchange,
                    "market_type": source.market_type,
                    "symbol": None,
                    "stage": "resolve_symbol",
                    "error_type": "SymbolNotAvailable",
                    "error": f"{symbol} indisponivel em {source.label}",
                }
            )
            continue

        try:
            ticker = exchange.fetch_ticker(matched_symbol)
            return CryptoTickerResult(
                ticker=ticker,
                exchange=source.exchange,
                market_type=source.market_type,
                resolved_symbol=matched_symbol,
                requested_symbol=symbol,
                fallback_used=source_index > 0 or matched_symbol != symbol.strip().upper(),
                attempts=attempts,
            )
        except Exception as exc:
            attempts.append(
                {
                    "exchange": source.exchange,
                    "market_type": source.market_type,
                    "symbol": matched_symbol,
                    "stage": "fetch_ticker",
                    "error_type": type(exc).__name__,
                    "error": _format_attempt_error(exc),
                }
            )

    last = attempts[-1] if attempts else {}
    reason = last.get("error") or "nenhuma fonte cripto disponivel"
    raise CryptoDataError(
        f"Todas as fontes cripto falharam para ticker {symbol}: {reason}",
        attempts,
    )


def get_crypto_data(
    symbol: str = "BTC/USDT",
    exchange_name: str = "okx",
    timeframe: str = "1h",
    limit: int = 100,
) -> pd.DataFrame:
    result = fetch_crypto_data_with_metadata(
        symbol=symbol,
        exchange_name=exchange_name,
        timeframe=timeframe,
        limit=limit,
    )
    return result.df

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd
import yfinance as yf


@dataclass(frozen=True)
class YahooFinanceDataHandler:
    """Baixa dados de ações via yfinance e devolve série/df pronta para estratégia."""
    auto_adjust: bool = True

    def fetch_ohlc(
        self,
        ticker: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        interval: str = '1d',
        period: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Retorna um DataFrame com colunas padronizadas: open, high, low, close, volume.
        """
        kwargs = {
            "tickers": ticker,
            "interval": interval,
            "auto_adjust": self.auto_adjust,
            "progress": False,
        }
        if period:
            kwargs["period"] = period
        else:
            kwargs["start"] = start
            kwargs["end"] = end

        df = yf.download(**kwargs)

        if df is None or df.empty:
            raise ValueError(f"Sem dados para {ticker} no periodo {start} -> {end}")

        # Se o DataFrame tiver MultiIndex nas colunas (ex: ('Open', 'AAPL')), achata para 'Open'
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Padroniza nomes para minúsculas
        df = df.rename(
            columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Adj Close': 'adj_close',
                'Volume': 'volume',
            },
        )

        # Se auto_adjust=True, 'Adj Close' costuma nem vir. Garantimos 'close' sempre.
        wanted = [c for c in ['open', 'high', 'low', 'close', 'volume'] if c in df.columns]

        df.columns.name = None
        return df[wanted].dropna()

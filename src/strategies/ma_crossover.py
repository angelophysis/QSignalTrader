from __future__ import annotations

import pandas as pd


def ma_crossover_signals(
    df: pd.DataFrame,
    short_window: int = 50,
    long_window: int = 200,
    price_col: str = "close",
) -> pd.DataFrame:
    """
    Gera sinais de MA crossover.
    Retorna df com:
      - ma_short, ma_long
      - signal: +1 se ma_short > ma_long, senão -1
      - trade: +1 no cruzamento de entrada, -1 no de saída, 0 caso contrário
    """
    if price_col not in df.columns:
        raise ValueError(f"Coluna '{price_col}' não encontrada no DataFrame.")

    out = df.copy()

    out["ma_short"] = out[price_col].rolling(window=short_window).mean()
    out["ma_long"] = out[price_col].rolling(window=long_window).mean()

    # estado: +1 comprado, -1 fora/short (por enquanto vamos tratar como "fora")
    out["signal"] = (out["ma_short"] > out["ma_long"]).astype(int)
    out["signal"] = out["signal"].replace({0: -1})

    # evento: onde mudou o estado
    out["trade"] = out["signal"].diff().fillna(0)

    # trade será +2 ou -2 (porque vai de -1 para +1). Vamos normalizar para +1/-1.
    out.loc[out["trade"] > 0, "trade"] = 1
    out.loc[out["trade"] < 0, "trade"] = -1

    return out

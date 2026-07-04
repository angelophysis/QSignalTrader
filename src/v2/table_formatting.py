from __future__ import annotations

import pandas as pd


_COLUMN_DISPLAY_NAMES = {
    "Ticker": "Ativo", "Symbol": "Ativo",
    "Preco": "Preço", "Price": "Preço",
    "RadarLiteScore": "Score", "RadarScore": "Score",
    "Status": "Status", "Modos": "Modos", "Warnings": "Avisos",
    "RSI": "RSI", "RSI_Delta_3": "RSI 3c",
    "ROC_10": "ROC 10", "ROC_20": "ROC 20",
    "Preco_EMA50": "P > EMA50", "Preço_EMA50": "P > EMA50", "Price_EMA50": "P > EMA50",
    "EMA21_EMA50": "E21 > E50",
    "Dist_EMA21_Pct": "Dist EMA21",
    "Vol_Rel": "Vol Rel",
    "ATR_Pct": "ATR%",
    "Dist_Max20_Pct": "Dist Máx20",
}

_DEFAULT_ORDER = [
    "Ativo", "Preço", "Status", "Score", "Modos", "RSI", "RSI 3c", "ROC 10", "ROC 20",
    "P > EMA50", "E21 > E50", "Dist EMA21", "Vol Rel", "ATR%", "Dist Máx20", "Avisos",
]

_LABEL_MAP_MINI = {
    "CRYPTO_TENDENCIA_SAUDAVEL": "Tendência saudável",
    "CRYPTO_PULLBACK_DE_ALTA": "Pullback de alta",
    "CRYPTO_BREAKOUT_SETUP": "Breakout setup",
    "CRYPTO_RECUPERACAO": "Recuperação",
    "TENDENCIA_SAUDAVEL": "Tendência saudável",
    "PULLBACK_DE_ALTA": "Pullback de alta",
    "BREAKOUT_SETUP": "Breakout setup",
    "RECUPERACAO_INICIAL": "Recuperação inicial",
}


def _humanize_modes(val: str) -> str:
    if pd.isna(val) or str(val) == "None" or not val:
        return ""
    parts = str(val).split(",")
    result = []
    for p in parts:
        p = p.strip()
        if p in _LABEL_MAP_MINI:
            result.append(_LABEL_MAP_MINI[p])
        else:
            result.append(p.replace("_", " ").title())
    return ", ".join(result)


def clean_radar_table(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    out = df.copy()

    for old, new in _COLUMN_DISPLAY_NAMES.items():
        if old in out.columns and old != new:
            out.rename(columns={old: new}, inplace=True)

    for col in out.columns:
        is_bool = out[col].dtype == bool
        if not is_bool:
            out[col] = out[col].apply(lambda v: "" if pd.isna(v) or str(v) == "None" else v)

    if "Modos" in out.columns:
        out["Modos"] = out["Modos"].apply(_humanize_modes)
    if "Avisos" in out.columns:
        out["Avisos"] = out["Avisos"].apply(lambda w: "" if not w or str(w) == "None" else str(w))

    ordered = [c for c in _DEFAULT_ORDER if c in out.columns]
    remaining = [c for c in out.columns if c not in ordered]
    out = out[ordered + remaining]

    return out

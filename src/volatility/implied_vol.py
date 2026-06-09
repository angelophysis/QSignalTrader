from __future__ import annotations

import time

import requests

from src.volatility.volatility_config import (
    DVOL_LOOKBACK_DAYS,
    DVOL_MA_20,
    DVOL_MA_50,
    DVOL_SLOPE_3,
    DVOL_SLOPE_7,
    IV_RANK_WINDOW,
)

DERIBIT_BASE = "https://www.deribit.com/api/v2/public"


def buscar_dvol_btc() -> dict:
    result = {
        "dvol": None, "dvol_ma20": None, "dvol_ma50": None,
        "dvol_slope_3": None, "dvol_slope_7": None,
        "iv_rank": None, "iv_percentile": None,
        "iv_rv_ratio": None, "term_structure": None, "skew": None,
        "fallback": False, "error": None,
    }

    try:
        now_ms = int(time.time() * 1000)
        start_ms = now_ms - DVOL_LOOKBACK_DAYS * 24 * 3600 * 1000

        url = (
            f"{DERIBIT_BASE}/get_volatility_index_data"
            f"?currency=BTC&resolution=1D"
            f"&start_timestamp={start_ms}&end_timestamp={now_ms}"
        )
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()

        data = resp.json()
        records = data.get("result", {}).get("data", [])

        if not records:
            result["fallback"] = True
            result["error"] = "Deribit retornou histórico vazio"
            return result

        values = []
        for r in records:
            if isinstance(r, list) and len(r) >= 2:
                try:
                    values.append(float(r[1]))
                except (ValueError, TypeError):
                    continue
            elif isinstance(r, dict):
                v = r.get("volatility")
                if v is not None:
                    values.append(float(v))

        if not values:
            result["fallback"] = True
            result["error"] = "Sem valores de volatilidade no retorno"
            return result

        result["dvol"] = values[-1]

        if len(values) >= DVOL_MA_20:
            result["dvol_ma20"] = round(sum(values[-DVOL_MA_20:]) / DVOL_MA_20, 2)

        if len(values) >= DVOL_MA_50:
            result["dvol_ma50"] = round(sum(values[-DVOL_MA_50:]) / DVOL_MA_50, 2)

        if len(values) >= DVOL_SLOPE_3 + 1:
            result["dvol_slope_3"] = round(values[-1] - values[-1 - DVOL_SLOPE_3], 2)

        if len(values) >= DVOL_SLOPE_7 + 1:
            result["dvol_slope_7"] = round(values[-1] - values[-1 - DVOL_SLOPE_7], 2)

        if len(values) >= 10:
            dvol_min = min(values)
            dvol_max = max(values)
            if dvol_max > dvol_min:
                result["iv_rank"] = round((values[-1] - dvol_min) / (dvol_max - dvol_min) * 100, 1)

            below_count = sum(1 for v in values if v < values[-1])
            result["iv_percentile"] = round(below_count / len(values) * 100, 1)

        return result

    except requests.RequestException as e:
        result["fallback"] = True
        result["error"] = f"Erro ao acessar Deribit: {e}"
        return result
    except Exception as e:
        result["fallback"] = True
        result["error"] = f"Erro inesperado: {e}"
        return result


def calcular_metricas_iv(realized_metrics: dict) -> dict:
    dvol_data = buscar_dvol_btc()

    rv30 = realized_metrics.get("rv30")
    dvol = dvol_data.get("dvol")
    if dvol is not None and rv30 is not None and rv30 > 0:
        rv30_percent = rv30 * 100
        dvol_data["iv_rv_ratio"] = round(dvol / rv30_percent, 4)

    return dvol_data

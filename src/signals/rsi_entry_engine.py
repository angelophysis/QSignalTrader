from __future__ import annotations


def classificar_rsi_entrada(rsi: float | None) -> dict:
    if rsi is None:
        return {"estado": "indisponivel", "mensagem": "RSI indisponível", "emoji": "⚪"}

    if rsi < 56:
        return {"estado": "forca_insuficiente", "mensagem": "Força insuficiente para entrada comprada", "emoji": "⚪"}
    if 56 <= rsi <= 66:
        return {"estado": "zona_ideal", "mensagem": "Zona ideal de força compradora", "emoji": "✅"}
    return {"estado": "esticado", "mensagem": "Movimento esticado; aguardar correção", "emoji": "⚠️"}


def analisar_rsi_por_timeframe(timeframes: dict, tipo: str) -> dict:
    if tipo == "cripto":
        principal_tf = "4h"
        pesos = {"15m": "secundario", "1h": "secundario", "4h": "principal", "1D": "macro", "1W": "macro"}
        tf_order = ["15m", "1h", "4h", "1D", "1W"]
    else:
        principal_tf = "1d"
        pesos = {"1d": "principal", "5d": "secundario", "1wk": "macro"}
        tf_order = ["1d", "5d", "1wk"]

    result_tfs = {}
    principal_rsi = None
    principal_estado = None

    for tf in tf_order:
        tf_data = timeframes.get(tf, {})
        rsi = tf_data.get("rsi") if isinstance(tf_data, dict) else None
        classification = classificar_rsi_entrada(rsi)
        result_tfs[tf] = {
            "rsi": rsi,
            "estado": classification["estado"],
            "mensagem": classification["mensagem"],
            "peso": pesos.get(tf, "secundario"),
        }
        if tf == principal_tf:
            principal_rsi = rsi
            principal_estado = classification["estado"]

    principal_emoji = classificar_rsi_entrada(principal_rsi)["emoji"]
    principal_mensagem = (
        f"{principal_emoji} RSI principal ({principal_tf}) em {classificar_rsi_entrada(principal_rsi)['mensagem'].lower()}"
        if principal_rsi is not None
        else "⚪ RSI principal indisponível"
    )

    return {
        "principal_timeframe": principal_tf,
        "principal_rsi": principal_rsi,
        "principal_estado": principal_estado,
        "principal_mensagem": principal_mensagem,
        "timeframes": result_tfs,
    }

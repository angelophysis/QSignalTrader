from __future__ import annotations

from pathlib import Path

import jinja2
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.signals.logger import carregar_historico, carregar_historico_volatilidade
from src.signals.signal_engine import gerar_analise_btc_completa, gerar_analise_completa

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="QSignalTrader")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(BASE_DIR / "templates")))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    template = jinja_env.get_template("index.html")
    html = template.render({"request": request})
    return HTMLResponse(content=html)


@app.get("/api/analise-completa")
async def api_analise_completa(symbol: str = Query(...)):
    symbol = _normalizar_symbol(symbol)
    try:
        result = gerar_analise_completa(symbol)
        return {"ok": True, **result}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": f"Erro na analise completa de {symbol}: {str(e)}"},
        )


@app.get("/api/sinal")
async def api_sinal(symbol: str = Query(...)):
    symbol = _normalizar_symbol(symbol)
    try:
        result = gerar_analise_completa(symbol)
        return {"ok": True, **result}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": f"Erro ao analisar {symbol}: {str(e)}"},
        )


@app.get("/api/historico")
async def api_historico(
    limit: int = Query(default=25, ge=1, le=100),
    ativo: str | None = Query(default=None),
    tipo: str | None = Query(default=None),
):
    try:
        return carregar_historico(limit=limit, ativo=ativo, tipo=tipo)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": f"Erro ao carregar historico: {e}"},
        )


@app.get("/api/btc/volatilidade")
async def api_btc_volatilidade():
    try:
        result = gerar_analise_btc_completa()
        return {"ok": True, **result["volatilidade"]}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": f"Erro ao analisar volatilidade BTC: {str(e)}"},
        )


@app.get("/api/btc/analise-completa")
async def api_btc_analise_completa():
    try:
        result = gerar_analise_btc_completa()
        return {"ok": True, **result}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": f"Erro na analise completa BTC: {str(e)}"},
        )


@app.get("/api/btc/historico-volatilidade")
async def api_btc_historico_vol(limit: int = Query(default=25, ge=1, le=100)):
    try:
        return carregar_historico_volatilidade(limit=limit)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": f"Erro ao carregar historico volatilidade: {e}"},
        )


@app.get("/api/radar/cripto")
async def api_radar_cripto(force: bool = Query(default=False)):
    try:
        from src.signals.radar_engine import executar_radar
        result = executar_radar("cripto", force=force)
        return {"ok": True, **result}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": f"Erro no Radar Cripto: {str(e)}"},
        )


@app.get("/api/radar/acoes")
async def api_radar_acoes(force: bool = Query(default=False)):
    try:
        from src.signals.radar_engine import executar_radar
        result = executar_radar("acoes", force=force)
        return {"ok": True, **result}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": f"Erro no Radar Acoes: {str(e)}"},
        )


def _normalizar_symbol(symbol: str) -> str:
    s = symbol.strip().upper()
    if "/" not in s:
        known_pairs = {
            "BTCUSDT": "BTC/USDT", "ETHUSDT": "ETH/USDT",
            "SOLUSDT": "SOL/USDT", "BNBUSDT": "BNB/USDT",
            "ADAUSDT": "ADA/USDT", "XRPUSDT": "XRP/USDT",
            "DOGEUSDT": "DOGE/USDT",
        }
        if s in known_pairs:
            return known_pairs[s]
    return s

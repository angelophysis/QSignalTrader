from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
DB_PATH = DB_DIR / "sinais.db"


def _get_connection() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sinais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            ativo TEXT NOT NULL,
            tipo TEXT NOT NULL,
            interpretacao TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS volatilidade_btc (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            symbol TEXT NOT NULL,
            regime TEXT,
            score_expansao INTEGER,
            score_contracao INTEGER,
            atr_percent REAL,
            bandwidth_percentile REAL,
            rv7 REAL,
            rv30 REAL,
            rv90 REAL,
            dvol REAL,
            iv_rank REAL,
            iv_percentile REAL,
            iv_rv_ratio REAL,
            leitura TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS estado_direcional (
            ativo TEXT PRIMARY KEY,
            timeframes_alta TEXT,
            timeframes_baixa TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    return conn


def salvar_sinal(ativo: str, tipo: str, interpretacao: str) -> None:
    conn = _get_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO sinais (timestamp, ativo, tipo, interpretacao) VALUES (?, ?, ?, ?)",
        (now, ativo, tipo, interpretacao),
    )
    conn.commit()
    conn.close()


def carregar_historico(
    limit: int = 25, ativo: str | None = None, tipo: str | None = None
) -> list[dict]:
    conn = _get_connection()
    query = "SELECT id, timestamp, ativo, tipo, interpretacao FROM sinais WHERE 1=1"
    params: list = []

    if ativo:
        query += " AND ativo = ?"
        params.append(ativo)
    if tipo:
        query += " AND tipo = ?"
        params.append(tipo)

    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "timestamp": r[1],
            "ativo": r[2],
            "tipo": r[3],
            "interpretacao": r[4],
        }
        for r in rows
    ]


def salvar_volatilidade_btc(vol_data: dict) -> None:
    conn = _get_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    r = vol_data.get("metricas_realizadas", {})
    i = vol_data.get("metricas_implicitas", {})

    conn.execute(
        """INSERT INTO volatilidade_btc
           (timestamp, symbol, regime, score_expansao, score_contracao,
            atr_percent, bandwidth_percentile, rv7, rv30, rv90,
            dvol, iv_rank, iv_percentile, iv_rv_ratio, leitura)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            now,
            vol_data.get("symbol", "BTC/USDT"),
            vol_data.get("regime"),
            vol_data.get("score_expansao"),
            vol_data.get("score_contracao"),
            r.get("atr_percent"),
            r.get("bandwidth_percentile"),
            r.get("rv7"),
            r.get("rv30"),
            r.get("rv90"),
            i.get("dvol"),
            i.get("iv_rank"),
            i.get("iv_percentile"),
            i.get("iv_rv_ratio"),
            vol_data.get("leitura"),
        ),
    )
    conn.commit()
    conn.close()


def carregar_historico_volatilidade(limit: int = 25) -> list[dict]:
    conn = _get_connection()
    rows = conn.execute(
        """SELECT id, timestamp, symbol, regime, score_expansao, score_contracao,
           atr_percent, bandwidth_percentile, rv7, rv30, rv90,
           dvol, iv_rank, iv_percentile, iv_rv_ratio, leitura
           FROM volatilidade_btc ORDER BY id DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()

    return [
        {
            "id": r[0], "timestamp": r[1], "symbol": r[2], "regime": r[3],
            "score_expansao": r[4], "score_contracao": r[5],
            "atr_percent": r[6], "bandwidth_percentile": r[7],
            "rv7": r[8], "rv30": r[9], "rv90": r[10],
            "dvol": r[11], "iv_rank": r[12], "iv_percentile": r[13],
            "iv_rv_ratio": r[14], "leitura": r[15],
        }
        for r in rows
    ]


def salvar_estado_direcional(ativo: str, alta_set: set, baixa_set: set) -> None:
    conn = _get_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    alta_json = json.dumps(sorted(alta_set)) if alta_set else "[]"
    baixa_json = json.dumps(sorted(baixa_set)) if baixa_set else "[]"
    conn.execute(
        """INSERT OR REPLACE INTO estado_direcional (ativo, timeframes_alta, timeframes_baixa, timestamp)
           VALUES (?, ?, ?, ?)""",
        (ativo, alta_json, baixa_json, now),
    )
    conn.commit()
    conn.close()


def carregar_estado_direcional(ativo: str) -> tuple[set, set]:
    conn = _get_connection()
    row = conn.execute(
        "SELECT timeframes_alta, timeframes_baixa FROM estado_direcional WHERE ativo = ?",
        (ativo,),
    ).fetchone()
    conn.close()
    if row and row[0] and row[1]:
        try:
            alta_set = set(json.loads(row[0]))
            baixa_set = set(json.loads(row[1]))
            return alta_set, baixa_set
        except (json.JSONDecodeError, TypeError):
            pass
    return set(), set()

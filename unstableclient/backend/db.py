from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

from .config import ensure_base_dirs


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "storage" / "schema.sql"


def get_db_path() -> Path:
    paths = ensure_base_dirs()
    return paths["base"] / "app.db"


def connect() -> sqlite3.Connection:
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with connect() as conn:
        conn.executescript(schema)
        _ensure_columns(conn)


def _ensure_columns(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
    if "is_active" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
    if "profile_description" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN profile_description TEXT NOT NULL DEFAULT ''")


def fetch_one(query: str, params: Iterable[Any] = ()) -> Dict[str, Any] | None:
    with connect() as conn:
        cur = conn.execute(query, params)
        row = cur.fetchone()
        return dict(row) if row else None


def fetch_all(query: str, params: Iterable[Any] = ()) -> list[Dict[str, Any]]:
    with connect() as conn:
        cur = conn.execute(query, params)
        rows = cur.fetchall()
        return [dict(row) for row in rows]


def execute(query: str, params: Iterable[Any] = ()) -> int:
    with connect() as conn:
        cur = conn.execute(query, params)
        conn.commit()
        return cur.lastrowid


def executemany(query: str, params: Iterable[Tuple[Any, ...]]) -> None:
    with connect() as conn:
        conn.executemany(query, params)
        conn.commit()

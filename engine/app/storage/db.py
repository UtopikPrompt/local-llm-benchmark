"""SQLite persistence layer for benchmark run results."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

# Columns that SQLite derives automatically. They must not be supplied
# explicitly to write_row(); attempting to do so is a programming error.
_GENERATED_COLUMNS: set[str] = {"throughput_toks_s"}

_CREATE_RESULTS_TABLE = """
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model TEXT NOT NULL,
    status TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    latency_s REAL NOT NULL,
    throughput_toks_s REAL AS (output_tokens / latency_s) STORED
)
"""


def init_db(db_path: str | Path) -> None:
    """Create the ``results`` table if it does not already exist."""
    path = Path(db_path)
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)
    try:
        conn.execute(_CREATE_RESULTS_TABLE)
        conn.commit()
    finally:
        conn.close()


def write_row(db_path: str | Path, **columns: Any) -> int:
    """Insert a single run into ``results`` and return its row id.

    Generated columns (e.g. ``throughput_toks_s``) must not be supplied
    explicitly; SQLite derives them from latency and output tokens.
    """
    if not columns:
        raise ValueError("write_row() requires at least one column value")

    illegal = _GENERATED_COLUMNS.intersection(columns)
    if illegal:
        raise ValueError(
            "cannot supply generated column(s) explicitly: "
            + ", ".join(sorted(illegal))
        )

    names = tuple(columns)
    placeholders = ", ".join("?" for _ in names)
    quoted = ", ".join(f'"{name}"' for name in names)
    sql = f"INSERT INTO results ({quoted}) VALUES ({placeholders})"

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(sql, tuple(columns[name] for name in names))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def read_rows(
    db_path: str | Path,
    where: str = "",
    params: tuple[Any, ...] = (),
) -> list[dict[str, Any]]:
    """Return result rows as a list of dictionaries."""
    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        sql = "SELECT * FROM results"
        args: list[Any] = []
        if where:
            sql += f" WHERE {where}"
            args.extend(params)
        return [dict(row) for row in conn.execute(sql, args)]
    finally:
        conn.close()
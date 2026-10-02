"""SQLite-backed persistence layer for benchmark runs."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Union

import sqlite3


SCHEMA_SQL: str = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    model TEXT NOT NULL,
    dataset TEXT NOT NULL,
    total_tokens INTEGER NOT NULL,
    duration_seconds REAL NOT NULL,
    tokens_per_second REAL NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def _connect(db_path: Union[str, Path]) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Union[str, Path]) -> sqlite3.Connection:
    conn = _connect(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn


def write_run(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    model: str,
    dataset: str,
    total_tokens: int,
    duration_seconds: float,
    status: str = "completed",
) -> int:
    if duration_seconds > 0:
        throughput = total_tokens / duration_seconds
    else:
        throughput = 0.0

    cursor = conn.execute(
        """
        INSERT INTO runs (
            run_id,
            model,
            dataset,
            total_tokens,
            duration_seconds,
            tokens_per_second,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            model,
            dataset,
            total_tokens,
            duration_seconds,
            throughput,
            status,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    return cursor.lastrowid


def read_all_runs(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    cursor = conn.execute(
        """
        SELECT * FROM runs ORDER BY id
        """
    )
    return [dict(row) for row in cursor.fetchall()]
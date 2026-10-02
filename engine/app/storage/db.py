"""SQLite storage layer for the benchmark backend."""

from __future__ import annotations

import sqlite3
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    engine TEXT,
    model_id TEXT,
    scenario TEXT
);
"""


def get_connection(database_path: str) -> sqlite3.Connection:
    """Return a :class:`sqlite3.Connection` to ``database_path``.

    ``":memory:"` yields an in-process database (used by tests); a file path
    yields a persistent database on disk.
    """
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(database_path: str) -> None:
    """Create the schema if it does not already exist."""
    conn = get_connection(database_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def connection_pool(database_path: str) -> Iterator[sqlite3.Connection]:
    """Yield a fresh connection per caller.

    SQLite serializes writes, so opening a connection per operation keeps the
    benchmark writer simple and avoids sharing a connection across threads.
    """
    conn = get_connection(database_path)
    try:
        yield conn
    finally:
        conn.close()

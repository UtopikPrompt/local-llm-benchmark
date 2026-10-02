from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.storage.db import (
    RunResult,
    init_db,
    read_all,
    read_row,
    write_row,
)

EXPECTED_COLUMNS = {
    "id",
    "run_id",
    "model",
    "tokenizer",
    "created_at",
    "prompt_tokens",
    "output_tokens",
    "latency",
    "ttfb",
    "throughput_toks_s",
    "system_prompt",
    "seed",
    "temperature",
    "max_tokens",
}


def _table_columns(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("PRAGMA table_info(results)").fetchall()
    return {row["name"] for row in rows}


def test_init_db_creates_schema_with_all_columns(tmp_path: Path) -> None:
    conn = init_db(tmp_path / "runs.db")
    try:
        assert EXPECTED_COLUMNS.issubset(_table_columns(conn))
    finally:
        conn.close()


def test_write_row_roundtrip_and_computed_throughput(tmp_path: Path) -> None:
    conn = init_db(tmp_path / "runs.db")
    try:
        result = RunResult(
            run_id="run-abc",
            model="sample-model",
            tokenizer="sample-tok",
            prompt_tokens=250,
            output_tokens=500,
            latency=2.0,
            ttfb=0.05,
            system_prompt="You are a helpful assistant.",
            seed=123,
            temperature=0.7,
            max_tokens=128,
        )
        row_id = write_row(conn, result)
        assert row_id > 0

        stored = read_row(conn, row_id)
        assert stored is not None
        assert stored.run_id == "run-abc"
        assert stored.model == "sample-model"
        assert stored.tokenizer == "sample-tok"
        assert stored.prompt_tokens == 250
        assert stored.output_tokens == 500
        assert stored.latency == 2.0
        assert stored.ttfb == 0.05

        expected = result.output_tokens / result.latency
        computed = conn.execute(
            "SELECT throughput_toks_s FROM results WHERE id = ?", (row_id,)
        ).fetchone()[0]
        assert computed == pytest.approx(expected)
    finally:
        conn.close()


def test_read_all_returns_persisted_rows_in_order(tmp_path: Path) -> None:
    conn = init_db(tmp_path / "runs.db")
    try:
        write_row(
            conn,
            RunResult(run_id="r1", model="m1", tokenizer="t1",
                      prompt_tokens=10, output_tokens=20, latency=1.0),
        )
        write_row(
            conn,
            RunResult(run_id="r2", model="m2", tokenizer="t2",
                      prompt_tokens=30, output_tokens=60, latency=3.0),
        )
        rows = read_all(conn)
        assert [r.run_id for r in rows] == ["r1", "r2"]
        row2_tput = conn.execute(
            "SELECT throughput_toks_s FROM results WHERE run_id = 'r2'"
        ).fetchone()[0]
        assert row2_tput == pytest.approx(20.0)
    finally:
        conn.close()
"""Tests for the SQLite storage layer (slice 3)."""
import sqlite3
from pathlib import Path

import pytest

from engine.app.storage import db as storage

EXPECTED_COLUMNS = {
    "id",
    "run_at",
    "model",
    "status",
    "input_tokens",
    "output_tokens",
    "latency_s",
    "throughput_toks_s",
    "prompt",
    "response",
}


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "runs.db"
    storage.init_db(path)
    return path


def test_init_db_creates_results_table_with_every_column(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("PRAGMA table_info(results)")
    columns = {row[1] for row in cursor.fetchall()}
    conn.close()
    assert EXPECTED_COLUMNS <= columns


def test_init_db_results_table_present(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    )
    names = {row[0] for row in cursor.fetchall()}
    conn.close()
    assert "results" in names


def test_write_row_returns_positive_row_id(db_path):
    row_id = storage.write_row(
        db_path,
        model="gpt-4",
        status="ok",
        input_tokens=100,
        output_tokens=200,
        latency_s=4.0,
    )
    assert isinstance(row_id, int)
    assert row_id > 0


def test_round_trip_and_computed_throughput(db_path):
    row_id = storage.write_row(
        db_path,
        model="gpt-4",
        status="ok",
        input_tokens=100,
        output_tokens=200,
        latency_s=4.0,
    )

    row = storage.get_row(db_path, row_id)
    assert row is not None
    assert row["model"] == "gpt-4"
    assert row["input_tokens"] == 100
    assert row["output_tokens"] == 200
    assert row["status"] == "ok"
    assert row["latency_s"] == pytest.approx(4.0)
    # throughput_toks_s derives from output_tokens / latency_s
    assert row["throughput_toks_s"] == pytest.approx(50.0)


def test_computed_throughput_rejects_explicit_value(db_path):
    with pytest.raises(ValueError):
        storage.write_row(
            db_path,
            model="x",
            status="ok",
            input_tokens=1,
            output_tokens=1,
            latency_s=1.0,
            throughput_toks_s=1.0,
        )
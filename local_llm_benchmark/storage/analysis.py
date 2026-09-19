"""Analysis module (ADR-005, ADR-019).

Runs read-only DuckDB queries over a single run's Parquet file. Results are
pandas-free: every query returns a list of plain dicts. The public entry point
is :func:`analyze`, which executes a fixed set of descriptive queries and
returns them grouped under stable keys.

Example:
    >>> results = analysis.analyze("/path/to/run.parquet")
    >>> results["token_distribution"]  # sorted list of {token_id, cumulative}
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import duckdb

from local_llm_benchmark.errors import BenchmarkError, ConfigurationError
from local_llm_benchmark.storage import TOKEN_COLUMNS

# ADF-friendly query keys.
KEYS = (
    "token_distribution",
    "ttft",
    "throughput",
    "token_volume",
    "token_frequency",
)


def _query(name: str, sql: str) -> List[dict]:
    """Execute a single query and return its rows as a list of dicts."""
    conn = duckdb.connect()
    try:
        rows = conn.execute(sql).fetchall()
        columns = [d[0] for d in conn.description]
        return [dict(zip(columns, row)) for row in rows]
    finally:
        conn.close()


def _token_distribution(tokens: List[dict]) -> List[dict]:
    """Return each token's cumulative length (id -> length)."""
    return [
        {"token_id": t[TOKEN_COLUMNS["token_id"]], "cumulative": t[TOKEN_COLUMNS["cumulative"]]}
        for t in tokens
    ]


def _ttft(metadata: dict) -> List[dict]:
    return [{"ttft": metadata.get("ttft")}]


def _throughput(metadata: dict) -> List[dict]:
    return [{"tokens_per_sec": metadata.get("tokens_per_sec")}]


def _token_volume(tokens: List[dict]) -> List[dict]:
    total = sum(t[TOKEN_COLUMNS["cumulative"]] for t in tokens)
    return [{"num_tokens": total}]


def _token_frequency(tokens: List[dict]) -> List[dict]:
    """Return the top tokens by frequency, using the prompt text as a proxy.

    The prompt column carries the delta of every token, so counting prompt
    text occurrences gives a reasonable frequency estimate without per-token
    id lookups.
    """
    freq = {}
    for t in tokens:
        text = t.get("prompt")
        if text:
            for word in text.split():
                freq[word] = freq.get(word, 0) + 1
    ranked = sorted(freq.items(), key=lambda kv: kv[1], reverse=True)
    return [{"token": token, "frequency": count} for token, count in ranked]


def _analyze(run_path: Path) -> Dict[str, List[dict]]:
    """Execute the full analysis suite against a single run's Parquet file."""
    if not run_path.exists():
        raise ConfigurationError(f"run {run_path} not found")
    conn = duckdb.connect(str(run_path))
    try:
        tokens = conn.execute(f"SELECT * FROM read_parquet('{run_path}')").fetchall()
        columns = [d[0] for d in conn.description]
        metadata = {col: val for col, val in zip(columns, tokens[0])}
        rows = [dict(zip(columns, row)) for row in tokens]
    finally:
        conn.close()

    return {
        "token_distribution": _token_distribution(rows),
        "ttft": _ttft(metadata),
        "throughput": _throughput(metadata),
        "token_volume": _token_volume(rows),
        "token_frequency": _token_frequency(rows),
    }


def analyze(run_path: Path) -> Dict[str, List[dict]]:
    """Run the full analysis suite over a run's Parquet file.

    Parameters
    ----------
    run_path:
        Path to the run's Parquet file (one file per run, per ADR-015).

    Returns
    -------
    Dict[str, List[dict]]
        Analysis results grouped under stable keys (see :data:`KEYS`).
    """
    try:
        return _analyze(Path(run_path))
    except BenchmarkError as exc:
        raise
    except Exception as exc:  # noqa: BLE001 - surface storage errors cleanly
        raise ConfigurationError(f"failed to analyze {run_path}: {exc}") from exc

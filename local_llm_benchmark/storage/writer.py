"""Storage writer (ADR-015, ADR-019).

Persists a run as a single Parquet file holding token-level rows plus run-level
metadata columns (ADR-019). Token timings are captured during streaming and
written here; the analysis module (see storage/analysis.py) reads them back with
DuckDB.
"""

from __future__ import annotations

import datetime as _dt
from typing import Dict, List, Sequence

import pyarrow as pa
import pyarrow.parquet as pq

from ..engine import ChatCompletion, StreamingToken
from .schemas import ALL_COLUMNS, RunMetadata


def _row_for_token(token: StreamingToken, prompt: str, metadata: RunMetadata, token_id: int) -> Dict[str, object]:
    """Build one token-level row, computing delta + cumulative latency.

    StreamingToken only carries ``token`` and ``timestamp``. The writer derives
    the remaining token fields:

    * ``prompt_id`` — a stable id for the prompt (here the prompt text, since a
      single run streams one prompt per token in this phase).
    * ``delta`` — per-token latency in seconds = ``timestamp - prev`` (ADR-011).
    * ``cumulative`` — time from stream start to this token (ADR-011).
    * ``generated_at`` — UTC ISO timestamp (ADR-019).
    """
    delta = token.timestamp - prev
    prev = token.timestamp
    cumulative = 0.0 if token_id == 0 else cumulative + delta
    return {
        "prompt_id": prompt,
        "prompt": prompt,
        "token_id": token_id,
        "token": token.token,
        "delta": delta,
        "cumulative": cumulative,
        "generated_at": _timestamp(),
        **{name: metadata[name] for name in RunMetadata._fields},
    }


def _py_type(name: str):
    if name == "num_tokens":
        return pa.int64()
    if name == "max_tokens":
        return pa.int64()
    if name == "seed":
        return pa.int64()
    if name == "num_examples":
        return pa.int64()
    if name in ("delta", "cumulative", "ttft"):
        return pa.float64()
    if name == "temperature":
        return pa.float64()
    if name in ("token", "prompt", "endpoint", "run_id", "benchmark", "engine", "model"):
        return pa.string()
    return pa.string()


def write_tokens(
    tokens: Sequence[StreamingToken],
    metadata: RunMetadata,
    prompt: str,
    path: str,
    created_at: str | None = None,
) -> None:
    """Persist token-level rows with run metadata into a Parquet file.

    Every token becomes a row with its text, per-token ``delta`` and cumulative
    ``cumulative`` latency (ADR-011), plus the run-level metadata columns (ADR-019).
    A trailing synthetic row carries the run's total cumulative latency as ``delta``.
    """
    if created_at is None:
        created_at = _timestamp()

    rows: List[Dict[str, object]] = []
    token_id = 0
    prev = 0.0
    cumulative = 0.0
    for token in tokens:
        rows.append(_row_for_token(token, prompt, metadata, token_id))
        prev = token.timestamp
        token_id += 1
        cumulative += token.timestamp - prev

    metadata_row = {name: metadata[name] for name in RunMetadata._fields}
    rows.append(
        {
            "prompt_id": prompt,
            "prompt": prompt,
            "token_id": token_id,
            "token": "",
            "delta": 0.0,
            "cumulative": cumulative,
            "generated_at": created_at,
            **metadata_row,
        }
    )

    columns: Dict[str, pa.ChunkedArray] = {
        name: pa.array([row[name] for row in rows], type=_py_type(name))
        for name in ALL_COLUMNS
    }
    table = pa.table(columns)
    pq.write_table(table, path)

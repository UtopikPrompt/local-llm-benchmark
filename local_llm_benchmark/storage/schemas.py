"""Streaming storage schema (ADR-015, ADR-019).

Defines the canonical token-level + run-level schema persisted as a single
Parquet file per run. See docs/adr/ADR-019-Streaming-storage-schema.md:

    * **Token-level rows** — one row per streamed token, holding the token
      text and its timing (delta + cumulative latency).
    * **Run-level metadata columns** — engine, model, benchmark, seed,
      temperature, etc., repeated on every token row so results can be
      grouped/filtered by DuckDB (ADR-019).

The schema is expressed as plain Python type annotations and used to build a
pyarrow Table. It is intentionally simple and columnar.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

# Token-level columns. The first three identify the row's prompt; the timing
# columns are the core of offline latency analysis (ADR-011).
TOKEN_COLUMNS: Tuple[str, ...] = (
    "prompt_id",
    "prompt",
    "token_id",
    "token",
    "delta",
    "cumulative",
    "generated_at",
)

# Run-level metadata columns repeated on every token row (ADR-019).
RUN_COLUMNS: Tuple[str, ...] = (
    "run_id",
    "engine",
    "model",
    "benchmark",
    "seed",
    "temperature",
    "max_tokens",
    "created_at",
    "endpoint",
    "num_examples",
    "num_tokens",
    "ttft",
    "tokens_per_sec",
)

# All columns in canonical order: token-level first, then run-level.
ALL_COLUMNS: Tuple[str, ...] = TOKEN_COLUMNS + RUN_COLUMNS


@dataclass
class RunMetadata:
    """Run-level metadata for a completed streaming run (ADR-019)."""

    run_id: str
    engine: str
    model: str
    benchmark: str
    seed: int
    temperature: float
    max_tokens: int
    created_at: str
    endpoint: str
    num_examples: int
    num_tokens: int
    ttft: float
    tokens_per_sec: float


def schema_fields() -> List[str]:
    """Return the ordered list of all schema columns."""
    return list(ALL_COLUMNS)


def token_schema_fields() -> List[str]:
    """Return the ordered token-level columns only."""
    return list(TOKEN_COLUMNS)


def run_schema_fields() -> List[str]:
    """Return the ordered run-level metadata columns only."""
    return list(RUN_COLUMNS)

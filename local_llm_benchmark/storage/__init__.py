"""Streaming storage module (ADR-015, ADR-019).

Persists token-level + run-level metadata as a single Parquet file per run,
queryable via DuckDB. Public API:

    from local_llm_benchmark.storage import (
        ALL_COLUMNS,
        RunMetadata,
        analysis,
        retention,
        schema_fields,
        token_schema_fields,
        run_schema_fields,
        write_tokens,
    )
"""

from __future__ import annotations

from .schemas import (
    ALL_COLUMNS,
    RUN_COLUMNS,
    TOKEN_COLUMNS,
    RunMetadata,
    schema_fields,
    token_schema_fields,
    run_schema_fields,
)

from . import analysis
from . import retention

__all__ = [
    "ALL_COLUMNS",
    "RUN_COLUMNS",
    "TOKEN_COLUMNS",
    "RunMetadata",
    "schema_fields",
    "token_schema_fields",
    "run_schema_fields",
    "analysis",
    "retention",
]

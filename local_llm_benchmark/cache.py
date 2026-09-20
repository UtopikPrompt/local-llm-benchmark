"""Shared, version-keyed benchmark-run cache.

Keeps a small JSON index of completed benchmark runs (keyed by ``run_id``) and
an LRU in-memory dict for hot access. Reads and writes the SAME parquet files
the CLI writes via :mod:`local_llm_benchmark.storage.writer`, so the UI can
display raw per-run metadata and per-dimension quality scores without any
changes to the CLI (ADR-014 cache lifecycle, ADR-018 cache identity).

Version-keyed: the on-disk index and the in-memory cache are named after the
benchmark-reading API version so a future schema change cannot corrupt old
entries.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import pyarrow.parquet as pq

from local_llm_benchmark import config
from local_llm_benchmark.cli import BenchmarkRun
from local_llm_benchmark.storage.schemas import RUN_COLUMNS, RUN_METADATA_COLUMNS
from local_llm_benchmark.quality import Aggregator, DIMENSIONS
import pyarrow.parquet as pq

# Bump when the shape of the persisted entries or the in-memory value changes.
CACHE_VERSION = 1
# In-memory LRU ceiling (ADR-014: bounded cache).
_MAX_ENTRIES = 256

# LRU bookkeeping for in-memory access tracking.
_STATE: Dict[str, Dict[str, float]] = {}

# Run-metadata columns exposed by the cache (a subset of RUN_COLUMNS).
_METADATA_COLUMNS = [
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
]


def _index_path() -> Path:
    return Path(config.cache_dir()) / f"cache.v{CACHE_VERSION}.json"


def cache_version() -> int:
    """Return the cache schema version."""
    return CACHE_VERSION


def cache_dir() -> Path:
    """Absolute path to the on-disk cache directory."""
    return Path(config.cache_dir())


def results_dir() -> Path:
    """Absolute path to the directory holding run parquet files."""
    return Path(config.results_dir())


def _load_index() -> Dict[str, Any]:
    """Load the JSON index, returning an empty index when it is missing/corrupt."""
    path = _index_path()
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
            if isinstance(data, dict) and "entries" in data:
                return data["entries"]
            # Backwards-compatible: bare object is treated as the entries map.
            if isinstance(data, dict):
                return data
            return {}
    except (json.JSONDecodeError, OSError, ValueError):
        return {}


def _save_index(index: Dict[str, Any]) -> None:
    cache_dir().mkdir(parents=True, exist_ok=True)
    with _index_path().open("w", encoding="utf-8") as fh:
        json.dump({"version": CACHE_VERSION, "entries": index}, fh, indent=2)


def _scan_parquet_files() -> List[Path]:
    """Return sorted parquet paths in the results directory."""
    results = results_dir()
    if not results.exists():
        return []
    return sorted(results.glob("*.parquet"))


def _index_parquet_files() -> Dict[str, Any]:
    """Read every run parquet file and build the metadata index map."""
    entries: Dict[str, Any] = {}
    for run_path in _scan_parquet_files():
        try:
            data = pq.read_table(run_path).to_pydict()
            run = BenchmarkRun(**{k: data[k][0] for k in asdict(BenchmarkRun).__fields__})
            entries[run.run_id] = {
                "meta": asdict(run),
                "path": str(run_path),
                "quality_columns": [
                    col for col in data.keys() if col not in _METADATA_COLUMNS
                ],
            }
        except Exception:  # pragma: no cover - defensive; skip unreadable files
            continue
    return entries


def _load() -> Dict[str, Any]:
    """Merge persisted index with freshly-scanned parquet metadata."""
    # Keep the persisted index but overwrite each entry's metadata with what the
    # parquet files actually contain (single source of truth = the parquet file).
    persisted = _load_index()
    for run_id, entry in persisted.items():
        if run_id in entries:
            entries[run_id]["meta"] = entries[run_id]["meta"]
            persisted[run_id] = entries[run_id]
    return entries


def get(run_id_or_key: str) -> Optional[Dict[str, Any]]:
    """Return the cached entry for ``run_id_or_key`` or ``None``.

    The key is the ``run_id`` (``engine:model@benchmark/seedN/tT/TS``) or any
    substring of it. Returns a dict with ``meta`` (run metadata), ``path`` and
    ``quality_columns``.
    """
    entries = _load()
    for key, entry in entries.items():
        if run_id_or_key in key:
            _touch(key, entry)
            return entry
    return None


def get_scores(run_id_or_key: str) -> Dict[str, float]:
    """Return raw per-dimension scores for the run matching ``run_id_or_key``.

    Reads quality columns (if present) from the run's Parquet file and aggregates
    them into a flat ``{dimension: score}`` mapping. Returns an empty mapping when
    no quality columns are present (ADR-020 deferral).
    """
    entry = get(run_id_or_key)
    return _aggregate_scores(entry)


def _aggregate_scores(entry: Optional[Dict[str, Any]]) -> Dict[str, float]:
    """Aggregate quality columns from the run entry into per-dimension scores.

    Reads any ``quality_columns`` column-name list present in the entry, and
    aggregates the values via :class:`Aggregator`. Returns an empty mapping when
    no quality columns are present (quality scoring is DEFERRED, ADR-020).
    """
    if not entry:
        return {}
    columns = entry.get("quality_columns")
    if not columns:
        return {}
    path = entry.get("path")
    if not path:
        return {}
    try:
        table = pq.read_table(path)
    except Exception:
        return {}
    values = {c: table.column(c).to_pylist() for c in columns}
    aggregator = Aggregator(dimensions=DIMENSIONS)
    for row in zip(*[values[c] for c in columns]):
        row = {c: v for c, v in zip(columns, row)}
        for dimension in DIMENSIONS:
            name = dimension.name
            if name not in row:
                continue
            try:
                aggregator.scores[name].append(float(row[name]))
            except (TypeError, ValueError):
                pass
    return {name: sum(scores) / len(scores) for name, scores in aggregator.scores.items()}


def has(run_id_or_key: str) -> bool:
    """Return ``True`` if ``run_id_or_key`` matches any known run."""
    entries = _load()
    return any(run_id_or_key in key for key in entries)


def invalidate(run_id_or_key: str) -> int:
    """Remove every entry matching ``run_id_or_key``. Returns the count removed."""
    entries = _load()
    if not entries:
        return 0
    to_remove = [key for key in entries if run_id_or_key in key]
    if to_remove:
        for key in to_remove:
            entries.pop(key, None)
        _save_index(entries)
        _prune()
    return len(to_remove)


def list() -> List[str]:
    """Return the sorted list of known run ids."""
    entries = _load()
    return sorted(entries.keys())


def all() -> Dict[str, Any]:
    """Return a copy of the full entry map (meta + path + quality_columns)."""
    return {key: dict(value) for key, value in _load().items()}


def _prune() -> None:
    """Evict in-memory entries by LRU / age policy and persist the trimmed set."""
    entries = _load()
    # Evict by age (oldest first) then by least-recently-used.
    entries = sorted(
        entries.values(),
        key=lambda e: (e.get("last_access", 0.0), e.get("last_used", 0.0)),
    )
    while len(entries) > _MAX_ENTRIES:
        entries.popitem()
    _save_index(entries)


def _touch(key: str, entry: Dict[str, Any]) -> None:
    """Record access time for the LRU policy (best-effort, no side effects)."""
    state = _STATE.get(key)
    if state is None:
        state = {"last_access": 0.0, "last_used": 0.0, "count": 0}
    state["last_access"] = time.time()
    state["last_used"] = time.time()
    state["count"] += 1
    _STATE[key] = state

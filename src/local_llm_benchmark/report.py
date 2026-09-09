"""Aggregate benchmark results into CSV/JSON reports and print a summary.

The report keeps the columns required by the spec: ``engine``, ``model``,
``judge``, ``task_id``, ``category``, ``ttft_s``, ``tok_per_s``, ``iters_per_s``,
``quality_passed``, ``quality_deterministic``, ``quality_judge``, ``quality_note``.
Both the CSV and JSON outputs include a ``judge`` column/field.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, List, Sequence

from local_llm_benchmark.results import CSV_COLUMNS, Row


def write_csv(rows: Sequence[Row], path: str) -> None:
    """Write *rows* to *path* as CSV."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_dict())


def write_json(rows: Sequence[Row], path: str) -> None:
    """Write *rows* to *path* as JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump([row.to_dict() for row in rows], handle, indent=2)


def write_report(rows: Sequence[Row], path: str, *, fmt: str = "json") -> None:
    """Write *rows* to *path* in the requested *fmt* (``"csv"`` or ``"json"``)."""
    if fmt == "csv":
        write_csv(rows, path)
    else:
        write_json(rows, path)


def print_summary(rows: Iterable[Row]) -> None:
    """Print a human-readable summary of *rows*."""
    rows = list(rows)
    if not rows:
        print("No results to summarize.")
        return

    engines = sorted({row.engine for row in rows})
    models = sorted({row.model for row in rows})
    judges = sorted({row.judge for row in rows if row.judge})
    categories = sorted({row.category for row in rows})

    print("Benchmark summary")
    print("=" * 60)
    print(f"engines:      {engines}")
    print(f"models:       {models}")
    print(f"judges:       {judges or 'none'}")
    print(f"categories:   {categories}")
    print(f"rows:         {len(rows)}")

    passed = sum(1 for row in rows if row.quality_passed)
    deterministic = sum(1 for row in rows if row.quality_deterministic)
    print(f"quality_passed:   {passed}/{len(rows)}")
    print(f"deterministic:    {deterministic}/{len(rows)}")

    print("\nPer-engine throughput (tok/s):")
    for engine in engines:
        rows_for_engine = [row for row in rows if row.engine == engine]
        if rows_for_engine:
            best = max(row.tok_per_s for row in rows_for_engine)
            worst = min(row.tok_per_s for row in rows_for_engine)
            print(f"  {engine}: {worst:.1f} .. {best:.1f} tok/s")

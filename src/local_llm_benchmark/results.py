"""Benchmark result rows.

A :class:`Row` is the unit of output produced by the benchmark: one
measurement for a single (engine, task) pair. The report module serializes
rows, and the runner aggregates them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class Row:
    """A single benchmark measurement.

    Attributes:
        engine: Name of the engine under test.
        model: Model served by the engine.
        judge: Name of the judge used (empty when none).
        task_id: Identifier of the task run.
        category: Task category (``doc``, ``code``, ``qa``, ``math``).
        prompt: The task prompt.
        expected: Expected substring (if any).
        output: The model's generated answer.
        ttft_s: Time-to-first-token in seconds.
        tok_per_s: Tokens per second.
        iters_per_s: Iterations (requests) per second.
        quality_passed: ``True`` if the answer passed quality checks.
        quality_deterministic: ``True`` if a deterministic check passed.
        quality_judge: ``True`` if the judge agreed.
        quality_note: Human-readable note (e.g. reason for a failure).
    """

    engine: str
    model: str
    judge: str = ""
    task_id: str = ""
    category: str = "qa"
    prompt: str = ""
    expected: str = ""
    output: str = ""
    ttft_s: float = 0.0
    tok_per_s: float = 0.0
    iters_per_s: float = 0.0
    quality_passed: bool = False
    quality_deterministic: bool = False
    quality_judge: bool = False
    quality_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the row to a plain mapping (includes a ``judge`` field)."""
        return {
            "engine": self.engine,
            "model": self.model,
            "judge": self.judge,
            "task_id": self.task_id,
            "category": self.category,
            "prompt": self.prompt,
            "expected": self.expected,
            "output": self.output,
            "ttft_s": self.ttft_s,
            "tok_per_s": self.tok_per_s,
            "iters_per_s": self.iters_per_s,
            "quality_passed": self.quality_passed,
            "quality_deterministic": self.quality_deterministic,
            "quality_judge": self.quality_judge,
            "quality_note": self.quality_note,
        }


#: Columns, in order, of the CSV report. Includes a ``judge`` column.
CSV_COLUMNS: tuple[str, ...] = (
    "engine",
    "model",
    "judge",
    "task_id",
    "category",
    "ttft_s",
    "tok_per_s",
    "iters_per_s",
    "quality_passed",
    "quality_deterministic",
    "quality_judge",
    "quality_note",
)

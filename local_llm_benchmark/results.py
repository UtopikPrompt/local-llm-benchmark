"""Benchmark result rows.

A :class:`Row` is the unit of output produced by the benchmark: one
measurement for a single (engine, task) pair. The report module serializes
rows, and the runner aggregates them.
"""

from __future__ import annotations

from dataclasses import dataclass

from local_llm_benchmark.utils.db_manager import DatabaseManager


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

    def to_dict(self) -> dict[str, any]:
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
    "prompt",
    "expected",
    "output",
    "ttft_s",
    "tok_per_s",
    "iters_per_s",
    "quality_passed",
    "quality_deterministic",
    "quality_judge",
    "quality_note",
)  # noqa: E501  # must match Row.to_dict() exactly (16 fields)


def get_all_results_from_db(
    db_path: str = None,
    models_filter: str | None = None,
    benchmark_type_filter: str | None = None,
) -> list[Row]:
    """
    Retrieves all benchmark results from the database, optionally filtered, and converts them into Row objects.

    Args:
        db_path: Optional path to the database file. If None, uses the default configured path.
        models_filter: Comma-separated list of model names to filter by.
        benchmark_type_filter: Filter by benchmark category (e.g., "qa", "code").
    Returns:
        A list of Row dataclass objects, filtered by the provided arguments.
    """
    db_manager = DatabaseManager(db_path=db_path)
    results_dicts = db_manager.fetch_all_results()
    db_manager.close()  # Ensure connection is closed after use

    if results_dicts is None:
        results_dicts = []

    filtered_results_dicts = results_dicts
    if models_filter:
        filtered_results_dicts = [d for d in results_dicts if str(d.get("model")) in models_filter]
    if benchmark_type_filter:
        filtered_results_dicts = [
            d for d in filtered_results_dicts if str(d.get("category")) == benchmark_type_filter
        ]

    if not filtered_results_dicts:
        return []

    rows: list[Row] = []
    for d in filtered_results_dicts:
        # We must explicitly map the dictionary keys from the DB to the Row fields.
        # This handles the structure fetched by fetch_all_results.
        row = Row(
            engine=str(d.get("engine")),
            model=str(d.get("model")),
            judge=str(d.get("judge", "")),
            task_id=str(d.get("task_id")),
            category=str(d.get("category", "qa")),
            prompt=str(d.get("prompt", "")),
            expected=str(d.get("expected", "")),
            output=str(d.get("output", "")),
            ttft_s=float(d.get("ttft_s", 0.0)),
            tok_per_s=float(d.get("tok_per_s", 0.0)),
            iters_per_s=float(d.get("iters_per_s", 0.0)),
            quality_passed=bool(d.get("quality_passed", "False")),
            quality_deterministic=bool(d.get("quality_deterministic", "False")),
            quality_judge=bool(d.get("quality_judge", "False")),
            quality_note=str(d.get("quality_note", "")),
        )
        rows.append(row)
    return rows

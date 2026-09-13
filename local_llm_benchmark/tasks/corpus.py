"""Task corpus for the benchmark.

A :class:`Task` is a single prompt the benchmark asks an engine to answer.
Every task belongs to a category and may carry deterministic *expected*
answers and a *validate* callable. The runner uses these to score quality
without needing a remote judge.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml

from local_llm_benchmark.config import ConfigError


class TaskCategory(str, Enum):
    """Categories of benchmark tasks."""

    DOC = "doc"
    CODE = "code"
    QA = "qa"
    MATH = "math"

    @classmethod
    def parse(cls, value: Any) -> "TaskCategory":
        """Parse a category from a string or a :class:`TaskCategory`."""
        if isinstance(value, TaskCategory):
            return value
        try:
            return cls(value)
        except ValueError as exc:
            raise ConfigError(f"invalid task category: {value!r}") from exc


TaskValidator = Callable[[str], bool]


@dataclass(frozen=True)
class Task:
    """A single benchmark task.

    Attributes:
        id: Unique task identifier.
        category: :class:`TaskCategory`.
        prompt: The user-facing prompt.
        system: Optional system prompt.
        expected: Optional string whose substring must appear in the answer.
        validate: Optional callable returning ``True`` when the answer is correct.
    """

    id: str
    category: TaskCategory
    prompt: str
    system: Optional[str] = None
    expected: Optional[str] = None
    validate: Optional[TaskValidator] = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ConfigError("task 'id' is required")
        if not self.prompt:
            raise ConfigError(f"task '{self.id}' has an empty prompt")

    @property
    def has_validator(self) -> bool:
        """Return ``True`` if this task carries a deterministic validator."""
        return self.validate is not None

    @classmethod
    def from_dict(cls, data: Dict[str, Any], source: str = "<dict>") -> "Task":
        """Build a :class:`Task` from a mapping loaded from disk."""
        if not isinstance(data, dict):
            raise ConfigError(f"task in {source} must be a mapping")
        task_id = data.get("id")
        category = data.get("category")
        prompt = data.get("prompt")
        if not task_id or not isinstance(task_id, str):
            raise ConfigError(f"task in {source} is missing a string 'id'")
        if not prompt or not isinstance(prompt, str):
            raise ConfigError(f"task '{task_id}' in {source} is missing a 'prompt'")
        if category is None:
            category = "qa"
        return cls(
            id=str(task_id),
            category=TaskCategory.parse(category),
            prompt=prompt,
            system=data.get("system"),
            expected=data.get("expected"),
            validate=data.get("validate"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain mapping."""
        data: Dict[str, Any] = {
            "id": self.id,
            "category": self.category.value,
            "prompt": self.prompt,
        }
        if self.system is not None:
            data["system"] = self.system
        if self.expected is not None:
            data["expected"] = self.expected
        return data


def _load_task_file(path: Path) -> Task:
    """Load a single task from a YAML or JSON file."""
    suffix = path.suffix
    if suffix == ".json":
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    else:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    return Task.from_dict(data, source=str(path))


def load_tasks(task_dir: str | os.PathLike[str]) -> List[Task]:
    """Load every task from *task_dir*.

    Files ending in ``.json`` are parsed as JSON, everything else as YAML.
    Each file yields exactly one task.
    """
    task_dir = Path(task_dir)
    if not task_dir.is_dir():
        raise ConfigError(f"task directory not found: {task_dir}")
    tasks: List[Task] = []
    for path in sorted(task_dir.glob("*.json")):
        tasks.append(_load_task_file(path))
    for path in sorted(task_dir.glob("*.yaml")):
        tasks.append(_load_task_file(path))
    for path in sorted(task_dir.glob("*.yml")):
        tasks.append(_load_task_file(path))
    if not tasks:
        raise ConfigError(f"no tasks found in {task_dir}")
    return tasks


def task_by_id(tasks: List[Task], task_id: str) -> Task:
    """Return the task with *task_id*, raising :class:`ConfigError` if missing."""
    for task in tasks:
        if task.id == task_id:
            return task
    raise ConfigError(f"task '{task_id}' not found")


# The default corpus: a small set of tasks across the four categories.
# Each is concise on purpose: the benchmark keeps the token window small.

# doc: REST API overview, password-reset user guide.
_DOC_REST = """
A brief overview of the REST API: list resources by GET, read by GET /{id},
update with PUT /{id}, delete with DELETE /{id}. All endpoints return JSON
and accept an Authorization header for protected resources.
"""
_DOC_PASSWORD = """
How to reset your password: visit the password-reset page, enter your email,
follow the link in the confirmation email, and choose a new password that is
at least 12 characters long.
"""

# code: sort-dict-by-value, httpx GET with timeout.
_CODE_SORT = "Sort a Python dictionary by its values in ascending order."
_CODE_HTTPX = "Fetch a URL using httpx with a per-request timeout."

# qa: first iPhone year, train distance.
_QA_IPHONE = "What year was the first iPhone released?"
_QA_TRAIN = "How far do the rails of a standard train track extend?"

# math: solve 2x+5=15, area of circle r=7.
_MATH_LINEAR = "Solve the equation 2x + 5 = 15 for x."
_MATH_AREA = "What is the area of a circle with radius 7? Use pi = 3.14159."

_CORPUS: Dict[str, Task] = {
    "doc-rest-api": Task(
        id="doc-rest-api",
        category=TaskCategory.DOC,
        prompt=_DOC_REST,
        expected="GET",
    ),
    "doc-password-reset": Task(
        id="doc-password-reset",
        category=TaskCategory.DOC,
        prompt=_DOC_PASSWORD,
        expected="password-reset",
    ),
    "code-sort-dict-by-value": Task(
        id="code-sort-dict-by-value",
        category=TaskCategory.CODE,
        prompt=_CODE_SORT,
        expected="sorted",
    ),
    "code-httpx-get-timeout": Task(
        id="code-httpx-get-timeout",
        category=TaskCategory.CODE,
        prompt=_CODE_HTTPX,
        expected="httpx",
    ),
    "qa-first-iphone-year": Task(
        id="qa-first-iphone-year",
        category=TaskCategory.QA,
        prompt=_QA_IPHONE,
        expected="2007",
    ),
    "qa-train-distance": Task(
        id="qa-train-distance",
        category=TaskCategory.QA,
        prompt=_QA_TRAIN,
        expected="1132",
    ),
    "math-solve-2x-5-15": Task(
        id="math-solve-2x-5-15",
        category=TaskCategory.MATH,
        prompt=_MATH_LINEAR,
        expected="x = 5",
    ),
    "math-area-circle-r7": Task(
        id="math-area-circle-r7",
        category=TaskCategory.MATH,
        prompt=_MATH_AREA,
        expected="153.938",
    ),
}


def _validate_solution(solution: str) -> bool:
    """Return ``True`` if *solution* solves ``2x + 5 = 15``.

    Accepts forms such as ``x = 5``, ``x=5``, ``5``, ``x=  5 ``.
    """
    cleaned = re.sub(r"\s+", " ", solution.strip()).lower()
    if "x = 5" in cleaned or "x=5" in cleaned or "5" in cleaned:
        return True
    return False


def _validate_area(area: str) -> bool:
    """Return ``True`` if *area* approximates the area of a circle with r = 7.

    The exact area is ``pi * 7^2 ≈ 153.938``.
    """
    cleaned = re.sub(r"\s+", " ", area.strip())
    if re.fullmatch(r"[\d.]+", cleaned):
        try:
            value = float(cleaned)
        except ValueError:
            return False
        return abs(value - 153.938) / 153.938 < 0.02
    return False


# The corpus ships deterministic validators for the math tasks; the rest rely
# on substring matching in the runner.
_DEFAULT_VALIDATORS: Dict[str, TaskValidator] = {
    "math-solve-2x-5-15": _validate_solution,
    "math-area-circle-r7": _validate_area,
}


def build_default_corpus() -> List[Task]:
    """Return the default corpus with deterministic validators attached."""
    # ``_CORPUS`` is a ``Dict[str, Task]`` of frozen dataclasses, so iterate the
    # values directly. Each task needing a deterministic validator is replaced
    # with a mutable copy carrying the ``validate`` callable; the shared frozen
    # tasks in ``_CORPUS`` are left untouched.
    tasks = list(_CORPUS.values())
    for index, task in enumerate(tasks):
        if task.id in _DEFAULT_VALIDATORS:
            tasks[index] = replace(task, validate=_DEFAULT_VALIDATORS[task.id])
    return tasks

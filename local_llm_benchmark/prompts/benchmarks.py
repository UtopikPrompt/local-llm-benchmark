"""Bundled benchmark datasets.

The benchmark prompts are stored as JSON files at the repo root
(``prompts/benchmarks/*``). This package loads them (ADR-004). Each dataset
is a JSON object mapping ``examples`` to a list of benchmark objects.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from local_llm_benchmark.config import PACKAGE_DIR
from local_llm_benchmark.errors import ConfigurationError


def _dataset_dir() -> Path:
    primary = PACKAGE_DIR / "prompts" / "benchmarks"
    if primary.exists():
        return primary
    # Fall back to the repo-root ``prompts/benchmarks`` directory.
    return Path(__file__).resolve().parents[1] / "prompts" / "benchmarks"


def _load(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def get_benchmark(name: str = "truthfulqa", benchmark_file: str | None = None) -> dict:
    """Load a benchmark dataset by name or file path.

    :param name: the bundled benchmark name (e.g. ``"truthfulqa"``).
    :param benchmark_file: an explicit path to a JSON file.
    :raises ConfigurationError: if the benchmark is unknown or the file is
        missing.
    """
    if benchmark_file:
        path = Path(benchmark_file)
        if not path.exists():
            raise ConfigurationError(f"benchmark file {path} does not exist")
        return _load(path)

    datasets = _dataset_dir()
    if not datasets.exists():
        raise ConfigurationError(f"benchmark datasets directory {datasets} not found")
    path = datasets / f"{name}.json"
    if not path.exists():
        raise ConfigurationError(
            f"unknown benchmark {name!r} in {_dataset_dir()}. Available: "
            f"{', '.join(sorted(p.name[:-5] for p in datasets.glob('*.json')))}"
        )
    return _load(path)


def list_benchmarks() -> Dict[str, str]:
    """Return a mapping of benchmark name to file path."""
    datasets = _dataset_dir()
    result: Dict[str, str] = {}
    if datasets.exists():
        for path in sorted(datasets.glob("*.json")):
            result[path.stem] = str(path)
    return result

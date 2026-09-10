"""Service layer for the API.

These functions contain the business logic behind the HTTP endpoints: engine
selection, configuration construction, running the benchmark and writing the
report. They import only from the shared core package
(:mod:`local_llm_benchmark`) and never from one another, so the HTTP concern
lives entirely in :mod:`api.controller`.

The services raise *domain* exceptions (:class:`BadRequest`,
:class:`EngineNotFound`) rather than FastAPI's ``HTTPException``; the
:class:`local_llm_benchmark.server.api.controller.Controller` is the sole place
that maps those to HTTP status codes. This keeps the service layer reusable
and free of any HTTP knowledge.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from local_llm_benchmark import config
from local_llm_benchmark.config import (
    DEFAULT_ENGINE_BASE_URL,
    DEFAULT_ENGINE_MODEL,
    DEFAULT_JUDGE_BASE_URL,
    DEFAULT_JUDGE_MODEL,
    DEFAULT_MAX_CONCURRENT,
    DEFAULT_RESULTS_DIR,
    DEFAULT_TIMEOUT,
    BenchmarkConfig,
    Defaults,
    EngineConfig,
    JudgeConfig,
    load_config,
)
from local_llm_benchmark.report import write_report
import local_llm_benchmark.runner as runner


class BadRequest(Exception):
    """The request is missing one or more required fields."""


class EngineNotFound(Exception):
    """The named engine is not configured."""


def _new_engine_from_request(request: Dict[str, Any], defaults: Defaults) -> EngineConfig:
    """Build a fresh :class:`EngineConfig` from the request body."""
    return EngineConfig(
        name="ollama",
        base_url=request["base_url"],
        model=request["model"],
        timeout=request.get("timeout", defaults.timeout),
        max_concurrent=request.get("max_concurrent", defaults.max_concurrent),
    )


def _new_judge_from_request(request: Dict[str, Any], defaults: Defaults) -> Optional[JudgeConfig]:
    """Build a fresh :class:`JudgeConfig` from the request body, if requested."""
    judge_url = request.get("judge_url") or request.get("judgeUrl")
    if not judge_url:
        return None
    return JudgeConfig(
        name="judge",
        base_url=str(judge_url),
        model=request.get("judge_model") or request.get("judgeModel") or defaults.judge_model,
        timeout=request.get("timeout", defaults.timeout),
    )


async def run(request: Dict[str, Any], *, config_path: Optional[str] = None) -> Dict[str, Any]:
    """Run the benchmark described by *request* and return the result rows.

    *request* is the JSON body posted to ``POST /run``. If it carries an
    ``engine`` name the matching configured engine is selected; otherwise a
    fresh single engine is built from ``base_url``/``model``. Optional judges,
    task directory, format and output path are taken from the request, falling
    back to the centralized :class:`~local_llm_benchmark.config.Defaults`.

    Args:
        request: The run request.
        config_path: Optional explicit config file. Defaults to the
            project-root ``config.yaml``.

    Returns:
        A mapping with ``rows`` (one dict per measurement) and ``output``
        (the path the report was written to).

    Raises:
        EngineNotFound: if an engine name is not configured.
        BadRequest: if the request is missing required fields.
    """
    defaults = Defaults()
    selected = request.get("engine")
    if selected:
        engine = defaults.select_engine(selected)
        if engine is None:
            raise EngineNotFound(f"engine '{selected}' not configured")
    else:
        if not request.get("base_url") or not request.get("model"):
            raise BadRequest("'base_url' and 'model' are required")
        engine = _new_engine_from_request(request, defaults)

    judges: List[JudgeConfig] = []
    judge = _new_judge_from_request(request, defaults)
    if judge is not None:
        judges.append(judge)

    config = BenchmarkConfig(
        engines=[engine],
        judges=judges,
        tasks=request.get("task_dir", defaults.tasks),
        task=request.get("task"),
        max_concurrent=request.get("max_concurrent", defaults.max_concurrent),
        timeout=request.get("timeout", defaults.timeout),
        format=request.get("format", defaults.format),
        output=request.get("output", defaults.output),
    )
    rows = await runner.run_benchmark(config)
    write_report(rows, config.output, fmt=request.get("format", defaults.format))
    return {"rows": [row.to_dict() for row in rows], "output": config.output}


async def defaults() -> Dict[str, Any]:
    """Return the centralized default values used to seed the dashboard form."""
    return Defaults().to_dict()


async def engines(config_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return the engines configured in the dashboard's config file."""
    path = _resolve_config(config_path)
    if not path.exists():
        return []
    data = load_config(str(path))
    return [engine.to_dict() for engine in data.engines]


def _resolve_config(config_path: Optional[str]) -> Path:
    """Resolve the full path to the configuration file."""
    if config_path:
        path = Path(config_path)
    else:
        # Fallback to the repository-root config.yaml, computed from this
        # module's location (the package sits three levels below the repo root).
        root_path = Path(__file__).resolve().parent.parent.parent.parent / "config.yaml"
        path = root_path
    
    if not path.exists():
        raise EngineNotFound(f"configuration file not found: {path}")
    return path


async def results(models: str | None, benchmark_type: str | None) -> dict:
    """
    Read all saved benchmark reports from the results directory and filter
    them by the requested *models* (comma-separated) and optional benchmark
    type. Results are returned sorted by (model, engine) so all rows for a
    given model cluster together.

    Args:
        models: Optional comma-separated list of model names to filter by.
        benchmark_type: Optional benchmark type (e.g., 'speed', 'quality').
    Returns:
        A dictionary containing a list of benchmark result dictionaries.
    """
    from pathlib import Path

    results_dir = Path(DEFAULT_RESULTS_DIR)
    if not results_dir.exists():
        return {"results": []}

    report_files = list(results_dir.glob("*.json"))
    all_results: List[Dict[str, Any]] = []

    for file_path in report_files:
        try:
            # Assuming the JSON file contains a list of result objects
            with open(file_path, "r") as f:
                data = json.load(f)

            if isinstance(data, list):
                for item in data:
                    # Assuming each item has fields like 'model', 'type', 'benchmark', etc.
                    all_results.append(item)
            else:
                # Handle case where the JSON might contain a single summary dict
                all_results.append(data)

        except json.JSONDecodeError:
            # Skip non-JSON files or corrupted JSON
            continue
        except Exception as e:
            print(f"Error processing file {file_path}: {e}")
            continue

    # Structure the results for the dashboard frontend using the Row schema:
    # engine, model, judge, category, ttft_s, tok_per_s, iters_per_s,
    # quality_passed, quality_judge, quality_note.
    formatted_results = []
    for item in all_results:
        if not isinstance(item, dict):
            continue
        formatted_results.append(
            {
                "engine": item.get("engine", item.get("model", "Unknown")),
                "model": item.get("model", item.get("engine", "Unknown")),
                "judge": item.get("judge", ""),
                "category": item.get("category", ""),
                "ttft_s": item.get("ttft_s", 0.0),
                "tok_per_s": item.get("tok_per_s", 0.0),
                "iters_per_s": item.get("iters_per_s", 0.0),
                "quality_passed": bool(item.get("quality_passed", False)),
                "quality_deterministic": bool(item.get("quality_deterministic", False)),
                "quality_judge": bool(item.get("quality_judge", False)),
                "quality_note": item.get("quality_note", ""),
            }
        )

        if models:
            wanted = {m.strip() for m in models.split(",") if m.strip()}
            formatted_results = [r for r in formatted_results if r["model"] in wanted]

        formatted_results.sort(key=lambda r: (r["model"], r["engine"]))

    return {"results": formatted_results}

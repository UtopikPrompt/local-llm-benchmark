"""Service layer for the API.

These functions contain the business logic behind the HTTP endpoints: engine
selection, configuration construction, running the benchmark and writing the
report. They import only from the shared core package
(:mod:`local_llm_benchmark`) and never from one another, so the HTTP concern
lives entirely in :mod:`api.controller`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from local_llm_benchmark.config import (
    DEFAULT_ENGINE_BASE_URL,
    DEFAULT_ENGINE_MODEL,
    DEFAULT_JUDGE_BASE_URL,
    DEFAULT_JUDGE_MODEL,
    DEFAULT_MAX_CONCURRENT,
    DEFAULT_TIMEOUT,
    BenchmarkConfig,
    Defaults,
    EngineConfig,
    JudgeConfig,
    load_config,
    project_config_path,
)
from local_llm_benchmark.report import write_report
import local_llm_benchmark.runner as runner


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
        HTTPException: if an engine name is not configured (status 404), or the
            request is missing required fields (status 400).
    """
    defaults = Defaults()
    selected = request.get("engine")
    if selected:
        engine = defaults.select_engine(selected)
        if engine is None:
            raise HTTPException(status_code=404, detail=f"engine '{selected}' not configured")
    else:
        if not request.get("base_url") or not request.get("model"):
            raise HTTPException(status_code=400, detail="'base_url' and 'model' are required")
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
    path = Path(config_path or str(project_config_path()))
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"configuration file not found: {path}")
    return path

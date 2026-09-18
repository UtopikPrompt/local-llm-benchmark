"""Service layer for the API.

These functions contain the business logic behind the HTTP endpoints: engine
selection, configuration construction, running the benchmark and writing the
report. They import only from the shared core package
(:mod:`local_llm_benchmark`) and never from one another, so the HTTP concern
lives entirely in :mod:`src.api.controller`.

The services raise *domain* exceptions (:class:`BadRequest`,
:class:`EngineNotFound`) rather than FastAPI's ``HTTPException``; the
:class:`local_llm_benchmark.src.api.controller.Controller` is the sole place
that maps those to HTTP status codes. This keeps the service layer reusable
and free of any HTTP knowledge.
"""

from __future__ import annotations

import json
from pathlib import Path

from local_llm_benchmark import config
from local_llm_benchmark.config import (
    DEFAULT_RESULTS_DIR,
    Defaults,
    EngineConfig,
    JudgeConfig,
    load_config,
    save_config,
)
from local_llm_benchmark.logger import BenchmarkLogger, logger
from local_llm_benchmark.results import get_all_results_from_db


class BadRequest(Exception):
    """The request is missing one or more required fields."""


class EngineNotFound(Exception):
    """The named engine is not configured."""


def _new_engine_from_request(request: dict[str, any], defaults: Defaults) -> EngineConfig:
    """Build a fresh :class:`EngineConfig` from the request body."""
    return EngineConfig(
        name="ollama",
        base_url=request["base_url"],
        model=request["model"],
        timeout=request.get("timeout", defaults.timeout),
        max_concurrent=request.get("max_concurrent", defaults.max_concurrent),
    )


def _engine_from_request(request: dict[str, any]) -> EngineConfig:
    """Build an :class:`EngineConfig` from the request body, validating it.

    Raises:
        BadRequest: if the request body fails the engine's validation
            (:class:`ConfigError`), keeping the service layer free of any HTTP
            knowledge while still signaling a bad request to the controller.
    """
    try:
        return EngineConfig.from_dict(request)
    except config.ConfigError as exc:
        raise BadRequest(str(exc)) from exc


def _new_judge_from_request(request: dict[str, any], defaults: Defaults) -> JudgeConfig | None:
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


async def run(request: dict[str, any], *, config_path: str | None = None) -> dict[str, any]:
    """Retrieve all saved benchmark reports from the database and return a
    summary of the results.

    This function replaces the previous execution logic and now serves as the
    primary endpoint for reading historical benchmark results, decoupling the
    API from the live execution workflow. It uses the data source abstraction
    layer :mod:`~local_llm_benchmark.results.get_all_results_from_db`.

    Args:
        request: The run request, used here to derive filtering parameters
            (e.g., model names or benchmark types).
        config_path: Optional explicit config file. Defaults to the
            project-root ``config.yaml``.

    Returns:
        A dictionary containing the structure returned
        by :class:`~local_llm_benchmark.results.results`, including a list of all retrieved
        benchmark result dictionaries.

    Raises:
        (No operational exceptions, as it only reads data.)
    """
    logger.info("Running results endpoint", extra={"models_filter": models_filter, "benchmark_type_filter": benchmark_type_filter})
    
    # Extract model filters from the request payload.
    # We prioritize 'model_names' (for multiple models) or fallback to a single 'model' field.
    models_filter: str | None = None
    if "model_names" in request and request["model_names"]:
        # Assuming model_names is a list/array structure that needs comma joining
        models_filter = ",".join(str(m) for m in request["model_names"])
    elif "model" in request and request["model"]:
        models_filter = request["model"]

    # The benchmark type filter is derived from the request as well.
    benchmark_type_filter: str | None = request.get("benchmark_type")

    # Retrieve all results from the persistent storage layer
    logger.debug("Fetching results from database", extra={"models_filter": models_filter, "benchmark_type_filter": benchmark_type_filter})
    results_data = get_all_results_from_db(
        models_filter=models_filter, benchmark_type_filter=benchmark_type_filter
    )

    # Return the structured results dictionary.
    logger.info("Results endpoint completed", extra={"result_count": len(results_data)})
    return results_data


async def defaults() -> dict[str, any]:
    """Return the centralized default values used to seed the dashboard form."""
    return Defaults().to_dict()


async def engines(config_path: str | None = None) -> list[dict[str, any]]:
    """Return the engines configured in the dashboard's config file."""
    source = _get_config_source(config_path)
    if source == "database":
        # When loading from DB, we assume a function exists to read the whole config structure.
        # We will call a hypothetical DB-aware loader here.
        from local_llm_benchmark.utils.db_manager import get_config_from_db

        try:
            data = await get_config_from_db()
        except Exception:
            return []
    elif isinstance(source, Path):
        if not source.exists():
            return []
        data = load_config(str(source))
    else:
        return []
    return [engine.to_dict() for engine in data.engines]


async def save_engine(request: dict[str, any], config_path: str | None = None) -> dict[str, any]:
    """Persist a new engine to the config file and return it as a mapping.

    The engine is loaded from the config file (defaulting to the repository
    root ``config.yaml``), appended to the engines list, and written back. An
    invalid ``base_url`` raises :class:`BadRequest` via the engine's validation.
    """
    path = _resolve_config(config_path)
    root_path = request.get("root_path")
    data = load_config(str(path), root_path)
    engine = _engine_from_request(request)
    data.engines.append(engine)
    save_config(str(path), data)
    return engine.to_dict()


async def get_engine(name: str, config_path: str | None = None) -> dict[str, any]:
    """Return the engine mapping for *name*, or raise :class:`EngineNotFound`."""
    path = _resolve_config(config_path)
    data = load_config(str(path))
    engine = data.engines_by_name.get(name)
    if engine is None:
        raise EngineNotFound(f"engine '{name}' not configured")
    return engine.to_dict()


async def update_engine(
    name: str, request: dict[str, any], config_path: str | None = None
) -> dict[str, any]:
    """Replace the engine *name* in the config file and return it as a mapping.

    The engine is loaded from the config file (defaulting to the repository
    root ``config.yaml``), replaced in the engines list, and written back. An
    invalid ``base_url`` raises :class:`BadRequest` via the engine's validation.
    """
    path = _resolve_config(config_path)

    if name not in load_config(str(path)).engines_by_name:
        raise EngineNotFound(f"engine '{name}' not configured")

    data = load_config(str(path))
    engine = _engine_from_request(request)
    for index, existing in enumerate(data.engines):
        if existing.name == name:
            data.engines[index] = engine
            save_config(str(path), data)
            return engine.to_dict()


async def delete_engine(name: str, config_path: str | None = None) -> str:
    """Remove the engine *name* from the config file and return its name.

    The config file is loaded (defaulting to the repository
    root ``config.yaml``), the matching engine is removed from the engines list, and
    the file is written back.
    """
    path = _resolve_config(config_path)
    data = load_config(str(path))

    if name not in data.engines_by_name:
        raise EngineNotFound(f"engine '{name}' not configured")
    data.engines = [engine for engine in data.engines if engine.name != name]
    save_config(str(path), data)
    return name


async def tasks() -> list[dict[str, any]]:
    """Return the default task corpus as a list of serializable task dicts.

    Each task carries its ``id``, ``category`` and ``prompt`` (plus optional
    ``system`` and ``expected`` fields). The :class:`TaskCategory` enum values
    are returned as their string form (``doc``, ``code``, ``qa``, ``math``).
    """
    from local_llm_benchmark.tasks.corpus import build_default_corpus

    return [task.to_dict() for task in build_default_corpus()]


def _resolve_config(config_path: str | None) -> Path:
    """Resolve the full path to the configuration source (File or DB)."""
    if config_path:
        path = Path(config_path)
        if path.exists():
            return path
        # Fallback to DB if file is specified but missing
        return None
    else:
        # Fallback to the repository-root config.yaml, computed from this
        # module's location (the package sits three levels below the repo root).
        root_path = Path(__file__).resolve().parent.parent.parent.parent / "config.yaml"
        if root_path.exists():
            return root_path
        # Fallback to DB if file is expected at root
        return None


def _get_config_source(config_path: str | None) -> Path | str:
    """
    Determines the configuration source. Returns the Path object if it's a
    file, or a unique DB identifier (e.g., 'database') if it should be
    read from the database.

    This function replaces the previous file-only path resolution.
    """
    if config_path:
        path = Path(config_path)
        if path.exists():
            return path

    # If file resolution failed or was not provided, assume DB source.
    return "database"


def _resolve_config_tasks(
    config: config.BenchmarkConfig, challenge_ids: list[str]
) -> list[tasks.Task]:
    """Resolve a list of challenge *ids* to :class:`Task` objects.

    The ids are looked up against the tasks loaded from ``config.tasks``
    (the default corpus when ``config.tasks == '.'``). Returns the ordered
    list of matching tasks.
    """
    from local_llm_benchmark.tasks import corpus

    task_dir = config.tasks
    try:
        loaded_tasks = corpus.load_tasks(task_dir)
    except corpus.ConfigError:
        # Fall back to the built-in default corpus when the configured path
        # holds no tasks (e.g. the default corpus was never materialized).
        loaded_tasks = corpus.build_default_corpus()

    return [corpus.task_by_id(loaded_tasks, cid) for cid in challenge_ids]


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
    all_results: list[dict[str, any]] = []

    for file_path in report_files:
        try:
            # Assuming the JSON file contains a list of result objects
            with open(file_path) as f:
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

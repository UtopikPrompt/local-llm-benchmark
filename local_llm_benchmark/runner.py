"""Benchmark orchestrator and command-line interface.

Runs the benchmark across all configured engines and writes the report::

    python -m local_llm_benchmark.runner \
        --base-url http://localhost:11434 --model llama3 \
        --output results/<timestamp>.json

or against a full configuration::

    python -m local_llm_benchmark.runner --config config.yaml --serve
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence

import anyio

from local_llm_benchmark.config import BenchmarkConfig, EngineConfig, JudgeConfig, default_output
from local_llm_benchmark.engines.base import Engine
from local_llm_benchmark.engines.openai_compat import OpenAICompatEngine
from local_llm_benchmark.eval.quality import Judge, evaluate_quality
from local_llm_benchmark.report import print_summary, write_report
from local_llm_benchmark.results import Row
from local_llm_benchmark.tasks.corpus import Task, build_default_corpus, load_tasks, task_by_id
from local_llm_benchmark.utils.db_manager import DatabaseManager

# Global connection management placeholder (will be initialized in main/run_benchmark)
DB_MANAGER = DatabaseManager()


def _select_tasks(config: BenchmarkConfig) -> list[Task]:
    """Return the list of tasks to run for *config*."""
    if config.tasks == ".":
        tasks = build_default_corpus()
    else:
        tasks = load_tasks(config.tasks)
    if config.task:
        return [task_by_id(tasks, config.task)]
    return tasks


async def _run_one(
    engine: Engine,
    task: Task,
    judges: list[Judge],
    expected: str | None,
    validate: Callable[[str], bool] | None,
) -> Row:
    """Run the speed benchmark on *task* and score the quality of the output."""
    from local_llm_benchmark.benchmarks.speed import benchmark_speed

    rows = await benchmark_speed(engine, task)
    if not rows:
        return Row(
            engine=engine.config.name,
            model=engine.config.model,
            task_id=task.id,
            category=task.category.value,
            prompt=task.prompt,
            expected=task.expected or "",
            quality_passed=False,
            quality_note="no speed rows produced",
        )

    # Use the best (highest-throughput) trial for quality scoring.
    best = max(rows, key=lambda row: row.tok_per_s)
    quality_row = await evaluate_quality(
        task,
        best.output,
        expected=task.expected,
        validate=validate,
        judge=judges[0] if judges else None,
    )
    best.judge = quality_row.judge
    best.quality_passed = quality_row.quality_passed
    best.quality_deterministic = quality_row.quality_deterministic
    best.quality_note = quality_row.quality_note
    return best


async def run_benchmark(config: BenchmarkConfig) -> None:
    """
    Runs the benchmark for all selected model/challenge combinations,
    persisting results per-challenge to SQLite.

    Refactored to enforce sequential execution:
    Model -> Challenge -> Engine -> Task
    Ensures engines are properly opened and closed for every run.
    """
    if not config.selected_models or not config.selected_challenges:
        print("No models or challenges selected. Skipping benchmark run.")
        return

    # Clear previous results and initialize DB for the run
    DB_MANAGER.clear_run_results()

    print(
        f"""Starting benchmark run for {len(config.selected_models)} models 
        across {len(config.selected_challenges)} challenges..."""
    )

    for model in config.selected_models:
        for task in config.selected_challenges:
            # Start Engine/Task block for a specific Model/Challenge pair
            print(f"--- Starting run for Model: {model}, Challenge: {task.id} ---")

            for engine_config in config.engines:
                engine = OpenAICompatEngine(engine_config)
                try:
                    # Now iterate over all tasks belonging to this challenge
                    tasks_in_challenge = [t for t in config.tasks if t.category == task.category.value]
                    if not tasks_in_challenge:
                        print(f"Warning: No tasks found for challenge {task.id} with current configuration.")
                        continue

                    for task_run in tasks_in_challenge:
                        # Run the benchmark and score quality for this specific Model/Challenge/Task combination
                        print(f"  -> Running Task: {task_run.id}")
                        row = await _run_one(engine, task_run, [], task_run.expected, task_run.validate)
                        await DB_MANAGER.save_row(row)
                    
                    print(f"--- Finished all tasks for Model: {model}, Challenge: {task.id} ---")

                finally:
                    # Crucial: Ensure the engine is always closed, even on failure
                    await engine.close()

    print("Benchmark run complete. Results persisted to SQLite.")


async def run_per_challenge(
    config: BenchmarkConfig,
    challenges: Sequence[str],
    engines: Sequence[EngineConfig],
) -> list[Row]:
    """Run the benchmark one engine at a time, one challenge at a time.

    ``challenges`` are category ids (e.g. ``"qa"``). Each challenge is run fully
    before the next begins. Within a challenge, engines are run one at a time
    (sequentially): every task of the challenge is benchmarked against the
    current engine before the next engine is opened. Each (engine, task) pair
    produces exactly one :class:`Row`, written to the shared ``rows`` list.
    """
    rows: list[Row] = []
    engine_configs: list[EngineConfig] = list(engines)
    for category in challenges:
        tasks = [t for t in config.tasks if t.category == category]
        if not tasks:
            continue
        for engine_config in engine_configs:
            engine = OpenAICompatEngine(engine_config)
            try:
                for task in tasks:
                    row = await _run_one(engine, task, [], task.expected, task.validate)
                    rows.append(row)
            finally:
                await engine.close()
    return rows


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Benchmark local LLM engines.")
    parser.add_argument("--engine", default="engine", help="Engine name from a config file.")
    parser.add_argument("--base-url", help="Base URL of the OpenAI-compatible engine.")
    parser.add_argument("--model", help="Model served by the engine.")
    parser.add_argument(
        "--models",
        action="store_true",
        help="List models for each engine (config or --base-url) and exit.",
    )
    parser.add_argument(
        "--list-engines",
        action="store_true",
        help="List configured engines (config or --engine/--base-url) and exit.",
    )
    parser.add_argument("--judge", help="Judge name from a config file.")
    parser.add_argument("--judge-url", help="Base URL of the judge engine.")
    parser.add_argument("--judge-model", help="Model served by the judge engine.")
    parser.add_argument("--task-dir", default=".", help="Directory of task files.")
    parser.add_argument("--task", help="Run a single task by id.")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output format.")
    parser.add_argument(
        "--output",
        default="",
        help="Path to write the report. Defaults to results/<timestamp>.<format>.",
    )
    parser.add_argument(
        "--max-concurrent", type=int, default=1, help="Max concurrent requests per task."
    )
    parser.add_argument(
        "--timeout", type=float, default=60.0, help="Per-request timeout in seconds."
    )
    parser.add_argument("--config", help="Path to a YAML/JSON config file.")
    parser.add_argument("--trials", type=int, default=3, help="Number of trials per task.")
    parser.add_argument(
        "--selector", action="store_true", help="Interactively pick a model and exit."
    )
    parser.add_argument(
        "--serve", action="store_true", help="Serve the engine as an OpenAI-compatible proxy."
    )
    return parser.parse_args(argv)


def _build_config(args: argparse.Namespace) -> BenchmarkConfig:
    """Build a :class:`BenchmarkConfig` from parsed CLI arguments."""
    if args.config:
        config = BenchmarkConfig.from_dict(_load_config_file(args.config))
    elif args.engine and args.base_url and args.model:
        config = BenchmarkConfig(
            engines=[
                EngineConfig(
                    args.engine,
                    args.base_url,
                    args.model,
                    timeout=args.timeout,
                    max_concurrent=args.max_concurrent,
                )
            ],
            tasks=args.task_dir,
            task=args.task,
            max_concurrent=args.max_concurrent,
            timeout=args.timeout,
            format=args.format,
            output=args.output,
        )
    else:
        raise ValueError("provide --config, or --engine/--base-url/--model")
    if args.judge and args.judge_url and args.judge_model:
        config.judges.append(
            JudgeConfig(
                name=args.judge,
                base_url=args.judge_url,
                model=args.judge_model,
                timeout=args.timeout,
            )
        )
    return config


def _load_config_file(path: str) -> dict:
    """Load a YAML/JSON config file, sniffing the format from the extension."""
    from local_llm_benchmark.config import load_config

    return load_config(path).to_dict()


def main(argv: list[str] | None = None) -> None:
    """Entry point for ``python -m local_llm_benchmark.runner``."""
    args = _parse_args(argv)

    if not args.output:
        args.output = default_output(fmt=args.format)

    if args.selector:
        _run_selector(args)
        return

    if args.serve:
        from local_llm_benchmark.server.proxy import serve_proxy

        serve_proxy(EngineConfig(name="serve", base_url=args.base_url, model=args.model))
        return

    if args.list_engines:
        _list_engines(args)
        return

    if args.models:
        _list_models(args)
        return

    config = _build_config(args)

    # Initialize and validate DB connection
    db_manager = DatabaseManager()
    if not db_manager.initialize_schema():
        print("FATAL: Could not initialize database schema. Exiting.")
        return

    rows = anyio.run(run_benchmark, config)

    # Save all collected benchmark rows to the database
    print("\\n[DB] Saving benchmark results to the database...")
    saved_count = 0
    for row in rows:
        # Convert the Row object to a dictionary suitable for the database manager
        # Assuming Row has attributes that match the DB schema fields.
        # If the Row object is a dataclass, accessing attributes directly is safer.
        result_data = {
            "run_timestamp": row.run_timestamp,
            "benchmarkId": row.benchmarkId,
            "model": row.model,
            "engine": row.engine,
            "score": row.score,
            "latencyMs": row.latencyMs,
            "passed": row.quality_passed,
            "scoreStr": row.scoreStr,
            "latencyStr": row.latencyStr,
            "status": row.status,
        }
        if db_manager.insert_result(result_data):
            saved_count += 1

    print(f"[DB] Successfully saved {saved_count}/{len(rows)} results to the database.")

    write_report(rows, config.output, fmt=config.format)
    print_summary(rows)

    db_manager.close()


def _run_selector(args: argparse.Namespace) -> None:
    """Interactively pick a model from the engine and exit."""
    from local_llm_benchmark.engines.openai_compat import OpenAICompatEngine

    engine_obj = OpenAICompatEngine(
        EngineConfig(name="preview", base_url=args.base_url or "", model="")
    )
    models = anyio.run(engine_obj.list_models)
    if not models:
        print("No models available.")
        return
    print("\n".join(models))


def _list_engines(args: argparse.Namespace) -> None:
    """List configured engines, mirroring the web Dashboard.

    Iterates over every engine in ``--config`` (falling back to a single
    ``--engine``/``--base-url`` pair when no config file is given) and prints
    a header for each one, exactly like the Dashboard's per-engine section.
    """
    # from local_llm_benchmark.engines.openai_compat import OpenAICompatEngine

    engines = _engines_for_listing(args)
    for engine_config in engines:
        print(f"# {engine_config.name}")
        if args.base_url:
            print(f"  base_url: {engine_config.base_url}")
        if engine_config.model:
            print(f"  model: {engine_config.model}")
        print()


def _list_models(args: argparse.Namespace) -> None:
    """List models for each engine, mirroring the web Dashboard.

    For every engine in ``--config`` (falling back to a single
    ``--engine``/``--base-url`` pair when no config file is given) queries
    ``list_models`` and prints an expandable section with model checkboxes,
    matching the Dashboard's ``renderModelCheckboxes`` behaviour.
    """
    from local_llm_benchmark.engines.openai_compat import OpenAICompatEngine

    engines = _engines_for_listing(args)
    for engine_config in engines:
        engine_obj = OpenAICompatEngine(engine_config)
        models = anyio.run(_list_and_close, engine_obj)
        print(f"# {engine_config.name}")
        if args.base_url:
            print(f"  base_url: {engine_config.base_url}")
        if engine_config.model:
            print(f"  model: {engine_config.model}")
        if models:
            for model in models:
                print(f"  + {model}")
        else:
            print("  (no models)")
        print()


def _engines_for_listing(args: argparse.Namespace) -> list[EngineConfig]:
    """Return the list of engines to inspect for --list-engines/--models.

    Prefers ``--config`` engines; otherwise synthesises a single engine from
    ``--engine``/``--base-url`` (matching how ``_run_selector`` and
    ``_list_models`` construct the engine), falling back to a single unnamed
    engine when only ``--base-url`` is supplied.
    """
    if args.config:
        return BenchmarkConfig.from_dict(_load_config_file(args.config)).engines
    if args.engine and args.base_url:
        return [EngineConfig(args.engine, args.base_url, args.model or "")]
    if args.base_url:
        return [EngineConfig(name="models", base_url=args.base_url, model="")]
    if args.engine:
        return [EngineConfig(args.engine, args.base_url or "", args.model or "")]
    # Defensive fallback: listing without any source is meaningless.
    return [EngineConfig(name="engine", base_url="", model="")]


async def _list_and_close(engine_obj: OpenAICompatEngine) -> list[str]:
    """List models and close the engine within a single event loop.

    Both operations must run on the *same* event loop: closing the HTTP client
    after ``list_models`` on a fresh loop raises ``RuntimeError: Event loop is
    closed`` because the first loop has already been torn down.
    """
    models = await engine_obj.list_models()
    try:
        await engine_obj.close()
    except Exception:
        # The engine may already be closed or the transport may race during
        # teardown; ignore so a failed close never fails the model listing.
        pass
    return models


if __name__ == "__main__":
    main()

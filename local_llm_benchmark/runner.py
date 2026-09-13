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
from typing import Callable, List, Optional

import anyio

from local_llm_benchmark.config import BenchmarkConfig, default_output, EngineConfig, JudgeConfig
from local_llm_benchmark.engines.base import Engine
from local_llm_benchmark.engines.openai_compat import OpenAICompatEngine
from local_llm_benchmark.eval.quality import Judge, evaluate_quality
from local_llm_benchmark.results import Row
from local_llm_benchmark.report import print_summary, write_report
from local_llm_benchmark.tasks.corpus import Task, build_default_corpus, load_tasks, task_by_id


def _select_tasks(config: BenchmarkConfig) -> List[Task]:
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
    judges: List[Judge],
    expected: Optional[str],
    validate: Optional[Callable[[str], bool]],
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


async def run_benchmark(config: BenchmarkConfig) -> List[Row]:
    """Run the full benchmark described by *config*.

    For every engine, runs every selected task, measures speed, and scores
    quality (deterministic checks plus the optional judge). Returns one
    :class:`Row` per (engine, task) pair.
    """
    tasks = _select_tasks(config)
    rows: List[Row] = []
    # Build concrete :class:`Judge` objects from the judge configurations,
    # loading each judge engine once and closing it when the run completes.
    judges: List[Judge] = []
    judge_engines: List[OpenAICompatEngine] = []
    engines: List[OpenAICompatEngine] = []
    try:
        for engine_config in config.engines:
            engine = OpenAICompatEngine(engine_config)
            engines.append(engine)
            for task in tasks:
                validate = task.validate if callable(task.validate) else None
                row = await _run_one(engine, task, judges, task.expected, validate)
                rows.append(row)
        # Open judge engines only once all engine tasks have run, so judges
        # are never opened when there is nothing to score.
        for judge_config in config.judges:
            judge_engine = OpenAICompatEngine(judge_config)
            judge_engines.append(judge_engine)
            judges.append(Judge(engine=judge_engine, name=judge_config.name))
    finally:
        # Always release every engine opened above, including on error.
        for engine in engines:
            await engine.close()
        for judge_engine in judge_engines:
            await judge_engine.close()
    return rows


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Benchmark local LLM engines.")
    parser.add_argument("--engine", default="engine", help="Engine name from a config file.")
    parser.add_argument("--base-url", help="Base URL of the OpenAI-compatible engine.")
    parser.add_argument("--model", help="Model served by the engine.")
    parser.add_argument("--models", action="store_true", help="List models for --base-url and exit.")
    parser.add_argument("--judge", help="Judge name from a config file.")
    parser.add_argument("--judge-url", help="Base URL of the judge engine.")
    parser.add_argument("--judge-model", help="Model served by the judge engine.")
    parser.add_argument("--task-dir", default=".", help="Directory of task files.")
    parser.add_argument("--task", help="Run a single task by id.")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output format.")
    parser.add_argument("--output", default="", help="Path to write the report. Defaults to results/<timestamp>.<format>.")
    parser.add_argument("--max-concurrent", type=int, default=1, help="Max concurrent requests per task.")
    parser.add_argument("--timeout", type=float, default=60.0, help="Per-request timeout in seconds.")
    parser.add_argument("--config", help="Path to a YAML/JSON config file.")
    parser.add_argument("--trials", type=int, default=3, help="Number of trials per task.")
    parser.add_argument("--selector", action="store_true", help="Interactively pick a model and exit.")
    parser.add_argument("--serve", action="store_true", help="Serve the engine as an OpenAI-compatible proxy.")
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
            JudgeConfig(name=args.judge, base_url=args.judge_url, model=args.judge_model, timeout=args.timeout)
        )
    return config


def _load_config_file(path: str) -> dict:
    """Load a YAML/JSON config file, sniffing the format from the extension."""
    from local_llm_benchmark.config import load_config

    return load_config(path).to_dict()


def main(argv: Optional[List[str]] = None) -> None:
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

    if args.models:
        _list_models(args)
        return

    config = _build_config(args)
    rows = anyio.run(run_benchmark, config)
    write_report(rows, config.output, fmt=config.format)
    print_summary(rows)


def _run_selector(args: argparse.Namespace) -> None:
    """Interactively pick a model from the engine and exit."""
    from local_llm_benchmark.engines.openai_compat import OpenAICompatEngine

    engine_obj = OpenAICompatEngine(EngineConfig(name="preview", base_url=args.base_url or "", model=""))
    models = anyio.run(engine_obj.list_models)
    if not models:
        print("No models available.")
        return
    print("\n".join(models))


def _list_models(args: argparse.Namespace) -> None:
    """List models for --base-url and exit."""
    from local_llm_benchmark.engines.openai_compat import OpenAICompatEngine

    engine_obj = OpenAICompatEngine(EngineConfig(name="models", base_url=args.base_url, model=""))
    models = anyio.run(_list_and_close, engine_obj)
    print("\n".join(models))


async def _list_and_close(engine_obj: OpenAICompatEngine) -> List[str]:
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

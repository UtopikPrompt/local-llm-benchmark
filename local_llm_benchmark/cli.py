"""Command-line interface — the single source of truth for the benchmark.

The CLI owns all benchmark logic: engine selection, inference, quality
evaluation, streaming, storage, and analysis. The Astro UI is a thin wrapper
that delegates to these same commands (ADR-003, ADR-029).

Usage:
    python -m local_llm_benchmark <command> [options]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
from rich.console import Console
from rich.table import Table

from local_llm_benchmark import __version__
from local_llm_benchmark.config import RESULTS_DIR, cache_dir
from local_llm_benchmark.engine import (
    Engine,
    EngineConfig,
    available_engines,
    engine_names,
    get_engine_class,
)
from local_llm_benchmark.errors import BenchmarkError, ConfigurationError
from local_llm_benchmark.prompts.benchmarks import get_benchmark, list_benchmarks
from local_llm_benchmark import storage

console = Console()


@dataclass
class BenchmarkRun:
    """Metadata describing a completed benchmark run."""

    run_id: str
    engine: str
    model: str
    benchmark: str
    seed: int
    temperature: float
    max_tokens: int
    created_at: str
    endpoint: str
    num_examples: int
    num_tokens: int
    ttft: float
    tokens_per_sec: float


@dataclass
class RunOptions:
    """Options for a benchmark run."""

    benchmark: str = "truthfulqa"
    engine: str = "transformers"
    model: str = ""
    seed: int = 42
    temperature: float = 0.0
    max_tokens: int = 128
    endpoint: str = ""
    api_key: str = ""
    api_base: str = ""
    stream: bool = False
    benchmark_file: Optional[str] = None


def resolve_benchmark(options: RunOptions) -> str:
    """Return the benchmark file path, resolving builtin or custom file."""
    if options.benchmark_file:
        return options.benchmark_file
    known = list_benchmarks()
    if options.benchmark in known:
        return known[options.benchmark]
    raise ConfigurationError(
        f"unknown benchmark {options.benchmark!r}. Available: {', '.join(list_benchmarks())}"
    )


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="local-llm-benchmark",
        description="Benchmark the performance and quality of LLM models.",
    )
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    # list-engines
    p_engines = sub.add_parser(
        "list-engines", help="List available engines and their dependencies.")
    p_engines.set_defaults(func=list_engines)

    # list-benchmarks
    p_bm = sub.add_parser(
        "list-benchmarks", help="List the bundled benchmark files.")
    p_bm.set_defaults(func=list_benchmarks_cmd)

    # run
    p_run = sub.add_parser("run", help="Run a benchmark against an engine.")
    p_run.add_argument("--benchmark", "-b", default="truthfulqa",
                       help="Bundled benchmark name.")
    p_run.add_argument(
        "--engine", "-e", default="transformers", help="Engine name.")
    p_run.add_argument("--model", "-m", default="",
                       help="Model name advertised to the engine.")
    p_run.add_argument("--seed", "-s", type=int,
                       default=42, help="Sampling seed.")
    p_run.add_argument("--temperature", "-t", type=float, default=0.0)
    p_run.add_argument("--max-tokens", type=int, default=128)
    p_run.add_argument("--endpoint", default="", help="Engine endpoint URL.")
    p_run.add_argument("--api-key", default="",
                       help="API key (required for remote engines).")
    p_run.add_argument("--api-base", default="",
                       help="Base URL override (defaults to the engine's default).")
    p_run.add_argument("--benchmark-file",
                       help="Path to a custom benchmark JSON file.")
    p_run.add_argument("--stream", action="store_true",
                       help="Stream tokens as they are produced.")
    p_run.add_argument("--json", action="store_true",
                       help="Emit machine-readable JSON instead of a table.")
    p_run.set_defaults(func=run_command)

    # stream
    p_stream = sub.add_parser(
        "stream", help="Stream tokens for a single prompt.")
    p_stream.add_argument("--engine", "-e", default="transformers")
    p_stream.add_argument("--model", "-m", default="")
    p_stream.add_argument("--seed", "-s", type=int, default=42)
    p_stream.add_argument("--temperature", "-t", type=float, default=0.0)
    p_stream.add_argument("--max-tokens", type=int, default=128)
    p_stream.add_argument("--prompt", required=True, help="The user prompt.")
    p_stream.add_argument("--endpoint", default="")
    p_stream.add_argument("--api-key", default="")
    p_stream.add_argument("--api-base", default="")
    p_stream.set_defaults(func=stream_command)

    # list-results
    p_results = sub.add_parser(
        "list-results", help="List saved benchmark runs.")
    p_results.add_argument("--json", action="store_true",
                           help="Emit machine-readable JSON.")
    p_results.set_defaults(func=list_results_command)

    # analyze
    p_analyze = sub.add_parser(
        "analyze", help="Analyze a saved run with DuckDB.")
    p_analyze.add_argument("run", help="Run ID to analyze.")
    p_analyze.set_defaults(func=analyze_command)

    return parser.parse_args(argv)


def get_engine_class_safe(name: str):
    try:
        return get_engine_class(name)
    except ConfigurationError:
        raise SystemExit(
            f"error: unknown engine {name!r}. Run `list-engines` for options.")


def build_engine(name: str, options: RunOptions) -> Engine:
    return get_engine_class_safe(name)(
        EngineConfig(
            endpoint=options.endpoint or options.api_base,
            api_key=options.api_key,
            model=options.model,
        )
    )


def load_dataset(path: str) -> tuple[List[dict], List[str]]:
    """Load a benchmark dataset, returning (examples, prompt texts).

    If an example lacks a `prompt` field, a prompt is synthesized from its
    `question` and `answer_choices` (when present).
    """
    try:
        dataset = get_benchmark(path)
    except ConfigurationError:
        raise
    examples = dataset["examples"]
    prompts = []
    for example in examples:
        prompt = example.get("prompt")
        if not prompt:
            if "question" in example:
                prompt = example["question"]
                if example.get("answer_choices"):
                    prompt += "\n" + "\n".join(example["answer_choices"])
        prompts.append(prompt)
    return examples, prompts


def run_command(args: argparse.Namespace) -> int:
    options = RunOptions(
        benchmark=args.benchmark,
        engine=args.engine,
        model=args.model,
        seed=args.seed,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        endpoint=args.endpoint,
        api_key=args.api_key,
        api_base=args.api_base,
        stream=args.stream,
        benchmark_file=args.benchmark_file,
    )
    benchmark_path = resolve_benchmark(options)
    examples, prompts = load_dataset(benchmark_path)
    if not prompts:
        raise ConfigurationError("benchmark dataset contains no examples")

    engine = build_engine(options.engine, options)
    if not engine.capabilities.get("chat") and not engine.capabilities.get("streaming"):
        raise ConfigurationError(
            f"engine {options.engine!r} supports neither chat nor streaming")

    cache_dir()
    results_dir = RESULTS_DIR
    run_id = f"{options.engine}:{options.model}@{options.benchmark}/seed{options.seed}/t{options.temperature}/{int(time.time() * 1000)}"
    parquet_path = results_dir / f"{run_id}.parquet"
    console.print(
        f"[green]Running[/green] {options.engine} / {options.model or 'any-model'} on {benchmark_path}")

    run: Optional[BenchmarkRun] = None
    token_count = 0
    ttft = 0.0
    start = time.time()
    streamed_tokens: List = []
    try:
        if options.stream:
            for prompt in prompts:
                tokens = engine.chat_stream(
                    messages=[
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": ""},
                    ],
                    seed=options.seed,
                    temperature=options.temperature,
                    max_tokens=options.max_tokens,
                )
                streamed_tokens.extend(tokens)
                ttft = ttft or tokens[0].timestamp - start if tokens else 0.0
                token_count += len(tokens)
            run = BenchmarkRun(
                run_id=run_id,
                engine=options.engine,
                model=options.model,
                benchmark=options.benchmark,
                seed=options.seed,
                temperature=options.temperature,
                max_tokens=options.max_tokens,
                created_at=datetime.now(timezone.utc).isoformat(),
                endpoint=options.endpoint or options.api_base,
                num_examples=len(prompts),
                num_tokens=token_count,
                ttft=ttft,
                tokens_per_sec=(token_count / (time.time() - start)
                                ) if (time.time() - start) else 0.0,
            )
        else:
            messages = [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": ""},
            ]
            engine.chat(messages, options.seed,
                        options.temperature, options.max_tokens)
            token_count = len(prompts) * options.max_tokens
            ttft = (token_count / (time.time() - start)
                    ) if (time.time() - start) else 0.0
            run = BenchmarkRun(
                run_id=run_id,
                engine=options.engine,
                model=options.model,
                benchmark=options.benchmark,
                seed=options.seed,
                temperature=options.temperature,
                max_tokens=options.max_tokens,
                created_at=datetime.now(timezone.utc).isoformat(),
                endpoint=options.endpoint or options.api_base,
                num_examples=len(prompts),
                num_tokens=token_count,
                ttft=ttft,
                tokens_per_sec=(token_count / (time.time() - start)
                                ) if (time.time() - start) else 0.0,
            )
    except BenchmarkError as exc:
        run = None
        raise

    if run:
        created_at = run.created_at
        metadata = BenchmarkRun(
            run_id=run.run_id,
            engine=run.engine,
            model=run.model,
            benchmark=run.benchmark,
            seed=run.seed,
            temperature=run.temperature,
            max_tokens=run.max_tokens,
            created_at=created_at,
            endpoint=run.endpoint,
            num_examples=run.num_examples,
            num_tokens=run.num_tokens,
            ttft=run.ttft,
            tokens_per_sec=run.tokens_per_sec,
        )
        if run.num_tokens:
            storage.write_tokens(
                streamed_tokens,
                metadata,
                prompts[0],
                str(parquet_path),
                created_at,
            )
        if not args.json:
            _print_run_summary(run)
        else:
            print(json.dumps(asdict(run), indent=2))
    return 0


def _print_run_summary(run: BenchmarkRun) -> None:
    table = Table(title=f"Benchmark run {run.run_id}")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Engine", run.engine)
    table.add_row("Model", run.model or "any-model")
    table.add_row("Benchmark", run.benchmark)
    table.add_row("Examples", run.num_examples)
    table.add_row("Tokens", run.num_tokens)
    table.add_row("TTFT (s)", f"{run.ttft:.3f}")
    table.add_row("Throughput (tok/s)", f"{run.tokens_per_sec:.1f}")
    table.add_row("Result", str(parquet_path))
    console.print(table)


def stream_command(args: argparse.Namespace) -> int:
    engine = build_engine(args.engine, RunOptions(engine=args.engine, model=args.model,
                          seed=args.seed, endpoint=args.endpoint, api_key=args.api_key, api_base=args.api_base))
    messages = [{"role": "user", "content": args.prompt},
                {"role": "assistant", "content": ""}]
    console.print(
        f"[green]Streaming[/green] with {args.engine} / {args.model or 'any-model'}")
    try:
        for token in engine.chat_stream(
            messages,
            args.seed,
            args.temperature,
            args.max_tokens,
        ):
            console.print(f"[cyan]{token.token}[/cyan]")
    except BenchmarkError as exc:
        console.print(f"[red]Streaming failed: {exc}[/red]")
        return 1
    return 0


def list_engines(args: argparse.Namespace) -> int:
    table = Table(title="Available engines")
    table.add_column("Name")
    table.add_column("Description")
    table.add_column("Requires")
    for name in engine_names():
        try:
            cls = get_engine_class(name)
            required = getattr(cls, "requires", [])
            note = ", ".join(required) if required else "none"
        except ConfigurationError:  # pragma: no cover - defensive
            note = "n/a"
        table.add_row(name, getattr(cls, "description", ""), note)
    console.print(table)
    return 0


def list_benchmarks_cmd() -> int:
    table = Table(title="Bundled benchmarks")
    table.add_column("Name")
    table.add_column("Path")
    for name, path in list_benchmarks().items():
        table.add_row(name, str(path))
    console.print(table)
    return 0


def list_results_command(args: argparse.Namespace) -> int:
    if not RESULTS_DIR.exists():
        if args.json:
            print("[]")
        return 0
    runs = sorted(RESULTS_DIR.glob("*.parquet"))
    if not runs:
        if args.json:
            print("[]")
        else:
            console.print("No benchmark runs found.")
        return 0
    results = []
    for run_path in runs:
        data = pq.read_table(run_path).to_pydict()
        # Updated: Include all known fields, including scores, to ensure consistency with frontend expectations.
        run = BenchmarkRun(**{k: data[k][0]
                           for k in asdict(BenchmarkRun).__fields__})

        # Aggregate scores from the underlying data structure for the JSON output
        # We assume the scores map to the QualityScores structure expected by the frontend.
        scores_data = {
            "accuracy": data.get('accuracy', [0])[0],
            "faithfulness": data.get('faithfulness', [0])[0],
            "groundedness": data.get('groundedness', [0])[0],
            "instructionFollowing": data.get('instructionFollowing', [0])[0],
            "reasoning": data.get('reasoning', [0])[0],
            "relevance": data.get('relevance', [0])[0],
            "helpfulness": data.get('helpfulness', [0])[0],
            "honesty": data.get('honesty', [0])[0],
            "harmlessness": data.get('harmlessness', [0])[0],
        }

        # Dynamically attach scores to the run object for JSON serialization
        run.scores = scores_data

        if args.json:
            results.append(asdict(run))
        else:
            console.print(run.run_id)
    if args.json:
        print(json.dumps(results, indent=2))
    return 0


def analyze_command(args: argparse.Namespace) -> int:
    run_id = args.run
    run_path = RESULTS_DIR / f"{run_id}.parquet"
    if not run_path.exists():
        raise ConfigurationError(f"run {run_id!r} not found in {RESULTS_DIR}")
    results = storage.analysis.analyze(run_path)
    table = Table(title=f"Analysis of {run_id}")
    for key in storage.analysis.KEYS:
        table.add_column(key.upper())
    table.add_row("---" * len(storage.analysis.KEYS))
    for row in _render_analyze(results):
        table.add_row(*[str(value) for value in row])
    console.print(table)
    return 0


def _render_analyze(results: Dict[str, List[dict]]) -> List[List[Any]]:
    """Flatten grouped analysis results into aligned rows."""
    rows: List[List[Any]] = []
    for key in storage.analysis.KEYS:
        for item in results.get(key, []):
            rows.append([key.upper(), item])
    return rows


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    try:
        return args.func(args)
    except BenchmarkError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())

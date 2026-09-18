"""Benchmark runner and execution utilities."""

from typing import Any, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
from collections import deque
import anyio

from .config import Config
from .logger import BenchmarkLogger, logger
from .metrics import BenchmarkMetrics, MetricsCollector


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""
    name: str
    metrics: BenchmarkMetrics
    timestamp: datetime
    config: dict


class BenchmarkRunner:
    """Runner for executing benchmarks."""

    def __init__(self, logger: BenchmarkLogger = logger, metrics_collector: MetricsCollector | None = None):
        self.logger = logger
        self.metrics = metrics_collector or MetricsCollector()

    async def run_benchmark(self, config: Config, benchmark_type: str) -> dict[str, Any]:
        """Run a benchmark based on the config and type using safe async patterns.

        Args:
            config: Configuration for the benchmark
            benchmark_type: Type of benchmark to run (speed, quality)

        Returns:
            Dictionary containing benchmark results
        """
        start_time = datetime.now()
        logger = self.logger
        metrics = self.metrics

        self.logger.info("Starting benchmark", extra={
            "config": str(config),
            "benchmark_type": benchmark_type,
        })

        # Initialize engine
        engine = config.engines.get(config.default_engine)
        if not engine:
            raise ValueError(f"No engine found for default_engine: {config.default_engine}")

        # Run benchmark with anyio TaskGroup for safe concurrent execution
        async def run_single_prompt(prompt: str) -> tuple[str, BenchmarkMetrics]:
            """Run a single prompt through the engine."""
            try:
                result = await engine.benchmark(prompt, config.max_tokens)
                return (prompt, result)
            except Exception as e:
                self.logger.error(f"Benchmark failed for prompt: {prompt[:50]}", extra={
                    "error": str(e),
                    "prompt_preview": prompt[:50],
                })
                return (prompt, BenchmarkMetrics(error=str(e))))

        # Submit all prompts as tasks to the task group
        async with anyio.create_task_group() as tg:
            tasks = [
                tg.start_soon(run_single_prompt, prompt)
                for prompt in config.prompts
            ]

            # Wait for all tasks to complete
            await anyio.wait(tg)

        # Calculate metrics
        total_time = (datetime.now() - start_time).total_seconds()
        metrics.total_time = total_time
        metrics.request_count = len(config.prompts)

        # Calculate success/failure counts
        success_count = sum(1 for _, r in tasks if r[1].success)
        metrics.success_count = success_count
        metrics.failure_count = len(tasks) - success_count

        # Log results
        logger.info("Benchmark completed", extra={
            "total_time_seconds": total_time,
            "request_count": len(tasks),
            "success_count": success_count,
            "failure_count": len(tasks) - success_count,
        })

        return {
            "name": benchmark_type,
            "metrics": {
                "total_time": round(total_time, 3),
                "request_count": len(tasks),
                "success_count": success_count,
                "failure_count": len(tasks) - success_count,
                "avg_time": round(total_time / max(1, len(tasks)), 3),
            },
            "results": [t[0] for t in tasks],
        }


def run_benchmark(config: Config, benchmark_type: str) -> dict[str, Any]:
    """Convenience function to run a benchmark.

    Args:
        config: Configuration for the benchmark
        benchmark_type: Type of benchmark to run

    Returns:
        Dictionary containing benchmark results
    """
    runner = BenchmarkRunner()
    return runner.run_benchmark(config, benchmark_type)


async def run_benchmark_async(config: Config, benchmark_type: str) -> dict[str, Any]:
    """Convenience function to run a benchmark asynchronously.

    Args:
        config: Configuration for the benchmark
        benchmark_type: Type of benchmark to run

    Returns:
        Dictionary containing benchmark results
    """
    runner = BenchmarkRunner()
    return await runner.run_benchmark(config, benchmark_type)

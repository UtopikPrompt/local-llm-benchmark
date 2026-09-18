"""Standalone entry point for running the library directly.

This script allows running local_llm_benchmark without the FastAPI layer:
- Direct benchmark execution
- Programmatic API access
- Testing and CI integration
"""

from local_llm_benchmark.runner import run_benchmark
from local_llm_benchmark.config import Config
from local_llm_benchmark.report import generate_report
from local_llm_benchmark.logger import logger


def main():
    """Main entry point for direct library execution."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run LLM benchmarks directly (bypassing FastAPI)."
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to configuration file (default: config.json)",
    )
    parser.add_argument(
        "--output",
        default="results.json",
        help="Output file for benchmark results",
    )
    parser.add_argument(
        "--format",
        default="jsonl",
        choices=["jsonl", "csv"],
        help="Output format (default: jsonl)",
    )
    parser.add_argument(
        "--engine-name",
        default=None,
        help="Specific engine name to benchmark",
    )
    parser.add_argument(
        "--benchmark-type",
        choices=["speed", "quality"],
        default="speed",
        help="Type of benchmark to run (default: speed)",
    )

    args = parser.parse_args()

    logger.info("Starting benchmark execution", extra={
        "config": args.config,
        "engine": args.engine_name,
        "benchmark_type": args.benchmark_type,
    })

    # Load configuration
    config = Config.load(args.config)
    if args.engine_name:
        config.engines = {args.engine_name: config.engines.get(args.engine_name)}
    
    logger.info("Configuration loaded", extra={
        "config_path": args.config,
    })
    
    print(f"Running benchmarks with config: {config}")
    
    # Run benchmarks
    results = run_benchmark(config, args.benchmark_type)
    
    logger.info("Benchmark completed", extra={
        "benchmark_type": args.benchmark_type,
    })
    
    # Generate report
    report = generate_report(results, args.output, args.format)
    
    logger.info("Benchmark execution finished", extra={
        "output_path": args.output,
    })
    
    print(f"✓ Benchmark complete. Results saved to: {args.output}")


if __name__ == "__main__":
    main()

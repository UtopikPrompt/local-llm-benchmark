"""Baseline performance benchmark for CI/CD regression detection."""

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any


async def benchmark_startup():
    """Benchmark application startup time."""
    import local_llm_benchmark
    
    start = time.perf_counter()
    await local_llm_benchmark.main()
    elapsed = time.perf_counter() - start
    
    return {
        "name": "startup",
        "min": elapsed,
        "max": elapsed,
        "mean": elapsed,
        "ops": 1 / elapsed,
    }


async def benchmark_api_request():
    """Benchmark API request latency."""
    import local_llm_benchmark
    
    start = time.perf_counter()
    await local_llm_benchmark.main()
    elapsed = time.perf_counter() - start
    
    return {
        "name": "api_request",
        "min": elapsed,
        "max": elapsed,
        "mean": elapsed,
        "ops": 1 / elapsed,
    }


async def main():
    """Run all benchmarks and generate report."""
    import pytest
    
    # Run with pytest-benchmark
    result = await pytest.main([__file__, "-v", "--benchmark-mode=min"])
    
    # Generate JSON report
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "platform": os.uname(),
        "engines": [],
        "metrics": [],
    }
    
    # Collect engine benchmarks
    try:
        import local_llm_benchmark.engines
        for engine_name, engine_cls in local_llm_benchmark.engines.__dict__.items():
            if engine_cls.__name__.startswith("Engine"):
                engine = engine_cls()
                report["engines"].append({
                    "name": engine_name,
                    "latency_ms": engine.latency_ms,
                    "tokens_per_second": engine.tokens_per_second,
                })
    except Exception as e:
        report["engines"] = [{"name": "benchmark", "error": str(e)}]
    
    # Save report
    report_path = Path("benchmarks/report.json")
    report_path.write_text(json.dumps(report, indent=2))
    
    # Open HTML report
    if os.name != "nt":
        os.system("open benchmarks/report.html &")
    else:
        os.system("start benchmarks/report.html")
    
    return result


if __name__ == "__main__":
    asyncio.run(main())

# Architectural Decision Record: Performance Testing

* **Title:** Performance Testing
* **Status:** `.pill` **Accepted**
* **Date:** 2026-09-18
* **Authors:** Local LLM Benchmark Team

---

## 📋 Problem Statement / Motivation

The test suite (see ADR 0011) provides functional coverage but has no mechanism to detect performance regressions. Without automated baseline recording and anomaly detection:

- **Invisible Regressions**: A code change that doubles API response latency is not caught by any existing check and ships undetected
- **No Statistical Validation**: Ad-hoc timing assertions (e.g., `assert elapsed < 1.0`) are brittle; they fail on slow CI hosts and pass on fast developer machines
- **No Load Profile**: There is no record of throughput under concurrent load, making capacity planning speculative
- **Missing Thresholds**: There is no formal contract for acceptable latency percentiles (p50, p95, p99) at any given endpoint

### Key Observations

1. Performance regressions are best caught by comparing against a recorded baseline rather than a hard-coded constant
2. Statistical anomaly detection (z-score or IQR) tolerates measurement noise better than absolute thresholds
3. `locust` provides an HTTP load-testing harness that integrates with pytest via `pytest-benchmark`
4. Configurable thresholds (per-endpoint, per-percentile) allow different SLOs for read vs. write endpoints

This decision formalises three complementary performance-testing components:

1. **Baseline Recording** — Capture initial performance measurements and persist them as a reference artefact
2. **Regression Detection** — Statistical comparison of new measurements against the stored baseline
3. **Configurable Thresholds** — Per-endpoint alert configuration expressed in `config.yaml`

---

## ✨ Decision

We will introduce a `tests/performance/` directory containing load tests, a `PerformanceBenchmark` utility, and a baseline-comparison fixture.

### 1.1 Baseline Recording

Capture p50 / p95 / p99 latency for each key endpoint and persist the measurements as a JSON artefact:

```python
# tests/performance/test_load.py

import pytest
import time
from httpx import AsyncClient
from locust import HttpUser, task, between


class BenchmarkUser(HttpUser):
    wait_time = between(1, 5)

    @task
    async def run_benchmark(self):
        """Simulate benchmark list request."""
        response = await self.client.get(
            "/api/benchmarks",
            headers={"Accept": "application/json"},
        )
        assert response.status_code == 200

    @task(5)
    async def run_quality_check(self):
        """Simulate benchmark execution request."""
        response = await self.client.post(
            "/api/benchmarks/run",
            json={"benchmark_id": "test-123"},
            headers={"Accept": "application/json"},
        )
        assert response.status_code == 200


@pytest.mark.performance
class PerformanceTests:
    """Performance test suite."""

    async def test_response_time(self, client: AsyncClient):
        """Assert average response time under repeated load stays under 1 s."""
        for _ in range(100):
            start = time.perf_counter()
            await client.get("/api/benchmarks")
            elapsed = time.perf_counter() - start
            assert elapsed < 1.0
```

### 1.2 Benchmarking Tooling

A reusable `PerformanceBenchmark` class that measures single and repeated invocations and reports summary statistics:

```python
# src/local_llm_benchmark/benchmark.py

import time
from typing import Callable, Any


class PerformanceBenchmark:
    """Timing harness for micro-benchmark measurements."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.results: list[dict[str, Any]] = []

    def run(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Time a single invocation."""
        start = time.perf_counter()
        result = func(*args, **kwargs)
        duration = time.perf_counter() - start
        self.results.append({"duration": duration, "iterations": 1})
        return result

    def run_n(
        self, func: Callable[..., Any], n: int, *args: Any, **kwargs: Any
    ) -> dict[str, Any]:
        """Time n consecutive invocations and return aggregate statistics."""
        total_time = 0.0
        for _ in range(n):
            start = time.perf_counter()
            func(*args, **kwargs)
            total_time += time.perf_counter() - start

        avg_time = total_time / n
        return {
            "total_time": total_time,
            "avg_time": avg_time,
            "iterations": n,
        }

    def report(self) -> None:
        """Print a human-readable summary to stdout."""
        if not self.results:
            return
        print(f"\n=== {self.name} ===")
        for result in self.results:
            print(f"Duration: {result['duration']:.4f}s")
            print(f"Iterations: {result['iterations']}")
        print("=" * 40)
```

### 1.3 Regression Detection

Compare new measurements against a persisted baseline using a z-score test; flag deviations beyond a configurable `sigma_threshold`:

```python
# tests/performance/regression.py

import json
import statistics
from pathlib import Path
from typing import Any

BASELINE_PATH = Path("tests/performance/baseline.json")


def load_baseline() -> dict[str, Any]:
    if BASELINE_PATH.exists():
        return json.loads(BASELINE_PATH.read_text())
    return {}


def save_baseline(measurements: dict[str, Any]) -> None:
    BASELINE_PATH.write_text(json.dumps(measurements, indent=2))


def detect_regression(
    baseline: dict[str, float],
    current: dict[str, float],
    sigma_threshold: float = 2.0,
) -> list[str]:
    """Return a list of metric names that exceed sigma_threshold z-scores."""
    regressions: list[str] = []
    for key, baseline_value in baseline.items():
        if key not in current:
            continue
        # Single-sample z-score against the stored mean
        delta = current[key] - baseline_value
        if baseline_value > 0 and abs(delta / baseline_value) > sigma_threshold:
            regressions.append(key)
    return regressions
```

### 1.4 Configurable Thresholds

Declare per-endpoint SLO thresholds in `config.yaml` so that CI can enforce them without code changes:

```yaml
# config.yaml (performance section)

performance:
  thresholds:
    GET /api/benchmarks:
      p50_ms: 50
      p95_ms: 200
      p99_ms: 500
    POST /api/benchmarks/run:
      p50_ms: 500
      p95_ms: 2000
      p99_ms: 5000
  regression:
    sigma_threshold: 2.0
    baseline_path: tests/performance/baseline.json
```

---

## 💡 Decision Rationale

- **Primary Factor — Regression Prevention**: Baseline comparison catches latency regressions in CI before they reach production; absolute thresholds alone cannot distinguish a legitimate performance improvement from a noisy measurement
- **Secondary Factor — Statistical Validity**: Z-score detection with a configurable sigma threshold adapts to measurement noise on different CI host classes
- **Trade-offs Accepted**: Maintaining a baseline JSON artefact requires deliberate updates when intentional performance changes land; this is an accepted operational cost

---

## ⚖️ Considerations / Alternatives Considered

### Alternative A: Hard-Coded Assertion Thresholds
*Pros:* Zero infrastructure; trivial to add to any test  
*Cons:* Brittle on slow CI machines; does not detect gradual regressions that stay under the threshold individually  
*Rationale for Rejection:* The existing `assert elapsed < 1.0` pattern has produced both false positives (slow CI) and false negatives (slow regressions that are individually under the limit)

### Alternative B: External APM (Datadog, New Relic)
*Pros:* Rich dashboards; persistent history across deployments  
*Cons:* SaaS dependency; cost; requires network egress from CI  
*Rationale for Rejection:* The local-first design principle (ADR 0001) prohibits mandatory external services; Prometheus (ADR 0017) already covers production observability

### Alternative C: `pytest-benchmark` Only (No Baseline File)
*Pros:* Built-in histogram and stats; minimal setup  
*Cons:* Comparisons are only relative to the previous run stored in `pytest-benchmark`'s own storage format; harder to inspect or version-control  
*Rationale for Rejection:* A plain JSON baseline file is human-readable, diffable in PRs, and language-agnostic

---

## 📊 Impact Analysis

### 🟢 Positive Impacts
* **Regression Safety Net**: Every CI run compares against the recorded baseline, catching latency increases before merge
* **SLO Documentation**: `config.yaml` thresholds make the performance contract explicit and reviewable alongside code changes
* **Reusable Tooling**: `PerformanceBenchmark` can be used in both automated CI and ad-hoc developer profiling

### 🔴 Negative Impacts / Trade-offs
* **Baseline Maintenance**: The `baseline.json` file must be updated deliberately when intentional improvements land; stale baselines will trigger false-positive regression alerts
* **Flakiness Risk**: Load tests that contact real LLM endpoints are environment-dependent; they must run in a controlled environment (mocked or local model) to produce stable baselines

---

## 🔗 Related ADRs

* ADR 0011 — Test Coverage Organisation and Verification Goals
* ADR 0017 — Monitoring and Alerting
* ADR 0018 — Benchmark Orchestration & Control

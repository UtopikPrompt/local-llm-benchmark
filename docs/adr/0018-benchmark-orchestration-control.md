# Architectural Decision Record: Benchmark Orchestration & Control

* **Title:** Benchmark Orchestration & Control
* **Status:** `.pill` **Accepted**
* **Date:** 2026-09-18
* **Authors:** Local LLM Benchmark Team

---

## 📋 Problem Statement / Motivation

The current benchmark execution model in `runner.py` runs engine requests sequentially. This design creates three compounding problems as the number of configured engines grows:

- **No Concurrency**: Benchmarks against N engines take O(N × latency) wall time, making large comparison runs impractically slow
- **No Timeout Enforcement**: A single stalled engine blocks the entire run indefinitely
- **No Failure Isolation**: An engine that errors or hangs cascades into all subsequent engines in the queue, producing partial or corrupt results

### Key Observations

1. LLM inference is I/O-bound; `asyncio.gather` can fan-out engine calls without blocking the event loop
2. Per-engine timeouts must be independently enforced so that one slow endpoint does not penalize others
3. Repeated failures against the same engine should trigger a temporary hold (circuit breaker) to prevent resource exhaustion during long runs
4. Concurrency must be configurable: a single-engine local setup and a 20-engine comparison run have different optimal parallelism settings

This decision formalises three complementary orchestration mechanisms:

1. **Concurrent Execution** — `asyncio.gather` with per-engine `asyncio.wait_for` timeout
2. **Configurable Parallelism** — `BenchmarkConfig.max_concurrent` controlling a semaphore guard
3. **Circuit Breaker** — per-engine failure tracking that opens the breaker after a configurable threshold

---

## ✨ Decision

We will refactor the benchmark runner to use `asyncio.gather` with an `asyncio.Semaphore` and a `CircuitBreaker` guard per engine.

### 1.1 Concurrent Benchmarking

Fan out all engine calls simultaneously, with a per-engine timeout to prevent hangs:

```python
# src/local_llm_benchmark/runner.py

import asyncio
from typing import List
from local_llm_benchmark.engines.base import BaseLLMEngine
from local_llm_benchmark.schemas.benchmark import BenchmarkResult


async def run_benchmark_concurrent(
    engines: List[BaseLLMEngine],
    prompt: str,
    timeout: float = 30.0,
) -> List[BenchmarkResult]:
    """Run benchmarks against all engines concurrently with per-engine timeout."""

    async def _run_single(engine: BaseLLMEngine) -> BenchmarkResult:
        return await asyncio.wait_for(
            engine.run(prompt),
            timeout=timeout,
        )

    results = await asyncio.gather(
        *[_run_single(engine) for engine in engines],
        return_exceptions=True,
    )
    return [r for r in results if not isinstance(r, BaseException)]
```

### 1.2 Configurable Parallelism

Cap the number of simultaneously active engine calls via `BenchmarkConfig.max_concurrent`:

```python
# src/local_llm_benchmark/schemas/benchmark.py

from pydantic import BaseModel, Field


class BenchmarkConfig(BaseModel):
    max_concurrent: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Maximum number of engines running in parallel",
    )
    per_engine_timeout: float = Field(
        default=30.0,
        gt=0,
        description="Seconds before an individual engine call is cancelled",
    )


# src/local_llm_benchmark/runner.py

async def run_with_semaphore(
    engines: List[BaseLLMEngine],
    prompt: str,
    config: BenchmarkConfig,
) -> List[BenchmarkResult]:
    """Limit concurrency to config.max_concurrent simultaneous engine calls."""
    semaphore = asyncio.Semaphore(config.max_concurrent)

    async def _guarded(engine: BaseLLMEngine) -> BenchmarkResult:
        async with semaphore:
            return await asyncio.wait_for(
                engine.run(prompt),
                timeout=config.per_engine_timeout,
            )

    return await asyncio.gather(
        *[_guarded(engine) for engine in engines],
        return_exceptions=True,
    )
```

### 1.3 Circuit Breaker Pattern

Prevent cascading failures by tracking per-engine error counts and temporarily skipping engines that exceed the failure threshold:

```python
# src/local_llm_benchmark/runner.py

from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class CircuitBreaker:
    failure_threshold: int = 3
    recovery_timeout: float = 60.0  # seconds
    _failures: int = field(default=0, repr=False)
    _opened_at: datetime | None = field(default=None, repr=False)

    @property
    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        elapsed = (datetime.utcnow() - self._opened_at).total_seconds()
        if elapsed >= self.recovery_timeout:
            self._failures = 0
            self._opened_at = None
            return False
        return True

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._opened_at = datetime.utcnow()

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None
```

---

## 💡 Decision Rationale

- **Primary Factor — Throughput**: Concurrent execution reduces wall time from O(N × latency) to O(max_concurrent × latency), typically a 5–10× improvement on a 10-engine comparison run
- **Secondary Factor — Isolation**: `asyncio.wait_for` and `return_exceptions=True` ensure a single engine failure does not abort the run
- **Trade-offs Accepted**: A semaphore adds a small scheduling overhead; accepted because it prevents resource exhaustion on hosts with limited file descriptors or open TCP connections

---

## ⚖️ Considerations / Alternatives Considered

### Alternative A: Sequential Execution (Status Quo)
*Pros:* Simplest code path; deterministic ordering of results  
*Cons:* Wall time grows linearly with engine count; one timeout blocks all subsequent engines  
*Rationale for Rejection:* Unacceptable latency for runs with more than 3 engines

### Alternative B: `ThreadPoolExecutor`
*Pros:* Works with synchronous engine adapters without code changes  
*Cons:* Creates OS threads per engine call; does not integrate with the existing `asyncio` event loop; higher memory overhead  
*Rationale for Rejection:* The engine layer is already `async`; introducing threads would require a `run_in_executor` wrapper and add unnecessary complexity

### Alternative C: External Job Queue (Celery / RQ)
*Pros:* Persistent task state; horizontal scaling across workers  
*Cons:* Adds a broker dependency (Redis/RabbitMQ); out of scope for a local single-process tool  
*Rationale for Rejection:* The benchmarking tool is designed to run locally; a broker dependency violates the "no external services required" principle established in ADR 0001

---

## 📊 Impact Analysis

### 🟢 Positive Impacts
* **Throughput**: Concurrent engine execution reduces total benchmark wall time proportionally to `max_concurrent`
* **Resilience**: Circuit breaker prevents a flaky remote engine from consuming the full timeout budget on every run
* **Configurability**: `BenchmarkConfig.max_concurrent` lets operators tune parallelism to their host's network and CPU constraints

### 🔴 Negative Impacts / Trade-offs
* **Complexity**: Semaphore and circuit breaker add ~80 lines of state-management code to `runner.py`
* **Result Ordering**: `asyncio.gather` with `return_exceptions=True` does not guarantee results arrive in engine-list order when some engines time out; callers must reconcile results by engine ID

---

## 🔗 Related ADRs

* ADR 0003 — Benchmark Execution Orchestration and Flow Control
* ADR 0010 — Async HTTP Client Configuration
* ADR 0015 — Configuration Management

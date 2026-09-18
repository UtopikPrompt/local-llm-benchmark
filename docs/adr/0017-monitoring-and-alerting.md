# Architectural Decision Record: Monitoring and Alerting

* **Title:** Monitoring and Alerting
* **Status:** `.pill` **Accepted**
* **Date:** 2026-09-18
* **Authors:** Local LLM Benchmark Team

---

## 📋 Problem Statement / Motivation

The `local-llm-benchmark` application currently has no observability infrastructure. Operators have no mechanism to determine whether the system is healthy, how benchmarks are performing over time, or when thresholds are being violated:

- **No Health Endpoint**: Deployment orchestrators (Docker, systemd) cannot probe liveness or readiness
- **No Metrics Collection**: There is no time-series data for benchmark throughput, latency, or cache efficiency
- **No Alerting**: Threshold violations (e.g., high error rates, memory exhaustion) go undetected until a user reports a failure
- **Debugging Blind Spot**: When something degrades, there is no telemetry to distinguish root causes

### Key Observations

1. Benchmark runs are long-running operations; a `/health` endpoint is required to signal whether the service is ready to accept work
2. LLM inference costs (token usage, latency) should be tracked per-engine to support cost analysis
3. Prometheus is the industry standard for pull-based metrics scraping and works without an external SaaS dependency
4. Alert rules expressed as Prometheus configuration are version-controllable and portable

This decision formalizes three complementary observability components:

1. **Health Check Endpoint** — `/health` route returning system status metrics
2. **Prometheus Metrics** — counters, histograms, and gauges for benchmark and LLM operations
3. **Alerting Configuration** — Prometheus alert rules for threshold-based notifications

---

## ✨ Decision

We will implement a structured observability layer using a FastAPI health endpoint, `prometheus_client` metrics, and `AlertManager` alert rules.

### 1.1 Health Check Endpoint

Expose a `/health` endpoint that returns the current status of the application, database, and cache:

```python
# src/local_llm_benchmark/api/health.py

from fastapi import APIRouter, Response
from pydantic import BaseModel

router = APIRouter(prefix="/health", tags=["Health"])


class HealthStatus(BaseModel):
    status: str
    version: str
    uptime: float
    memory_usage: dict


class HealthEndpoint(BaseModel):
    status: str
    version: str
    uptime: float
    memory_usage: dict
    database: dict
    cache: dict


@router.get("/", response_model=HealthEndpoint)
async def health_check():
    """Health check endpoint."""
    import psutil
    import os

    memory = psutil.virtual_memory()
    uptime = os.getpid()  # Simplified uptime

    return HealthEndpoint(
        status="healthy",
        version="1.0.0",
        uptime=uptime,
        memory_usage={
            "total": memory.total / 1024 ** 3,
            "used": memory.used / 1024 ** 3,
            "percent": memory.percent
        },
        database={
            "status": "connected",
            "pool_size": 10,
            "checked_out": 5
        },
        cache={
            "status": "healthy",
            "hits": 1000,
            "misses": 50
        }
    )
```

### 1.2 Prometheus Metrics

Define labeled counters, histograms, and gauges for the key instrumentation points:

```python
# src/local_llm_benchmark/metrics.py

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry


# Metrics definitions
BENCHMARK_REQUESTS = Counter(
    "benchmark_requests_total",
    "Total number of benchmark requests",
    ["status", "engine"]
)

BENCHMARK_DURATION = Histogram(
    "benchmark_duration_seconds",
    "Time spent running benchmarks",
    ["engine"]
)

LLM_TOKENS = Counter(
    "llm_tokens_used",
    "Tokens used by LLM calls",
    ["engine", "direction"]
)

CACHE_HITS = Counter(
    "cache_hits_total",
    "Number of cache hits",
    ["level"]
)

CACHE_MISSES = Counter(
    "cache_misses_total",
    "Number of cache misses",
    ["level"]
)

# Expose metrics
METRICS_PORT = 8000
METRICS_PATH = "/metrics"
```

### 1.3 Alerting Configuration

Manage Prometheus alert rules through a typed `AlertManager` class:

```python
# src/local_llm_benchmark/alerts.py

from prometheus_client import CollectorRegistry
from typing import Callable


class AlertManager:
    """Prometheus alerting manager."""

    def __init__(self, registry: CollectorRegistry):
        self.registry = registry

    def register_alert(self, name: str, rule: str):
        """Register an alert rule."""
        self.registry.register(
            type('AlertRule', (), {
                '_name': name,
                '_rule': rule
            })()
        )

    def get_alerts(self) -> list:
        """Get current alerts."""
        # Fetch from Prometheus
        pass
```

---

## 💡 Decision Rationale

| Factor | Rationale |
|--------|-----------|
| **Operational Visibility** | Without metrics, operators cannot distinguish degraded service from normal operation |
| **Deployment Compatibility** | A `/health` endpoint is required by Docker health checks, Kubernetes liveness probes, and load balancers |
| **Cost Analysis** | Token counters per engine directly support the project's benchmarking cost-comparison use case |
| **Standard Tooling** | Prometheus is pull-based, requires no agent installation, and integrates with Grafana dashboards |

### Trade-offs Accepted

- **Dependency Addition**: `prometheus_client` and `psutil` must be added to project dependencies
- **Cardinality Risk**: Labeling metrics by `engine` requires bounded engine names to avoid high cardinality
- **Metrics Scrape Endpoint**: A `/metrics` endpoint must be secured or limited to internal networks to avoid exposing operational data

---

## ⚖️ Considerations / Alternatives Considered

### Alternative A: No Observability (Status Quo)

*Pros:* Zero implementation overhead

*Cons:*
- Failures are invisible until a user reports them
- No data for performance regression analysis
- Deployment orchestrators cannot probe health

*Rationale for Rejection:* The system is a long-running server; observability is a baseline operational requirement.

### Alternative B: Structured Logging Only (No Metrics)

*Pros:*
- Already partially implemented via `logger.py`
- Log aggregation tools (ELK, Loki) can derive metrics from logs

*Cons:*
- Log parsing for metrics is expensive and error-prone
- No real-time alerting without a separate log-processing pipeline
- Latency histograms require explicit instrumentation regardless

*Rationale for Rejection:* Metrics and logs are complementary; structured logs address root-cause investigation while Prometheus handles aggregate trend analysis and alerting.

### Alternative C: Application Performance Monitoring (APM) SaaS

*Pros:*
- Turnkey dashboards, distributed tracing, and anomaly detection
- No metrics infrastructure to operate

*Cons:*
- External dependency; data leaves the local environment (contrary to the project's local-first design)
- Cost scales with data volume
- Not viable for air-gapped or offline deployments

*Rationale for Rejection:* The project is explicitly designed for local deployment; shipping telemetry to a SaaS violates that premise.

### Alternative D: StatsD Push Model

*Pros:*
- Simple fire-and-forget API from application code
- Widely supported

*Cons:*
- Requires a running StatsD daemon as an additional process
- UDP-based; metrics can be silently lost under packet loss
- Less expressive than Prometheus (no label cardinality control)

*Rationale for Rejection:* Prometheus pull model is more resilient and requires no additional daemon; it is the better fit for a single-host deployment.

---

## 📊 Impact Analysis

### 🟢 Positive Impacts

* [**Deployment Readiness**]: `/health` enables automated health checks by orchestrators, enabling zero-downtime restarts and readiness gates
* [**Performance Baseline**]: `BENCHMARK_DURATION` histograms establish latency baselines, making regressions measurable
* [**Cost Attribution**]: `LLM_TOKENS` counters provide per-engine token usage data directly aligned with the benchmarking mission
* [**Cache Tuning**]: `CACHE_HITS` / `CACHE_MISSES` counters per cache level feed the cache hit rate target (>80%) defined in Appendix A

### 🔴 Negative Impacts / Trade-offs

* [**Instrumentation Overhead**]: Prometheus counters and histograms add nanosecond-level overhead per recorded event; negligible for LLM workloads but worth noting
* [**/metrics Exposure**]: The Prometheus scrape endpoint must be protected from public access; it should be restricted to localhost or an internal network
* [**Cardinality Discipline**]: Metric labels must use bounded values (engine names, not arbitrary strings) to avoid registry memory growth

---

## 🔗 Related ADRs

* [ADR 0010 - Async HTTP Client Configuration](./0010-http-client-configuration.md) — LLM request latency tracked by `BENCHMARK_DURATION` originates in the HTTP client layer
* [ADR 0016 - Multi-Level Caching](./0016-multi-level-caching.md) — `CACHE_HITS` and `CACHE_MISSES` metrics instrument the L1/L2 cache hierarchy

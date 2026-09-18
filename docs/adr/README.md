# Architecture Decision Records (ADRs)

This directory tracks the major architectural decisions that guided the development of the Local LLM Benchmark. Each record documents *why* a specific technical approach was chosen, ensuring that design choices are traceable, reviewable, and consistent.

## 📜 Table of Contents

| ID | Title | Status | Summary |
| :--- | :--- | :--- | :--- |
| **ADR 0001** | Benchmarking Framework Design | Accepted | Defines the high-level goal and scope of the entire benchmarking system. |
| **ADR 0002** | ESM Module Architecture | Accepted | Establishes the principle that components (Engines, Benchmarks) must be isolated Service Modules (ESMs). |
| **ADR 0003** | Benchmark Execution Orchestration and Flow Control | Accepted | Dictates the mechanism for running benchmarks, managing both full-run and per-challenge execution states. |
| **ADR 0004** | Global Data Schema and State Contract | Accepted | Defines the canonical data structure used everywhere: database results, API payloads, and client state. |
| **ADR 0005** | Evaluation Metrics Pipeline and Aggregation Rules | Accepted | Formalizes the mathematical rules for transforming raw execution data into final, reportable metrics. |
| **ADR 0006** | API Design and Service Boundaries | Accepted | Enforces separation between the HTTP layer (Controller) and the core business logic (Service). |
| **ADR 0007** | Module Loading and Dependency Graph Management | Accepted | Details the dynamic discovery pattern used to load new benchmarks, tasks, and engines without modifying core startup code. |
| **ADR 0008** | Engine Management API | Proposed | Establishes the RESTful `/api/engines` contract for the full CRUD lifecycle of engine definitions. |
| **ADR 0009** | Engine CRUD User Interface | Proposed | Implements the client-side, event-driven engine management workflow in the benchmark view. |
| **ADR 0010** | Async HTTP Client Configuration | Accepted | Optimizes `httpx.AsyncClient` configuration for high-concurrency LLM benchmarking scenarios. |
| **ADR 0011** | Test Coverage Organization and Verification Goals | Accepted | Formalizes test coverage goals, organization structure, and verification metrics for the benchmarking framework. |
| **ADR 0012** | API Response Caching with TTL and Decorator Pattern | Proposed | Implements LRU response caching with per-call TTL to reduce redundant LLM API calls. |
| **ADR 0013** | Database Query Optimization | Proposed | Formalizes indexing, N+1 prevention, and pagination strategies for database efficiency. |
| **ADR 0014** | Frontend Bundle Optimization | Accepted | Adopts tree shaking, esbuild code splitting, and lazy loading to reduce JavaScript bundle size and improve load time. |
| **ADR 0015** | Configuration Management | Accepted | Establishes environment-based configuration via `pyproject.toml` and typed Pydantic config classes for all application settings. |
| **ADR 0016** | Multi-Level Caching | Accepted | Implements a hierarchical L1 (in-memory) → L2 (persistent) cache with entity-scoped invalidation to improve cache hit rates. |
| **ADR 0017** | Monitoring and Alerting | Accepted | Introduces a `/health` endpoint, Prometheus metrics (counters, histograms, gauges), and alert rules for system observability. |
| **ADR 0018** | Benchmark Orchestration & Control | Accepted | Adopts `asyncio.gather` with per-engine timeouts, a `BenchmarkConfig.max_concurrent` semaphore guard, and a circuit breaker to prevent cascading failures. |
| **ADR 0019** | LLM Inference Optimization | Accepted | Introduces batched requests, dynamic per-benchmark-type temperature, persistent KV-cache sessions, and optional quantisation (GGUF/INT4/INT8) support. |
| **ADR 0020** | Performance Testing | Accepted | Establishes baseline recording, z-score regression detection, and per-endpoint configurable SLO thresholds for automated performance regression testing. |

---

*(Continue with the standard ADR template content below this summary.)*
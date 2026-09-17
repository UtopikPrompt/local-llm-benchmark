# Architectural Decision Records (ADRs)

This directory tracks the major architectural decisions that guided the development of the Local LLM Benchmark. Each record documents *why* a specific technical approach was chosen, ensuring that design choices are traceable, reviewable, and consistent.

## 📜 Table of Contents

| ID | Title | Status | Summary |
| :--- | :--- | :--- | :--- |
| **ADR 0001** | Benchmarking Framework Design | Accepted | Defines the high-level goal and scope of the entire benchmarking system. |
| **ADR 0002** | ESM Module Architecture | Accepted | Establishes the principle that components (Engines, Benchmarks) must be isolated Service Modules (ESMs). |
| **ADR 0003** | Benchmark Execution Orchestration and Flow Control | Proposed | Dictates the mechanism for running benchmarks, managing both full-run and per-challenge execution states. |
| **ADR 0004** | Global Data Schema and State Contract | Proposed | Defines the canonical data structure used everywhere: database results, API payloads, and client state. |
| **ADR 0005** | Evaluation Metrics Pipeline and Aggregation Rules | Proposed | Formalizes the mathematical rules for transforming raw execution data into final, reportable metrics. |
| **ADR 0006** | API Design and Service Boundaries | Proposed | Enforces separation between the HTTP layer (Controller) and the core business logic (Service). |
| **ADR 0007** | Module Loading and Dependency Graph Management | Proposed | Details the dynamic discovery pattern used to load new benchmarks, tasks, and engines without modifying core startup code. |
| **ADR 0008** | Engine Management API | Proposed | Establishes the RESTful `/api/engines` contract for the full CRUD lifecycle of engine definitions. |
| **ADR 0009** | Engine CRUD User Interface | Proposed | Implements the client-side, event-driven engine management workflow in the benchmark view. |

---

*(Continue with the standard ADR template content below this summary.)*
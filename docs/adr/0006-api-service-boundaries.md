# Architectural Decision Record (ADR) - API Design and Service Boundaries

**Title:** API Design and Service Boundaries
**Status:** Proposed
**Date:** 2026-09-14
**Authors:** AI Assistant

---

## 🎯 1. Context

*The system needs a clear contract layer between the public-facing API and the complex, internal business logic.*

The backend is split between the API Controller (`controller.py`), which handles HTTP request mapping, and the Service Layer (`services.py`), which contains the business rules. A rigid boundary is required to prevent the Controller from becoming bloated with logic or the Service Layer from being accessed directly via HTTP endpoints, ensuring testability and clear responsibility.

## ✨ 2. Decision

The boundary will be enforced such that:
1.  The API Controller's *only* job is **Request/Response Mapping**: validating incoming request payloads and mapping successful business calls to appropriate HTTP status codes and formats.
2.  The Service Layer's *only* job is **Business Logic Execution**: performing complex tasks, coordinating data, and executing business rules, irrespective of the transport mechanism (HTTP, message queue, etc.).
3.  All internal components must communicate via strongly typed function calls (interfaces), not by calling each other's private methods.

## ⚖️ Considerations / Alternatives Considered

### Alternative A: Monolithic Controller
*Pros:* Simplest to implement initially.
*Cons:* High coupling. Changes in one area (e.g., result formatting) could inadvertently affect unrelated business logic, leading to a massive, untestable component.
*Rationale for Rejection:* Violates the Single Responsibility Principle and inhibits maintainability.

### Alternative B: Direct Component Invocation
*Pros:* Minimal overhead.
*Cons:* Removes the ability to gate the service layer with authentication, rate limiting, or logging logic that should happen at the API boundary.
*Rationale for Rejection:* The API layer provides essential cross-cutting concerns that must be enforced.

## 🚀 Consequences

### 🟢 Positive Consequences
* Clear separation of concerns, allowing independent development and testing of API endpoints vs. core logic.
* Easier implementation of cross-cutting concerns (logging, caching, security).

### 🔴 Negative Consequences / Trade-offs
* Requires developers to be mindful of this strict separation, potentially leading to an initial increase in boilerplate code (wrapper functions).

## 🔗 Related ADRs

- ADR 0001: Benchmarking Framework Design (Project Overview).
- ADR 0002: ESM Module Architecture (Structure guidance).
- ADR 0003: Benchmark Execution Orchestration and Flow Control.
- ADR 0004: Global Data Schema and State Contract (Defines the input/output types used by the boundary).
- ADR 0005: Evaluation Metrics Pipeline and Aggregation Rules (Defines what the service layer processes).
- ADR 0007: Module Loading and Dependency Graph Management (Defines how modules are loaded and executed).
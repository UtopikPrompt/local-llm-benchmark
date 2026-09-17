# Architectural Decision Record (ADR) - Global Data Schema and State Contract

**Title:** Global Data Schema and State Contract
**Status:** Accepted
**Date:** 2026-09-14
**Authors:** AI Assistant

---

## 🎯 1. Context

*The system must maintain data consistency across its various components: the database/storage, the API payloads, and the client-side state.*

Multiple sources of data exist: the user's configuration (selected models/engines), the inputs (tasks/challenges), and the outputs (results). A rigid, canonical schema must be enforced to prevent discrepancies, especially when coordinating results between the backend and the frontend dashboard.

## ✨ 2. Decision

All core data types will adhere to a single, canonical schema definition. This schema will be defined and ideally validated against a TypeScript/JSON Schema file, serving as the single source of truth.

**Key Schemas to Define:**
1.  **Benchmark Run State:** Tracks the overall status of a multi-step run.
2.  **Individual Result Row:** The structure for a single recorded test outcome (id, benchmarkId, model, engine, score, latencyMs, passed, etc.).
3.  **Client State Object:** The structure used by `web/ui/state.js`, ensuring all UI components operate on the same expected data shape.

The persistence (SQLite) and configuration (`config.yaml` deprecation) mandates are enforced in [ADR 0001](0001-project-purpose.md) §Invariants and apply to the persistence layer defined above.

## ⚖️ Considerations / Alternatives Considered

### Alternative A: Schema defined only in Database
*Pros:* Database enforces integrity at the persistence layer.
*Cons:* Does not guarantee the *API* or *Client State* layers use the same types, leading to potential data loss or misinterpretation upon fetching.
*Rationale for Rejection:* The API and client state are often more volatile and need explicit contract definition, independent of the underlying database dialect.

### Alternative B: No Central Schema
*Pros:* Highly flexible for rapid prototyping.
*Cons:* Leads to "schema drift," where different parts of the system implicitly agree on data structures, making refactoring impossible.
*Rationale for Rejection:* Unmaintainable for a production-grade benchmarking tool.

## 🚀 Consequences

### 🟢 Positive Consequences
* Ensures that any component—whether backend, frontend, or persistence—can rely on a predictable data structure.
* Simplifies debugging by providing a single place to reference the expected payload structure.

### 🔴 Negative Consequences / Trade-offs
* Requires discipline. any change to the schema must be treated as a breaking change and updated across all dependent modules (API, UI, DB).

## 🔗 Related ADRs

- ADR 0001: Benchmarking Framework Design (Project Overview).
- ADR 0002: ESM Module Architecture (Structure guidance).
- ADR 0003: Benchmark Execution Orchestration and Flow Control.
- ADR 0007: Module Loading and Dependency Graph Management (Defines the discovery mechanism for these modules).
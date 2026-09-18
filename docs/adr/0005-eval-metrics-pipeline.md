# Architectural Decision Record (ADR) - Evaluation Metrics Pipeline and Aggregation Rules

**Title:** Evaluation Metrics Pipeline and Aggregation Rules
**Status:** [`.pill` Status: Accepted]
**Date:** 2026-09-14
**Authors:** AI Assistant

---

## 📋 Problem Statement / Motivation

*The raw output from a benchmark run must be transformed into meaningful, comparative metrics displayed on the dashboard.*

Raw output contains granular data points (e.g., raw response text, individual task scores, latency for each sub-step). However, the user needs a summarized, reliable view (e.g., average score, overall pass rate, comparative ranking). This ADR defines the immutable rules for this transformation.

## ✨ Decision

All raw data processing for final metrics must happen in a dedicated, isolated service (or module, e.g., `local_llm_benchmark/eval/quality.py`). The process will be a multi-stage pipeline:
1.  **Raw Data Ingestion:** Accept the raw list of results (per-task, per-model, per-engine).
2.  **Metric Calculation:** Apply specific formulas (e.g., average score, weighted score) defined for each metric type.
3.  **Normalization & Serialization:** Standardize the calculated metrics into the final schema (e.g., rounding scores, converting status flags).

The persistence and configuration mandates are enforced in [ADR 0001](0001-project-purpose.md) §Invariants.

## 💡 Decision Rationale

- **Primary Factor:** Integrity through centralized metrics calculation
- **Secondary Factor:** Auditability with preserved re-computation capability
- **Trade-offs Accepted:** High importance of the `eval/quality.py` module requiring rigorous testing

## ⚖️ Considerations / Alternatives Considered

### Alternative A: Calculate Metrics on the Frontend
*Pros:* Offloads processing from the backend.
*Cons:* High risk of inconsistency; the frontend might misinterpret the aggregation rules, leading to distrust in the displayed numbers.
*Rationale for Rejection:* Metrics calculation is a core business rule and must be immutable and executed on the trusted backend.

### Alternative B: Store Pre-calculated Metrics
*Pros:* Extremely fast read access.
*Cons:* Breaks the ability to easily re-run analysis or audit historical results if the scoring rules change.
*Rationale for Rejection:* While good for performance, we must preserve the ability to re-run calculations with updated logic.

## 📊 Impact Analysis

### 🟢 Positive Impacts
* Guarantees that all reported metrics adhere to the same set of mathematical and logical rules, regardless of where or when the data is queried.
* Decouples the reporting logic from the data storage layer.

### 🔴 Negative Impacts / Trade-offs
* The `eval/quality.py` module will become highly important and sensitive to change, requiring rigorous unit testing.

## 🔗 Related ADRs

- ADR 0001: Benchmarking Framework Design (Project Overview).
- ADR 0002: ESM Module Architecture (Structure guidance).
- ADR 0003: Benchmark Execution Orchestration and Flow Control (Defines when the metrics are calculated).
- ADR 0004: Global Data Schema and State Contract (Defines the input/output format).
- ADR 0007: Module Loading and Dependency Graph Management (This ADR's dependencies are defined here).

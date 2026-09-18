# Architectural Decision Record (ADR) - Project Overview

**Title:** Benchmarking Framework Design
**Status:** [`.pill` Status: Accepted]
**Date:** 2026-09-16
**Authors:** AI Assistant

---

## 📋 Problem Statement / Motivation

The goal of this entire project is to create a robust and comprehensive benchmarking framework. The system must compare the performance and quality of various LLM engines and the models running on those engines. All persistent data, including benchmark results and metadata, **MUST** be stored using **SQLite** as the single source of truth, replacing all prior configuration and data layers (including usage of `config.yaml`). The core complexity remains comparing results across models and challenges.

## ✨ Decision

The project will function as a multi-faceted benchmarking tool that:
1. Allows the user to select multiple LLM models and multiple benchmarks/challenges.
2. Orchestrates the execution of all selected combinations.
3. **Mandates SQLite:** All data storage, including benchmarking results, must exclusively utilize a SQLite database.
4. **Configuration Source:** System configuration and runtime parameters must be managed programmatically or via code, and the deprecated `config.yaml` file is no longer to be used for runtime data or configuration.
5. Runs all selected tasks across all selected models simultaneously (or in managed batches).
6. Collects and aggregates results (score, latency, pass/fail status) for every unique engine/model/challenge combination to provide a holistic comparison dashboard.

## 💡 Decision Rationale

- **Primary Factor:** Maintainability and scalability through centralized SQLite persistence
- **Secondary Factor:** Eliminating configuration file dependencies for runtime flexibility
- **Trade-offs Accepted:** Increased runtime complexity from concurrent execution management

## ⚖️ Considerations / Alternatives Considered

### Alternative A: Single Run/Single Model Focus
*Pros:* Simplicity in execution and reporting.
*Cons:* Cannot provide a multi-dimensional comparison, limiting the benchmark's utility for comparative analysis.
*Rationale for Rejection:* This defeats the primary goal of comparing *engines* and *models*.

### Alternative B: Highly Modular, Manual Triggering
*Pros:* Maximum control over every single test run.
*Cons:* Requires significant UI/backend complexity to manage the combinatorial explosion of test cases (Engine * Model * Challenge).
*Rationale for Rejection:* While granular, the system needs an automated, structured way to manage the execution graph, which the current design of running all tasks simultaneously addresses better.

## 📊 Impact Analysis

### 🟢 Positive Impacts
* Provides a single source of truth for comparing different LLM providers and models side-by-side.
* Establishes a clear API contract for test case execution across various backends.

### 🔴 Negative Impacts / Trade-offs
* **Complexity:** The runner logic (`runner.py`/`services.py`) must handle concurrent or semi-concurrent execution flows, increasing potential points of failure.
* **Execution Time:** Running all combinations might be time-consuming.

## ⚙️ Invariants

These are stable, cross-cutting decisions that every ADR must uphold and must not drift from. They are recorded here as the single source of truth; other ADRs that encode them link back to this record rather than restating them.

1. **SQLite Persistence:** All persistent data storage, state management, and long-term records MUST use SQLite as the exclusive data store. No other persistence mechanism (bare JSON/YAML files, direct OS writes) is permitted for long-term data storage.
2. **Configuration Deprecation:** The use of `config.yaml` for configuration is formally deprecated and prohibited. All configuration must be sourced exclusively from environment variables or compile-time constants.

These two invariants originate from ADR 0001's decision and are enforced by ADRs 0002–0007.

## 🔗 Related ADRs

* ADR 0002: ESM Module Architecture (The structure adopted for service modules).
* ADR 0003: Benchmark Execution Orchestration and Flow Control.

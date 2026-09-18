# Architectural Decision Record (ADR) - Benchmark Execution Orchestration and UI Specification

**Title:** Benchmark Execution Orchestration and UI Specification
**Status:** [`.pill` Status: Accepted]
**Date:** 2026-09-14
**Authors:** AI Assistant (Updated from initial draft)

---

## 📋 Problem Statement / Motivation

*The goal is to define the precise architecture and user experience for running and viewing benchmark results, especially the flow between different execution modes (full batch vs. selective/incremental).*

The system must efficiently orchestrate benchmark runs while providing a granular, multi-panel user interface to support various selection criteria and real-time feedback.

## ✨ Decision

The core execution flow will be managed by a centralized **Orchestrator Service** (in `local_llm_benchmark/runner.py`/`local_llm_benchmark/server/api/services.py`). This service determines the correct sequence and type of execution (full batch vs. per-challenge feedback) based on the user's explicit selections from the UI components defined below. The frontend must manage state synchronization between the UI components and the backend API endpoint (`/api/run`).

See [ADR 0001](0001-project-purpose.md) §Invariants for the mandatory persistence (SQLite) and configuration (`config.yaml` deprecation) requirements.

## 💡 Decision Rationale

- **Primary Factor:** Maintainability through centralized orchestration
- **Secondary Factor:** User experience via multi-panel coordinated UI
- **Trade-offs Accepted:** Increased orchestrator complexity managing dual execution modes

## ⚖️ Considerations / Alternatives Considered

### Alternative A: Single Full-Batch Mode Only
*Pros:* Simpler UI and execution.
*Cons:* Cannot support per-challenge incremental runs or real-time status.
*Rationale for Rejection:* The system needs to support both a full batch run and granular per-challenge feedback.

### Alternative B: Decentralized Run Triggers
*Pros:* Maximum flexibility for the caller.
*Cons:* No single point to manage the Engine × Model × Challenge combinatorial graph.
*Rationale for Rejection:* A centralized Orchestrator Service keeps execution state coherent and testable.

## 📊 Impact Analysis

### 🟢 Positive Impacts
* A single Orchestrator Service coordinates full-batch and per-challenge flows.
* The `/api/run` contract drives frontend state synchronization.

### 🔴 Negative Impacts / Trade-offs
* The orchestrator must handle both execution modes, increasing its surface area.
* UI state must stay in sync with backend progress.

## 🔗 Related ADRs

* ADR 0001: Benchmarking Framework Design (Project Overview).
* ADR 0002: ESM Module Architecture (Structure guidance).
* ADR 0004: Global Data Schema and State Contract (Defines run state and result shapes).
* ADR 0006: API Design and Service Boundaries (Defines the Orchestrator Service boundary).

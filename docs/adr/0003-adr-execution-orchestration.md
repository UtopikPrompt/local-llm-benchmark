# Architectural Decision Record (ADR) - Benchmark Execution Orchestration and UI Specification

**Title:** Benchmark Execution Orchestration and UI Specification
**Status:** Draft (Needs Review)
**Date:** 2026-09-14
**Authors:** AI Assistant (Updated from initial draft)

---

## 🎯 1. Context

*The goal is to define the precise architecture and user experience for running and viewing benchmark results, especially the flow between different execution modes (full batch vs. selective/incremental).*

The system must efficiently orchestrate benchmark runs while providing a granular, multi-panel user interface to support various selection criteria and real-time feedback.

## ✨ 2. Decision

The core execution flow will be managed by a centralized **Orchestrator Service** (in `local_llm_benchmark/runner.py`/`local_llm_benchmark/server/api/services.py`). This service determines the correct sequence and type of execution (full batch vs. per-challenge feedback) based on the user's explicit selections from the UI components defined below. The frontend must manage state synchronization between the UI components and the backend API endpoint (`/api/run`).

## 🌐 3. Frontend/UI Specification (New)

The dashboard is structured into three main, coordinated panels:

### 🅰. Dashboard Panel (The Overview)
This panel serves as the primary landing page for results aggregation.
1.  **Filter Container:** A top-level container must house a search box for global filtering across all displayed results.
2.  **Results Table:** The main area must display a comprehensive, sortable table showing *all* accumulated benchmark results.

### 🅱. Benchmark Panel (The Control Center)
This panel controls the parameters for a run.
1.  **Left Menu (Selection Controls):**
    *   **Engine List:** A comprehensive list of available engines (e.g., OpenAI, local-llm).
    *   **Model Selection:** A list of models grouped by engine. Each model must have an associated selection checkbox.
    *   **Global Model Selector:** A checkbox for **'All Models'** to select all available models, overriding individual model checkboxes.
2.  **Challenges Selection (Main Container):**
    *   A list of all available challenges/tasks. Each challenge must have an associated selection checkbox.
    *   A global checkbox for **'All Challenges'** to select all available tasks.
3.  **Action Button:** A prominent button labeled **'Start Challenges Batch'** that triggers the full execution cycle.
4.  **Status Area:** A dedicated area must display the real-time status (progress bar, status text) for *each individual running challenge* in the batch.

### Ⓒ. Challenges Panel (The Detail View)
This panel provides a dedicated, comprehensive view of all available challenges/tasks, separate from the run control panel.
1.  **Challenge List:** A straightforward list displaying all available challenges, ideally allowing for per-challenge status viewing or selection.

## ⚖️ Considerations / Alternatives Considered

*(Content retained from original ADR)*

## 🚀 Consequences

*(Content retained from original ADR)*

## 🔗 Related ADRs

*(Content retained from original ADR)*
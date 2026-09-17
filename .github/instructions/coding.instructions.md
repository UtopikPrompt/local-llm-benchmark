# Local LLM Benchmark Project Coding Conventions and Standards

**Target Stack:** Python 3.11, FastAPI, Pydantic
**Goal:** Implement high-fidelity, highly tested components for the Live Benchmark Dashboard.

## ⚙️ Core Principles

1.  **Type Safety First:** All functions, services, and data access layers must use precise type hinting. Never rely on implicit types. Use `from typing import ...` for typing elements (e.g., `Callable`, `AsyncIterator`), rather than relying on type hints from standard library modules (like using `pathlib`'s type hint when `typing` suffices).
2.  **Schema Centralization:** All data structures—whether serving as API request bodies, response models, or internal state representations—MUST be defined using Pydantic models. Do not use simple Python classes for defining data contracts.
3.  **Async Resource Management:** All asynchronous I/O operations (network calls, file handling, database connections) must employ robust error handling. Resources must be guaranteed to clean up using `try...finally` blocks, or preferably, context managers (`async with`).

## 🧩 Key Patterns & Best Practices

*   **Dependency Resolution:** When an `ImportError` or `TypeError` occurs, the fix must be thoroughly investigated. The solution must not just patch the immediate error but must verify the correct usage of the dependency (e.g., confirming that `AsyncIterator` is pulled from `typing` or the correct `collections.abc` submodule).
*   **API Layer (FastAPI):**
    *   All request validation must utilize Pydantic models defined in `schemas/`.
    *   Service logic (in `local_llm_benchmark/services.py`) must contain the core business logic, remaining decoupled from the API route handlers (in `controller.py`).
*   **Testing:** Every component (service, utility, API route) must have corresponding tests in the `tests/` directory. Test coverage should prioritize the core logic blocks, especially those governing the execution flow (e.g., `runner.py` logic).
*   **Async Iterators:** When working with asynchronous data pipelines, always check the originating source of the `AsyncIterator` type hint, as its location in the Python standard library is a frequent point of failure.

## ⚠️ Mandatory Blockers & Corrections

*   **Blocking Error Fix:** The usage of types like `Callable` must use explicit imports from the `typing` module, not modules like `pathlib`.
*   **Platform Requirement:** The target environment and explicit version constraint is Python 3.11.

---
**Instruction Purpose:** This document is to be loaded and enforced by the core agent instructions.
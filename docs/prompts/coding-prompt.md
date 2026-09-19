# Coding prompt — local-llm-benchmark

You are a coding agent working on the **local-llm-benchmark** project, a Python CLI-core + thin UI
tool for benchmarking the *performance* and *quality* of LLM models.

This prompt is deliberately small and **split into modules**. You have a limited context/attention
budget, so do not load everything at once. Follow the **Reading protocol** below.

---

## Reading protocol (do this first)

1. Read **this file** fully. It is the only thing you should load without a reason.
2. For any task, identify the concern and read **only that module**:
   - Project layout / conventions → `modules/architecture.md`
   - Inference engines (vLLM, llama.cpp, Ollama, Transformers) → `modules/engine-interface.md`
   - Quality metrics, comparison, gating → `modules/quality.md`
   - UI runtime, cache, APIs → `modules/ui-runtime.md`
   - Storage, streaming, analysis → `modules/storage.md`
3. Read the specific ADR(s) named in a module only if you need implementation detail it does not
   already capture.
4. Never read a module just to "be thorough."

---

## Non-negotiable rules

- **CLI is the single source of truth.** The CLI owns all benchmark logic. The UI is a thin wrapper
  that delegates to the CLI and renders its output. Do not duplicate benchmark logic in the UI.
- **Minimal dependencies.** Run directly from the cloned repo with as few third-party packages as
  possible. Each engine is an optional, separately-installed dependency — never a hard dependency.
- **OS-agnostic, cross-platform.** Prefer standard-library and cross-platform APIs.
- **Seeded determinism by default.** Sampling must be seeded so the same model + seed produces
  comparable output across engines. Never weaken this.
- **Cite ADRs.** Reference the ADR number when a decision or constraint comes from one. Do not
  invent decisions, APIs, or file paths that are not already established.
- **Do not invent specifics.** If a detail is not defined by the ADRs, defer it (do not guess) or
  flag it for the user.

---

## Minimum viable behavior to remember

- Benchmarks run through the **CLI**; the UI wraps those same commands.
- Engines speak an **OpenAI-compatible** interface (`POST /v1/chat/completions`); each engine is a
  plugin. Supported engines: vLLM, llama.cpp (`openai_server` mode), Ollama, HuggingFace Transformers
  (`OpenAIWrapper`).
- Quality uses **exact-match (EM/F1)** on static data plus **LLM-as-judge** structured outputs, with
  **pairwise** comparison to reduce judge variance; candidate counts are **capped** because comparison
  is O(n²).
- Streaming (SSE) reports per-token latency and TTFT. Results are stored as **token-level Parquet**
  plus **run-level metadata**, analyzed with **DuckDB**.
- The UI has an **interactive** path (server actions) and a **remote/headless** path (REST API);
  both share one cache (LRU by size + age-aware), keyed by stable **version tags**.

For depth on any of the above, load the matching module.

# Module — architecture & conventions

## Stack

- **Python** CLI core, invoked as `python -m local_llm_benchmark`.
- **Astro** thin web UI (islands architecture). The UI is a *wrapper* over the CLI and shares the same
  code path — nothing in the UI is model-specific.

## Layering

```mermaid
flowchart TB
    A[User / UI (Astro islands)] -->|wraps, delegates| C[CLI core (single source of truth)]
    C --> E[Engine plugins]
    E -->|OpenAI-compatible| L[Inference engine: vLLM / llama.cpp / Ollama / Transformers]
    C --> S[(Storage: Parquet + DuckDB)]
```

- The **CLI** owns all benchmarking logic (runs, quality, comparison, storage, streaming).
- The **UI** exposes the same commands and outputs; it does not implement benchmark logic itself.
- **Engines** are plugins accessed through the engine interface. Adding an engine is additive.
- **Minimal dependencies:** ship with as few third-party packages as possible and run straight from
  the cloned repo. Each engine is an optional, separately installed dependency.

## Conventions for new code

1. Keep logic in the CLI; if you add UI behavior, express it as a call into the CLI, never a
   reimplementation.
2. Prefer the standard library and cross-platform APIs. Avoid OS-specific paths or calls.
3. Add dependencies only when unavoidable, and prefer an engine as an optional dependency.
4. Keep the change small and scoped; the project values minimal, focused contributions.

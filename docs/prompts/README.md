# Coding prompts

Token- and attention-budget efficient coding prompts for the **local-llm-benchmark** project.

The project targets **small LLM models** (which are also the benchmark subjects), so the prompt is
designed to fit a small context window and load only what a task needs.

## Layout

| File | Purpose |
| --- | --- |
| [`coding-prompt.md`](coding-prompt.md) | Entry point. Small, fully self-contained core + reading protocol. Load this only. |
| `modules/architecture.md` | Stack, layering, conventions. |
| `modules/engine-interface.md` | OpenAI-compatible engine contract and supported engines. |
| `modules/quality.md` | Quality dimensions, hybrid scoring, comparison, gating. |
| `modules/ui-runtime.md` | UI runtime paths, version tags, shared cache. |
| `modules/storage.md` | Streaming, Parquet/DuckDB storage. |

## How to use

1. Load **`coding-prompt.md`** (it contains the reading protocol).
2. Read **only the module** relevant to the task.
3. Read the cited ADR(s) only when implementation detail is needed.

All content is grounded in the ADRs under `docs/adr/`. Cite ADR numbers; do not invent decisions or
paths.

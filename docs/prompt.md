# Prompt: Migrate local-llm-benchmark to TypeScript (SvelteKit)

Full context for building the new static, browser-only benchmark tool. See
[ADR 0001](./adr-0001-migration-to-typescript.md) for the rationale and
decisions.

## Decisions

- **Stack:** Vite + SvelteKit + TypeScript, managed with `pnpm`.
- **Charts:** Chart.js.
- **Deploy:** deploy the `build/` folder to the **`pages`** branch via
  `github-pages-deploy-action` (for a repo named `local-llm-benchmark`, this
  serves at `<owner>.github.io`).
- **Persistence:** `IndexedDB` (via `idb`) for results, engines, models, and
  corpus config. Optional JSON export on user request.
- **Engine:** rebuild the core engine in TypeScript.
- **CORS:** browser `fetch` to the local engine requires `OLLAMA_ORIGINS="*"`
  (Ollama) or `--cors` (LM Studio).

## Domain model (port from the Python implementation)

- **Engine** (`name`, `base_url`, `model`, `timeout=60`, `max_concurrent=1`).
- **Judge** (`name`, `base_url`, `model`, `timeout=60`) — optional quality judge.
- **Task** (`id`, `category`, `prompt`, `system`, `expected`, `validate`).
  Categories: `doc`, `code`, `qa`, `math`. Default corpus has 8 tasks.
- **Row** (one per trial): `engine`, `model`, `judge`, `task_id`, `category`,
  `prompt`, `expected`, `output`, `ttft_s`, `tok_per_s`, `iters_per_s`,
  `quality_passed`, `quality_deterministic`, `quality_judge`, `quality_note`.

### Measurements (from `benchmarks/speed.py`)

- **TTFT** = time to first token.
- **tokens/s** = tokens / elapsed.
- **iters/s** = trials / total_elapsed.
- Uses a semaphore with `max_concurrent`.

### Pages

1. `/` — Dashboard: results with filters (engine, model, category, quality,
   judge) + Chart.js charts.
2. `/run` — Configure & run a benchmark, streaming progress.
3. `/corpus` — Configure tasks and corpus.

## Conventions

- Keep TypeScript strict, no `any` where avoidable.
- All engine logic lives under `src/lib/engines/` mirroring the old
  `engines/` package.
- State access goes through the storage layer in `src/lib/storage/`.
- Tests go under `src/test/` using SvelteKit's test runner + `@testing-library/svelte`.

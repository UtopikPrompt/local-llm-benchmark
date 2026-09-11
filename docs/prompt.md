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

## Status

The migration is **partially complete but not yet functional**. The scaffolding
is in place, but core logic, tests, and type integrity are unfinished. Neither
`pnpm test` nor `pnpm check` passes.

### Done

- **Build tooling** is configured: `package.json` uses Vite, SvelteKit
  `^2.12`, TypeScript `^5.7`, `adapter-static`, Chart.js, `idb`, and
  `@testing-library/svelte`. Scripts (`dev`, `build`, `test`, `check`, `lint`)
  are all defined.
- **New TS engine layer** exists under `src/lib/engines/` (`engines.ts`,
  `index.ts`, `judge.ts`, `models.ts`, `openai_compat.ts`) mirroring the old
  Python `engines/` package.
- **Storage layer** scaffolded in `src/lib/storage/` (`db.ts`, `index.ts`).
- **Pages** created: dashboard `/` (`+page.svelte`, 284 lines), `/corpus`,
  `/run`.
- On branch `feat/typescript-migration`.

### Not done / broken

1. **`pnpm test` fails — no tests written.** Vitest reports _"No test files
   found_" (`include: src/**/*.{test,spec}.{js,ts}`). The old Python tests in
   `tests/` are not migrated, and only `src/test/setup.ts` exists. **0 of ~14
   test modules ported.**
2. **`pnpm check` fails with 57 errors + 19 warnings** across 13 files. The
   dashboard UI imports types (`BenchmarkConfig`, `Row`, `EngineConfig`,
   `Judge`, `max_concurrent`, `NetworkError`) that don't resolve or don't
   match. Representative issues:
   - Missing module exports (e.g. `EngineConfig`, `Judge`, `max_concurrent`)
   - Implicit `any` parameters (`index`, `s`, `id`)
   - `Task` objects missing required `system`/`validate` fields
   - String-vs-array conversions, `idb` type mismatches, Chart.js canvas type
3. **Python code not fully removed.** `test_nav.py` and the entire
   `local_llm_benchmark/` Python package remain in the workspace.
4. **Core benchmark logic appears incomplete.** `engines.ts` is only 24 lines —
   the actual runner/benchmark execution logic (TTFT, tokens/s, iters/s,
   semaphore concurrency) doesn't appear implemented in TS yet.

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

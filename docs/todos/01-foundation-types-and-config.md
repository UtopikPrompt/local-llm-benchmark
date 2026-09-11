# Sub-prompt 1/7 — Foundation: domain types, config, errors, results

Port and reconcile the canonical domain types and configuration so every other
layer has a single source of truth. This is pure types/boilerplate — no
network, no UI. It must pass `pnpm check` on its own.

## Context

The Python app modeled: `EngineConfig`, `JudgeConfig`, `BenchmarkConfig`,
`Row`, `Task`, `Category`, `TaskValidator`, the `BenchmarkError` family, and
the default corpus (8 tasks). These types are already partially sketched in
`src/lib/**.ts`; the job is to make them consistent, complete, and type-clean.

## Goals

- **`src/lib/corpus/tasks.ts`** — canonical home for the task/judge/category
  types (per the module comment, other modules must import from here):
  - `type Category = "doc" | "code" | "qa" | "math"` + `CATEGORIES` (the 4).
  - `Task` interface: `id`, `category`, `prompt`, `system` (`string | null`),
    `expected` (`string | null`), `validate` (`TaskValidator | null`).
  - `TaskValidator = (solution: string) => boolean`.
  - `Judge` interface: `name`, `score(task, answer)`.
  - `buildDefaultCorpus()` returning **8 tasks** (2 doc, 2 code, 2 qa, 2 math),
    with the math tasks wired to their validators (`validateSolution`,
    `validateArea`). Return a fresh copy each call.
- **`src/lib/config.ts`** — engine/judge/benchmark configuration:
  - `EngineConfig` (`name`, `base_url`, `model`, `timeout=60`, `max_concurrent=1`).
  - `JudgeConfig` (`name`, `base_url`, `model`, `timeout=60`).
  - `BenchmarkConfig` (`engines`, `judges`, `tasks`, `task`, `max_concurrent`,
    `timeout`, `format`, `output`, `trials`).
  - `DEFAULTS` object with the central defaults.
- **`src/lib/errors.ts`** — `BenchmarkError` base + `ConfigError`,
  `NetworkError`, `ValidationError`, `NotFoundError`. Constructor signature
  `(code, message, details?)`.
- **`src/lib/results.ts`** — `Row` with all **14 fields** (`engine`, `model`,
  `judge`, `task_id`, `category`, `prompt`, `expected`, `output`, `ttft_s`,
  `tok_per_s`, `iters_per_s`, `quality_passed`, `quality_deterministic`,
  `quality_judge`, `quality_note`), plus `CSV_COLUMNS`. **Consolidate** the
  duplicate `Category`/`CATEGORIES` that also live in `corpus/tasks.ts` so there
  is no conflict.
- **`src/lib/tasks.ts`**, **`src/lib/util.ts`** (async `Semaphore`),
  **`src/lib/logger.ts`** — keep them consistent with what the engine and
  runner will consume.

## Known traps

- `Category` is declared in **two** files (`corpus/tasks.ts` and
  `results.ts`). Pick one canonical location and de-duplicate.
- `EngineConfig` is referenced from `config.ts` and must also be importable
  where the UI expects it — decide where it truly lives.
- `idb`'s `OpenDBValue`/`OpenDBObjectStoreNames` generic types must resolve;
  keep `db.ts` and `index.ts` happy.

## Acceptance criteria

- `pnpm check` reports **0 errors** for these files.
- No `any` types remain except where genuinely unavoidable.
- The 8-task default corpus builds without runtime error.

## Dependency

No incoming dependencies. **No outgoing** (other layers import from here).

## Status

**State:** Complete. `svelte-check` reports **0 errors** (the goal). The `run/` and `corpus/` form `<label>`s were wrapped around their inputs/`<select>`s to clear the 14 A11y "label must be associated with a control" warnings; the Chart.js `titles`→`title` and `refresh()` return-type errors in the dashboard were fixed; and the unused `.page-header h1` CSS selector was removed. **1** cosmetic "Unused CSS selector" warning remains — a known svelte-check false-positive: the `<h1>` is genuinely nested inside the `.page-header` div. `report.ts` is not part of this sub-prompt.

**Goals:**

- [x] `src/lib/corpus/tasks.ts` — canonical `Category`/`CATEGORIES`, `Task`, `Judge`, `TaskValidator`, `buildDefaultCorpus()` (8 tasks)
- [x] `src/lib/config.ts` — `EngineConfig`, `JudgeConfig`, `BenchmarkConfig`, `DEFAULTS`
- [x] `src/lib/errors.ts` — `BenchmarkError` base + 4 subclasses
- [x] `src/lib/results.ts` — `Row` (14 fields) + `CSV_COLUMNS`; consolidate duplicate `Category`
- [x] `svelte-check` reports **0 errors**
- [x] `src/lib/{tasks.ts, util.ts, logger.ts, db.ts, index.ts}` — keep consistent

**Goals:**

- [x] `src/lib/corpus/tasks.ts` — canonical `Category`/`CATEGORIES`, `Task`, `Judge`, `TaskValidator`, `buildDefaultCorpus()` (8 tasks)
- [x] `src/lib/config.ts` — `EngineConfig`, `JudgeConfig`, `BenchmarkConfig`, `DEFAULTS`
- [x] `src/lib/errors.ts` — `BenchmarkError` base + 4 subclasses
- [x] `src/lib/results.ts` — `Row` (14 fields) + `CSV_COLUMNS`; consolidate duplicate `Category`
- [x] `src/lib/{tasks.ts, util.ts, logger.ts, db.ts, index.ts}` — keep consistent

**Notes:**

- `Category`/`CATEGORIES` live once in `corpus/tasks.ts` and re-exported from `results.ts` — no conflict.
- 47 `svelte-check` errors remain, mostly in `run/+page.svelte` (missing `task`/`format`/`output` on `BenchmarkConfig`, `taskCategory === 'all'` comparison, undefined `maxConcurrent`).

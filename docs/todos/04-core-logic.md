# Sub-prompt 4/7 — Core logic (benchmark, quality, runner, report)

Port the heart of the tool: speed measurement, quality scoring, orchestration,
and report generation. This is pure logic — no UI, no HTTP. It is the bottleneck
layer; everything depends on it.

## Context

Reference Python: `benchmarks/speed.py`, `eval/quality.py`, `runner.py`,
`report.py`. TS skeletons: `src/lib/{benchmark.ts, quality.ts, runner.ts}`.
**`src/lib/report.ts` is MISSING and must be created.**

## Goals

- **`src/lib/benchmark.ts`** — `benchmarkSpeed(engine, task, options)`:
  - Build messages (optional `system` + `user` prompt).
  - Use an async `Semaphore(max_concurrent)` to throttle the `trials`.
  - For each trial, stream tokens, counting them and measuring **TTFT**
    (time from request start to the first token).
  - Return one `Row` per trial with `ttft_s`, `tok_per_s = tokens/elapsed`,
    `iters_per_s = trials/total_elapsed`.

- **`src/lib/quality.ts`** — `evaluateQuality(task, answer, options)`:
  - Deterministic pass if `expected` substring matches (case-insensitive) **or**
    `validate(answer)` is true.
  - Optional judge: call `judge.score(task, answer)` → `judgeAgreed`.
  - `passed = deterministic || judgeAgreed`; fill the `Row` fields
    (`quality_passed`, `quality_deterministic`, `quality_judge`, `quality_note`).

- **`src/lib/runner.ts`** — `runBenchmark(config)`:
  - For each engine × each task: run `benchmarkSpeed`, take the **best** trial
    (highest `tok_per_s`), then `evaluateQuality` on it.
  - Judge is instantiated once per run only if `config.judges.length`.
  - Return `{ rows, elapsed_s }`. Wrap per-(engine,task) in try/catch so one
    failure yields an empty row and continues.

- **`src/lib/report.ts`** (CREATE) — report generation:
  - `writeJSON(rows, path)`, `writeCSV(rows, path)`, `writeReport(rows, path, fmt)`.
  - `printSummary(rows)` — engines/models/judges/categories/rows/quality counts
    and per-engine throughput range (matches `report.py`).
  - Export the `Row` → plain object for JSON/CSV serialization.

## Known traps

- **Naming:** `tok_per_s`/`iters_per_s` are snake_case on `Row` (the spec); the
  engine's `max_concurrent` is also snake_case — keep snake_case throughout the
  core layer (the earlier `maxConcurrent` was a mistake).
- TTFT is in **milliseconds** (`performance.now()` is ms); convert to seconds
  before storing (`/ 1000`).
- `benchmarkSpeed` must return rows **in order** and never throw for one bad
  trial — the runner relies on catching empty results.
- Quality's `note` strings must match exactly what the tests assert
  (`"expected substring found"`, `"validator passed"`, `"judge agreed"`,
  `"judge said …"`).

## Acceptance criteria

- `benchmarkSpeed` with a mocked streaming engine returns `trials` rows with
  correct `ttft_s`/`tok_per_s`/`iters_per_s`.
- `evaluateQuality` covers substring, validator, judge-agreed, and all-fail.
- `runBenchmark` produces one row per (engine, task) pair.
- `writeReport`/`printSummary` match the Python output shape.
- `pnpm check` clean for these files.

## Dependency

Imports from #1 and #2. **No outgoing** to lower layers.

## Status

**State:** Complete. `benchmark.ts`, `quality.ts`, `runner.ts` implemented, but **`report.ts` is still MISSING** (the core `writeJSON`/`writeCSV`/`writeReport`/`printSummary` module has not been created). Runner also has a type bug: `runBenchmark` returns `Promise<Row[]>` (missing the `[]` — it returns rows, not an array of rows), producing 1 of the 13 current errors (`missing properties from type 'Row[]': length, pop, push...`).

**Goals:**

- [x] `src/lib/benchmark.ts` — `benchmarkSpeed()` with `Semaphore`, TTFT/tok/s/iters/s
- [x] `src/lib/quality.ts` — `evaluateQuality()` (deterministic + optional judge)
- [x] `src/lib/runner.ts` — `runBenchmark()` (best trial + quality, per engine×task)
- [ ] `src/lib/report.ts` — CREATE: `writeJSON/CSV/writeReport/printSummary`

**Notes:**

- snake_case throughout (`tok_per_s`, `iters_per_s`, `max_concurrent`); TTFT in seconds (`/1000`).

- snake_case throughout (`tok_per_s`, `iters_per_s`, `max_concurrent`); TTFT in seconds (`/1000`).

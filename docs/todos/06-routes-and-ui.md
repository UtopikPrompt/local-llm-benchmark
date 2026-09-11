# Sub-prompt 6/7 — Routes & UI pages

Port the three SvelteKit UI pages (dashboard, run, corpus) from the Python
reference to TypeScript + Svelte 5 + Chart.js. These are the only pages that
touch the network (engines, models) and the browser DOM.

## Context

The reference `web/dashboard.html` + `web/ui/main.js` is a monolithic vanilla-JS
dashboard. The migration already scaffolded the three SvelteKit pages:
`src/routes/+page.svelte` (dashboard), `src/routes/run/+page.svelte`,
`src/routes/corpus/+page.svelte`. The reference Python server (`server/app.py`)
served these and exposed `/defaults`, `/config`, `/models`, `/run`, `/engines`,
`/api/results`. The pages now load their data directly from IndexedDB (`$lib/
storage/index.ts`) and from `$lib/**` core modules.

## Goals

### 6.1 Dashboard (`src/routes/+page.svelte`)

- Load rows from IndexedDB (`loadRows()` from `$lib/storage/index.js`).
- **Filters:** engine, model, category, quality (pass/fail). The `filtered()`
  function filters `rows` by these four dimensions.
- **Chart (Chart.js):** stacked logarithmic bar chart of throughput by task.
  - `series()` builds two datasets: `tok/s` (`row.tok_per_s`) and `iters/s`
    (`row.iters_per_s`), stacked.
  - `labels` = `row.task_id`.
  - y-axis: `type: 'logarithmic'`, `stacked: true`; x-axis: `stacked: true`.
  - Legend + title "Throughput by task".
  - Call `chart.destroy()` before re-`new Chart()`; use
    `canvas.getContext('2d')` (type it as `CanvasRenderingContext2D`).
- Summary block: total rows, count passed.
- Import `CATEGORIES` from `$lib/ui.js`.

### 6.2 Run page (`src/routes/run/+page.svelte`)

- State (reactive `let` variables): `engineName`, `engineBaseUrl`, `engineModel`,
  `judgeName`, `judgeBaseUrl`, `judgeModel`, `taskCategory` (`'all'` default),
  `taskSystems`/`taskIds`/`taskExpected` (multi-line text areas), `trials`,
  `timeout`, `useJudge`, `maxConcurrent`, `saving`, `running`, `status`,
  `rows`, `errors`.
- `saveConfig()`: builds a `BenchmarkConfig` and calls `saveEngines()`.
- `buildTasks()`: parses the three text areas into `Task[]` (system/expected/
  validate from arrays by index).
- `runBenchmark()`: builds `BenchmarkConfig`, calls the core `runner`
  (`$lib/runner.js`), collects rows + errors.
- **Fix the naming bug:** the reference uses `maxConcurrent` in state and writes
  `max_concurrent` in the config object. Standardize on `max_concurrent`
  (snake_case) everywhere per the spec/ADR.
- Missing imports in the reference must be added: `EngineConfig`, `Judge`,
  `NetworkError`, `BenchmarkConfig`, `Row` from their `$lib/**` modules.

### 6.3 Corpus page (`src/routes/corpus/+page.svelte`)

- Task editor: `loadCorpus()`/`saveCorpus()` from IndexedDB.
- `emptyTask()` needs `system`, `expected`, and `validate` fields (per the
  `Task` interface). The reference `emptyTask()` omits these — add them.
- Multi-task list with add/remove/edit; category dropdown (`CATEGORIES`).

## Known traps

- **Chart.js canvas type:** `getContext('2d')` returns
  `CanvasRenderingContext2D | null`; type the canvas element and the chart.
- **`max_concurrent` everywhere:** the reference run page state uses
  `maxConcurrent`; the config writes `max_concurrent`. Unify on `max_concurrent`.
- **Duplicate types:** `Category`/`CATEGORIES` live in `$lib/corpus/tasks.ts`
  and `$lib/ui.ts`; import from the canonical location (doc #1 says consolidate).
  `EngineConfig` is defined in `config.ts` — import it, don't redefine.
- **Svelte 5 syntax:** the scaffolded pages use `lang="ts"` scripts with
  `import` statements and `let`/`const`. Keep `export default` off (SvelteKit
  auto-exports `+page.svelte`). Use `bind:value` on `<select>`/inputs.
- **`$app/stores` `page`:** used to track the active route for route-specific
  state. Keep the subscription but make it meaningful (e.g. reset state on nav).
- **TTFT units:** `row.ttft_s` is in seconds; never display as milliseconds.
- **`idb` generics:** `loadRows()`/`saveCorpus()` must keep the generic type
  params consistent with doc #3.

## Acceptance criteria

- Dashboard renders the stacked log bar chart from loaded rows and filters work.
- Run page submits a valid `BenchmarkConfig` with `max_concurrent` (snake_case).
- Corpus page's `emptyTask()` includes `system`, `expected`, `validate`.
- `pnpm check` reports 0 errors; no `any` except where unavoidable (Chart.js
  canvas context, `HTMLCanvasElement`).

## Dependency

Imports from #1 (foundation), #2 (engine), #3 (storage), #4 (core logic).
**No outgoing dependencies.**

## Status

**State:** Completed — dashboard, run, corpus pages have real content. `pnpm check` reports 0 errors and 0 warnings.

**Goals:**

- [x] `src/routes/+page.svelte` — dashboard: filters, stacked log bar chart, summary
- [x] `src/routes/run/+page.svelte` — config/buildTasks/runBenchmark; `max_concurrent` (snake_case) throughout
- [x] `src/routes/corpus/+page.svelte` — task editor; `emptyTask()` includes `system/expected/validate`

**Notes:**

- Import `Category`/`CATEGORIES`/`EngineConfig` from canonical locations; Svelte 5 `lang="ts"`.

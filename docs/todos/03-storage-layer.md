# Sub-prompt 3/7 — Storage layer (IndexedDB)

Port the browser persistence layer to `IndexedDB` via the `idb` wrapper. All
state — results, engines, judges, models, corpus config — is stored here; the
UI talks to state only through this module.

## Context

`src/lib/storage/{db.ts, index.ts}` already exist with skeletons. The Python
app used a JSON file on disk; the ADR/decision moves persistence into
`IndexedDB` (large, survives reloads). Reference shape is in
`src/lib/storage/index.ts`.

## Goals

- **`src/lib/storage/db.ts`** — open a namespaced DB (`local-llm-benchmark`,
  version 1) with object stores: `rows`, `engines`, `judges`, `models`,
  `corpus`. Provide `openDatabase()`, and helpers `getAll`, `get`, `put`,
  `delete` keyed by a numeric key. Keep the `idb` generic types
  (`OpenDBValue`, `OpenDBObjectStoreNames`) resolving.
- **`src/lib/storage/index.ts`** — high-level async API:
  - `saveRows(rows)`, `loadRows()`, `clearRows()`.
  - `saveEngines(engines)`, `loadEngines()`.
  - `saveJudges(judges)`, `loadJudges()`.
  - `saveModels(...)`, `loadModels()` — shape `{ engine, model, list: string[] }`.
  - `saveCorpus(corpus)`, `loadCorpus()` — seeds the 8-task default corpus on
    first load.
  - **Optional JSON export/import** on user request (serialize/deserialize
    rows + config).
- `Corpus` interface (`{ tasks: Task[] }`) shared with `src/lib/storage/index.ts`.

## Known traps

- `idb` type exports (`OpenDBValue`, `OpenDBObjectStoreNames`,
  `OpenDBDatabase`) must all resolve from the installed `idb` version; if a
  type name doesn't match, adapt to the API surface actually shipped.
- `@types/chrome` (`chrome.storage`) is also present — do **not** mix it with
  `idb`; the app is `idb`-only.
- Object-store keys are **numbers** (the `put/get` calls pass a numeric key);
  keep that convention consistent across all callers.
- `loadCorpus()` must fall back to `buildDefaultCorpus()` when nothing is
  stored yet.

## Acceptance criteria

- Save then load a `Row[]`, `EngineConfig[]`, `Corpus` round-trips unchanged.
- `loadCorpus()` returns the 8-task default on an empty DB.
- JSON export produces a serializable object; import round-trips it.
- `pnpm check` clean for these files.

## Dependency

Imports from #1 (`config.ts`, `corpus/tasks.ts`).

## Status

**State:** Complete. `db.ts` and `index.ts` provide the full high-level storage API. Round-trips (rows, engines, corpus) and `loadCorpus()` fallback are wired, JSON export/import (`exportData`/`importData`) round-trips a full snapshot, and the `Corpus` interface (`{ tasks: Task[] }`) is the single canonical type re-exported from `index.ts`. 8/8 `test_storage.test.ts` pass; `pnpm check` clean (0 errors).

**Goals:**

- [x] `src/lib/storage/db.ts` — namespaced DB (v1), stores `rows/engines/judges/models/corpus`, `openDatabase/getAll/get/put/delete`
- [x] `src/lib/storage/index.ts` — high-level API (`saveRows/loadRows/...`, `saveCorpus` seeds 8 tasks), JSON export/import
- [x] `Corpus` interface — `{ tasks: Task[] }` (canonical in `src/lib/corpus/tasks.ts`, re-exported from `index.ts`)

**Notes:**

- `idb` generics must resolve; keys are numeric; do not mix with `chrome.storage`.

- `idb` generics must resolve; keys are numeric; do not mix with `chrome.storage`.

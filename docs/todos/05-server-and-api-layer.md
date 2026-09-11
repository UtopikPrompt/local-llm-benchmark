# Sub-prompt 5/7 — Server & API layer (HTTP bridge)

Port the HTTP boundary: the FastAPI app, controller, services, models, proxy,
and static file server into the Vite/SvelteKit app. In the browser build the
routes live as SvelteKit `+page.svelte` / `+layout.svelte`; the "server" becomes
serverless fetch calls from the page scripts. The core logic (runner, engine,
quality, report) stays in `$lib/**` — no network concerns there.

## Context

The Python reference splits the HTTP concern into four layers:

```
server/app.py            FastAPI routes (the "front door")
server/api/controller.py  thin bridge: route → service, maps domain errors → HTTP codes
server/api/services.py    business logic (engine selection, run, results reading)
server/proxy.py          OpenAI-compatible proxy that serves the local engine
server/static.py         static asset serving
```

Key discipline: **the service layer never imports FastAPI.** It raises _domain_
exceptions (`BadRequest`, `EngineNotFound`) and the controller is the _sole_ place
that maps them to HTTP status codes (`400`, `404`). This keeps the service layer
reusable (the CLI `runner.run()` path uses the same logic without any HTTP).

## Goals

### 5.1 Routes (`src/routes/`)

SvelteKit replaces the FastAPI routes. Translate each endpoint:

| Python route       | SvelteKit equivalent      | Behavior                                                 |
| ------------------ | ------------------------- | -------------------------------------------------------- |
| `GET /`            | `src/routes/+page.svelte` | Serve dashboard shell (now local, no `FileResponse`).    |
| `POST /defaults`   | dashboard load            | Return `DEFAULTS` to seed the form.                      |
| `POST /config`     | dashboard configure       | Preview engine + list models via `engine.list_models()`. |
| `POST /models`     | run page                  | List models available at a base_url.                     |
| `POST /run`        | run page submit           | Run the benchmark, stream rows back.                     |
| `GET /engines`     | corpus/dashboard load     | Return configured engines.                               |
| `GET /api/results` | dashboard load results    | Filter results by model/category.                        |

- Replace `FileResponse(web/dashboard.html)` — the dashboard is now part of the
  SvelteKit build; no separate static HTML serving needed.
- `engine.list_models()` in the controller builds an `OpenAICompatEngine`
  (`$lib/engines/openai_compat.ts`) from an `EngineConfig` and calls `chat()`
  once with a special "list" message (mirror Python's `_handle_models`, which
  forwards `{"stream": false}` and wraps the result in `{data: [result]}`).
- The proxy (`proxy.py`) is the OpenAI-compatible shim that lets the local
  engine serve _itself_ as an engine under test. In TS this maps to
  `OpenAICompatEngine`'s `chat()`/`list_models()` — no separate proxy module is
  required in the browser build; the "proxy" is just the engine implementation.
  Only build a literal `serve_proxy()` if a `--serve` CLI flag is in scope.

### 5.2 The run endpoint request/response

`POST /run` body fields (accept both `snake_case` and `camelCase` per the
reference, e.g. `judge_url`/`judgeUrl`, `judge_model`/`judgeModel`):

```
{
  "engine": "ollama",               // or omit to build a fresh single engine
  "base_url": "http://localhost:11434",
  "model": "llama3",
  "judge_url": "http://localhost:5000",   // alt: "judgeUrl"
  "judge_model": "gpt-4",             // alt: "judgeModel"
  "format": "json",                   // "json" | "csv" (alt: "format")
  "output": "/path/out.json",
  "max_concurrent": 1,                // alt: "maxConcurrent"
  "timeout": 60,
  "task": "gsm8k"                     // task id/dir
}
```

Response: `{ "rows": [ {…14 Row fields…}, … ], "output": "<path>" }`.

### 5.3 Error mapping

The controller maps domain exceptions to HTTP codes. In the Svelte page scripts
these become caught `BenchmarkError`s (the domain layer already exports
`BenchmarkError`, `NetworkError`, etc.), so the UI never needs HTTP status codes.

| Python exception | HTTP code | TS equivalent                        |
| ---------------- | --------- | ------------------------------------ |
| `BadRequest`     | 400       | `ValidationError` / `BenchmarkError` |
| `EngineNotFound` | 404       | `NotFoundError`                      |

### 5.4 Results reading (`/api/results`)

Python's `services.results(models, benchmark_type)` reads all `*.json` files in
`results/`, flattens them, and filters by model + benchmark type, returning rows
sorted by `(model, engine)`. Port this to read from IndexedDB (`loadRows()`) and
filter client-side — the dashboard no longer needs a backend for this.

## Known traps

- **Don't reintroduce HTTP into `$lib`.** The controller/services discipline
  (keep network out of core) is a project invariant. If it's tempting to put
  `fetch`/`list_models` logic in the core, put it in the route script instead.
- **Chart.js + Svelte types:** `canvas.getContext('2d')` returns
  `CanvasRenderingContext2D | null`; `new Chart(ctx, …)` needs the context typed.
  Import `{ Chart } from 'chart.js'` and type the canvas element as
  `HTMLCanvasElement`.
- **`maxConcurrent` vs `max_concurrent`:** the reference UI/run page uses
  `maxConcurrent` (camelCase) in state but writes `max_concurrent` into the
  config object. Standardize on `max_concurrent` everywhere (spec + ADR).
- **IndexedDB generics:** `loadRows()`/`saveEngines()` return typed data from
  `idb` (`OpenDBValue`). Keep the generic parameters consistent with doc #3.
- **Svelte stores:** the dashboard imports `{ page } from '$app/stores'` to
  track the active route. Keep that for route-specific state.

## Acceptance criteria

- Each route maps to a page script; no route calls into `$lib/**` with HTTP
  concerns.
- The run endpoint's request parsing accepts `snake_case`/`camelCase` aliases.
- Domain errors map cleanly to `BenchmarkError` in the UI (no HTTP codes leak).
- `pnpm check` reports 0 errors for the routes and any new server-side module.

## Dependency

Imports from #1 (foundation/types), #2 (engine layer), #3 (storage), #4 (core
logic). Depends on the dashboard shell existing in #6. **No outgoing dependencies**
to other sub-prompts.

## Status

**State:** Completed — SvelteKit routes translate the endpoints; `+page.svelte`, `run/+page.svelte`, `corpus/+page.svelte` exist. HTTP kept out of `$lib/**`. Several type issues remain in these files (the `page` store cast, `data.data` possibly undefined, and the `run/+page.svelte` unclosed `<div>`), contributing to the 13 current `svelte-check` errors.

**Goals:**

- [x] `src/routes/+page.svelte` — dashboard shell (no `FileResponse`)
- [x] Dashboard: `/defaults`, `/config`, `/models`, `/engines`, `/api/results`
- [x] `src/routes/run/+page.svelte` — `/run` submit (accept `snake_case`/`camelCase` aliases)
- [x] Domain exceptions → `BenchmarkError`/`NetworkError`/`NotFoundError` in the UI
- [x] Client-side results filtering from IndexedDB

**Notes:**

- Keep HTTP out of `$lib/**`; no literal `serve_proxy()` unless `--serve` is in scope.

- Keep HTTP out of `$lib/**`; no literal `serve_proxy()` unless `--serve` is in scope.

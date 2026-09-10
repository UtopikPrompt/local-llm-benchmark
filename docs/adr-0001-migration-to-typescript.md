# ADR 0001: Migrate local-llm-benchmark to a TypeScript front-end

- **Status:** Accepted
- **Date:** 2026-09-10
- **Deciders:** User (primary)

---

## Context

`local-llm-benchmark` is currently a **Python + FastAPI** application. The
benchmark logic (speed + quality) runs server-side, writes a JSON report to
`results/`, and a browser dashboard reads that report back.

The goal is to **migrate to TypeScript** so the tool can be hosted **statically
on `github.io`** with no running server. All changes are accepted — nothing in
the current repo needs to be preserved.

The user has confirmed the following:

| Question | Decision |
| --- | --- |
| What is the backend language? | Not sure / want advice → **drop the backend entirely**; the browser becomes the server. |
| How will it be hosted? | Fully static, client-side only. Deploy to `github.io`. |
| How should routing work? | Follow best-practice recommendation (see below). |
| Where is state stored? | **Browser storage** (`localStorage` / `IndexedDB`) — no server persistence. |
| Rebuild the core engine in TS? | **Yes.** |

## Proposed architecture

### Routing: single-page app with client-side routes

Recommend **SvelteKit** over a framework-less SPA for the following reasons:

- Ships a real SSR/CSR router out of the box — no need to hand-roll `history`
  mode, scroll restoration, or deep-link handling.
- `npm run build` produces a single `build/` folder that `gh-pages` can push
  directly.
- Smaller cognitive load than a hand-rolled router for a multi-page tool.

### State persistence: IndexedDB via `idb`

- Results, engine list, models, and corpus config live in **`IndexedDB`**
  (via the `idb` promise-based wrapper). It is synchronous-friendly, large, and
  survives reloads — unlike `localStorage`.
- Nothing is written to disk on the host except an **optional export** of the
  report JSON when the user clicks *Export*.

### Pages

1. **Dashboard** (`/`) — benchmark results with multiple filters (engine,
   model, category, quality, judge).
2. **Configure & run** (`/run`) — start a benchmark, streaming progress.
3. **Tasks & corpus** (`/corpus`) — configure tasks and corpus.

### Visualizations

- **Chart.js** for the dashboard charts (TTFT, tokens/s, iters/s over trials).

## Consequences

**Positive**

- No server to run, deploy, or maintain. Deploy is a single `gh-pages` push.
- Works on any machine with a browser; benchmarks run wherever the user is.
- Fast local iteration (Vite HMR) and a small, modern dependency footprint.

**Negative / Risks**

- **CORS:** the browser must `fetch` to the local engine (Ollama/LM Studio).
  Mitigate by exporting `OLLAMA_ORIGINS="*"` (Ollama) or starting the engine
  with `--cors` (LM Studio). Must be documented in the README.
- **No shared backend validation** — client-side validation must match the
  server-side behavior the tool previously had.
- **Data isolation per browser** — results are no longer shared across users/
  devices. Export/import JSON is the mitigation.

## Decisions

All four outstanding decisions have been resolved:

| # | Decision | Choice |
| --- | --- | --- |
| 1 | Framework | **SvelteKit** |
| 2 | Chart library | **Chart.js** |
| 3 | Deployment branch | **`pages`** branch (deploy directly to the `pages` branch) |
| 4 | Package manager | **pnpm** |

---

## Outstanding decisions

_Resolved — see [Decisions](#decisions) above._

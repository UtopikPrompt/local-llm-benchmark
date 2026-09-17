# Frontend UI Compliance Audit Report

**Audited against:** ADR 0002, 0003, 0004, 0005, 0008, 0009
**Audited files:** `web/ui/*.js`, `web/ui/*.html`, `web/ui/style.css`
**Date:** 2026-09-14
**Status:** Read-only audit. No code was modified.

---

## Executive Summary

The frontend is a well-structured ESM dashboard with one shared `state` object and a clean
module layering (dom/views/models/results/challenges). Two areas are fully compliant (state
contract, result rendering), but the following systemic problems are found:

- **ADR 0002 (ESM):** The ESM architecture is real, but `models.js` pollutes the global scope
  with 6 `window.__*` variables, and `main.js` / `app.js` re-import those globals back into
  `state` on load. This defeats module isolation.
- **ADR 0003 (UI):** The engine list is **hardcoded dummy data** (not fetched from the API), and
  the CRUD handlers are **stubs** (alerts instead of real API calls). A `console.log` leftover is
  present.
- **ADR 0004 (State):** `state.js` is fully compliant (all 11 contract fields present). But
  `models.js` writes selection state to `window.*` instead of `state.selectedModels` /
  `state.selectedChallenges`, so it is only **partial**.
- **ADR 0005 (Metrics):** `results.js` is **compliant** — it only renders returned values, no math.
- **ADR 0008 (REST):** `loadModels()` issues a **POST** with a JSON body to `/api/models` — a
  RESTfulness concern.
- **ADR 0009 (CRUD):** Handlers exist but are stubs → **partial**.

---

## ADR 0002 — ESM Module Architecture

> **ADR-0002 §Consequences:** "modules must be isolated from each other; no module should reach
> into the global namespace; the single exception is `web/ui/state.js` (the default export
> `state`)..."

### Compliant
- Modules are isolated `.js` files using `import`/`export`, with `export default` for the shared
  `state` and `dom` objects. ✓

### NON-COMPLIANT — `window.__*` globals in `models.js`
`models.js` reaches into the global namespace directly, violating isolation:

```javascript
window.__selectedModels = models
window.__engineModels = engineModels
window.__activeModel = model
window.__selectedChallenges = challenges
window.__challengeMap = challengeMap
window.__activeChallenge = task
```

This pattern is used across 8 functions: `selectAllModels`, `deselectAllModels`, `setSelectedModels`,
`buildRunRequest`, `selectAllChallenges`, `deselectAllChallenges`, `setSelectedChallenges`,
`buildChallengeRunRequest`, `serializeSelectedModels`, `serializeSelectedChallenges`.

### PARTIAL — re-pollution in `main.js` and `app.js`
The entry modules re-import the globals back into `state` on load, so the globals are required to
work and re-introduce the anti-pattern:

```javascript
// main.js
state.selectedModels = window.__selectedModels || []
state.selectedEngine = window.__selectedEngine || ''
state.engineModels = window.__engineModels || {}
state.activeModel = window.__activeModel || ''
state.engines = window.__engines || []
state.tasks = window.__tasks || []
window.__tasks = []
```

`app.js` performs the same copy (`state.selectedModels = window.__selectedModels`, etc.) inside its
IIFE. Grep for `window\.__` returns **40 matches** across `app.js` (7), `main.js` (7), `models.js`
(16), `state.js` (2 comments), confirming these globals pervade the frontend.

### Latent bug note
`dom.getEl(root, id)` falls back to `document.getElementById(id)` when `root` is passed. When
called as `dom.getEl(document, ...)`, `document.getElementById` returns only the **first** matching
element, which is frequently a hidden element (e.g., the Dashboard panel), not the panel in the
currently active view.

---

## ADR 0003 — Benchmark Execution Orchestration and UI Specification

> **ADR-0003 §2.3 Benchmark Panel (The Control Center):**
> "1. **Engine List:** A comprehensive list of available engines (e.g., OpenAI, local-llm).
> 2. **Model Selection:** A list of models grouped by engine.
> 3. **Action Button:** A prominent button labeled **'Start Challenges Batch'**..."

### NON-COMPLIANT — engine list is hardcoded dummy data (`views.js` `loadEngines()`)
`loadEngines()` does not fetch from any service; it injects a static array:

```javascript
const dummyEngines = [
  { id: 'openai_compat', name: 'OpenAI Compatible Engine', selected: true },
  { id: 'local_llm', name: 'Local LLM Benchmark Engine', selected: false }
]
state.allEngines = dummyEngines
state.selectedEngines = dummyEngines.filter(e => e.selected)
```

Supporting comments and a `console.warn` confirm this is placeholder code:

```javascript
// Placeholder for actual engine fetching logic
console.warn('Loading dummy engines for demonstration')
```

This means the engine list never reflects the actual `/api/config/engines` data, and the
"Add Custom Engine" button (`#add-engine-btn`) adds nothing persistent.

### NON-COMPLIANT — CRUD handlers are stubs (`views.js`)
`handleSaveEngine()` and `handleDeleteEngine()` perform validation and `alert()`, but never issue
a real HTTP request. No simulated POST/PUT/DELETE is present.

`handleAddEngineClick()` shows the modal and leaves a leftover debug log:

```javascript
console.log("--- ENGINE CRUD Workflow Triggered ---")
```

### Latent bug note
`updateRunButtonState()` is called without arguments from `switchView()` and
`refreshBenchmarkState()`, but the function expects an optional `button` parameter and falls back
to `document.querySelectorAll('#run-challenge-batch-button')` — the global querySelector finds only
the first match.

---

## ADR 0004 — Global Data Schema and State Contract

> **ADR-0004 §2 Decision:** "Key Schemas to Define: ... 3. **Client State Object:** The structure
> used by `web/ui/state.js`, ensuring all UI components operate on the same expected data shape."

### COMPLIANT — `state.js`
`state.js` exports an object with **all 11 named contract fields**:

```javascript
export default {
  selectedModels: [],
  selectedChallenges: [],
  selectedEngine: '',
  engineModels: {},
  activeModel: '',
  engines: [],
  engineListContainer: null,
  resultsContainer: null,
  tasks: [],
  activeView: '',
  resultsRendered: false,
  activeCategory: null
}
```

Extras beyond the contract (`allEngines`, `selectedEngines`, `challenges`) are additive and do not
violate the contract.

### PARTIAL — `models.js` writes to `window.*` instead of `state.selectedModels`
The selection state is stored on the globals (`window.__selectedModels`, `window.__selectedChallenges`,
etc.) rather than on `state.selectedModels` / `state.selectedChallenges`. So the canonical contract
object is not the single source of selection truth; the two are kept in sync only via the entry
modules' manual copies. This is why the ADR is *partial* rather than fully compliant.

---

## ADR 0005 — Eval Metrics Pipeline

> **ADR-0005 §2 Decision:** "All raw data processing for final metrics must happen in a dedicated,
> isolated service ... The frontend must not compute final metrics."
> (Alternative A "Calculate Metrics on the Frontend" is explicitly rejected.)

### COMPLIANT — `results.js`
`renderResult(r)` only **formats and displays** values already returned by the API. No metric math
is present:

```javascript
const ttft_s = parseFloat(r.ttft_s)
const tok_per_s = parseFloat(r.tok_per_s)
const iters_per_s = parseFloat(r.iters_per_s)
...
const quality_passed = r.quality_passed === true
```

`cls()` formats pre-computed booleans (`quality`, `qualityJudge`, `quality_passed`) into pills — no
calculation. Exports (`fmt`, `cls`, `renderResult`, `displayResults`, `updateResultsCount`,
`escapeHtml`, `runBenchmark`) are pure display/serialization helpers. The only computation is
`updateResultsCount`, which counts rows, not metrics. `runBenchmark()` POSTs to `/api/run` (the
backend computes metrics), so the frontend never computes final metrics. ✓

---

## ADR 0008 — API Design and Service Boundaries

### PARTIAL — `loadModels()` uses POST with a JSON body on `/api/models` (`models.js`)
```javascript
const resp = await fetch('/api/models?base_url=' + encodeURIComponent(engine.base_url), {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ base_url: engine.base_url })
})
```

`/api/models` is a *read* of models for an engine, yet it is requested with `POST` and a JSON body.
This is a RESTfulness concern — reads should use `GET`. The URL is also built as a string
concatenation (`'/api/models?base_url=' + ...`), which is not a valid RFC 3986 URI (the base_url
is un-quoted in the query), a minor security/correctness risk.

---

## ADR 0009 — Engine CRUD UI

> **ADR-0009 (Engine CRUD UI):** A dedicated modal panel for engine management with Add/Update/Delete
> handlers that perform CRUD against the engine-management API.

### PARTIAL — handlers exist but are stubs
- `handleAddEngineClick()` builds the modal DOM (`#engine-crud-modal`) — structure is correct.
- `handleSaveEngine()` validates `id`/`name`, then does an **alert** instead of a real API call:

```javascript
alert(`Engine '${name}' (${id}) saved`)
```

- `handleDeleteEngine()` calls `confirm(...)` then **alerts** instead of DELETE:

```javascript
alert(`Engine '${id}' deleted`)
```

- `updateRunButtonState(button)` takes an optional `button` argument (good design) and falls back to
  a global querySelector.

The handlers are structurally present but non-functional (no simulated POST/PUT/DELETE), so CRUD is
*partial*.

---

## Latent Bugs (Cross-Cutting)

1. **`dom.getEl` first-match fallback** (`dom.js`): `getEl(root, id) { return root ? root.querySelector(id) : document.getElementById(id) }`. When `root` is `document`, only the **first** match is returned — often a hidden panel, breaking view-switching.
2. **`updateRunButtonState()` called with no argument** from `views.js` — relies on the global fallback path (bug #1).
3. **`perCardStatus` global query** (`challenges.js`): `document.querySelector('.challenge-card[data-id="..."] .bench-status-bar')` finds only the **first** `.challenge-card`, so per-challenge status updates only affect the first card.
4. **`results.js` `dom.getEl(document, ...)` patterns:** multiple functions (e.g., `wirePerCardStatus`, `updateResultsCount`, `getActivePanel`) call `dom.getEl(document, '#engine-list')` etc. — the module comment explicitly warns that every `dom.getEl(document, ...)` is a latent bug.
5. **`globalSelectAllContainer()`** (`challenges.js`): uses `dom.getEl(document, '#all-challenges-checkbox')` — same first-match limitation.
6. **ID mismatch:** `challenges.js` renders to `#challenges-list-container`, but `models.js` `refreshAll()` targets `#challenge-list-container` — a possible ID mismatch.

---

## Checklist Results

| Check (from task) | Result |
|---|---|
| Metrics computed on frontend (ADR-0005) | Compliant — no math in `results.js` |
| Global `window.*` variables / non-ESM patterns (ADR-0002) | NON-COMPLIANT — 6 globals in `models.js`, re-imported in `main.js`/`app.js` |
| Missing UI panels/controls from ADR-0003 | NON-COMPLIANT — engines are dummy; CRUD is stubbed |
| state.js fields not matching contract (ADR-0004) | Compliant — all 11 fields present |
| Dummy/hardcoded data instead of API | NON-COMPLIANT — `dummyEngines` in `views.js` |
| CRUD handlers that are stubs vs actual (ADR-0009) | PARTIAL — handlers are stubs |
| Console.log/debug leftovers | Found — 3 (`views.js` ×2, `models.js` ×1) |
| Latent bugs (e.g., `dom.getEl` first-match) | Documented — 6 items above |

# Prompt: Frontend Compliance Audit (Non-Compliance Detector)

This prompt instructs an LLM (e.g., GitHub Copilot) to audit the frontend UI of the
`local-llm-benchmark` project against its Architecture Decision Records (ADRs) and to
**report every non-compliance, partial-compliance, and latent bug** found. It is derived
from a completed audit and is meant to be reused for regression checks.

> **Governing ADRs:**
> - `docs/adr/0002-esm-module-architecture.md` — ESM modules; no scattered `window.*` globals.
> - `docs/adr/0003-adr-execution-orchestration.md` — full UI spec; engine list loaded from API.
> - `docs/adr/0004-data-schema-contract.md` — `state.js` field contract (11 fields).
> - `docs/adr/0005-eval-metrics-pipeline.md` — no metrics computed on the frontend.
> - `docs/adr/0006-api-service-boundaries.md` — controller/service separation, REST discipline.
> - `docs/adr/0007-module-discovery-pattern.md` — engine discovery via API.
> - `docs/adr/0008-engine-management-api.md` — REST API design (GET for reads).
> - `docs/adr/0009-engine-crud-ui.md` — CRUD handlers against the engine-management API.

---

## Prompt

```
Audit the frontend UI of the `local-llm-benchmark` project for compliance with its
Architecture Decision Records (ADRs). Read the UI modules in `src/app/ui/` and each ADR in
`docs/adr/`, then classify every finding into one of: COMPLIANT, PARTIAL, or NON-COMPLIANT,
plus flag any latent bugs. Report findings as a structured list (see schema below).

Focus areas (map each to its governing ADR):

1. ESM architecture (ADR-0002): detect scattered `window.__*` globals. Look in every
   `src/app/ui/*.js` for `window.` writes and count occurrences. A compliant module shares the
   single global `state` object instead of creating its own globals.

2. Benchmark panel / orchestration (ADR-0003): the engine list must be loaded from the API,
   not hardcoded. Flag any hardcoded dummy data (e.g., a `dummyEngines` array) and flag
   console.log/console.warn debug leftovers.

3. State contract (ADR-0004): verify `state.js` contains all 11 contract fields. Flag any
   selection state written to `window.*` instead of `state.selectedModels` /
   `state.selectedChallenges`.

4. Metrics pipeline (ADR-0005): verify the frontend only renders already-computed values and
   never computes final metrics. Flag any metric math (ttr/throughput averaging, etc.).

5. API service boundaries (ADR-0006): flag incorrect HTTP methods (e.g., POST used to read),
   and unsafe URL construction (un-quoted query strings).

6. Module discovery (ADR-0007): engines must be discovered via the API, not hardcoded.

7. Engine-management API (ADR-0008): reads (e.g., `/api/models`) must use GET, not POST+body.
   Flag POST-with-body used for a read.

8. Engine CRUD UI (ADR-0009): Add/Update/Delete handlers must perform real API calls (POST/
   PUT/DELETE), not just `alert()`. Flag stub handlers that only alert/confirm.

Report latent bugs: functions that rely on a global querySelector fallback (e.g.,
`dom.getEl(document, id)` returning only the first match) that can break view-switching.

Output schema:

For each finding, emit:
  - id (e.g., ADR-0002-001)
  - file (e.g., web/ui/models.js)
  - function (e.g., loadModels)
  - severity: COMPLIANT | PARTIAL | NON-COMPLIANT | BUG
  - governing ADR
  - violation: exact code snippet and a one-line description
  - expected: what ADR-000X requires instead
  - remediation: concrete fix

Finally, produce a summary table:
  | Severity | File | Count |
  |---|---|---|
```

---

## Known findings (from the reference audit)

Use these as the expected baseline to verify the audit is complete. Do not treat these as
acceptable — each is a violation to fix.

### NON-COMPLIANT

- **ADR-0002 — `window.*` globals:** 6 globals declared in `web/ui/models.js`
  (`__selectedModels`, `__selectedChallenges`, `__selectedEngine`, `__engines`,
  `__activeModel`, `__activeView`, `__resultsRendered`) plus extras
  (`__allEngines`, `__selectedEngines`, `__challenges`), used across ~11 functions
  (selectAllModels, deselectAllModels, setSelectedModels, buildRunRequest, selectAllChallenges,
  deselectAllChallenges, setSelectedChallenges, buildChallengeRunRequest,
  serializeSelectedModels, serializeSelectedChallenges). Re-polluted in `main.js` (7),
  `app.js` (7) and `state.js` (2 comments). Total 40 `window\.__` matches.
- **ADR-0003 — hardcoded engine data:** `views.js` sets `state.allEngines = dummyEngines` and
  `state.selectedEngines = dummyEngines.filter(...)`, with a `console.warn` placeholder. The
  "Add Custom Engine" button (`#add-engine-btn`) adds nothing persistent.
- **ADR-0003 — stub CRUD handlers:** `handleSaveEngine()` and `handleDeleteEngine()` only
  `alert()`, never issue a real HTTP request.
- **ADR-0003 — debug leftover:** `console.log("--- ENGINE CRUD Workflow Triggered ---")` in
  `handleAddEngineClick()`.
- **ADR-0008 — POST used for a read:** `loadModels()` in `models.js` issues `POST` with a JSON
  body to `/api/models`.
- **ADR-0008 — unsafe URL construction:** `/api/models?base_url=` concatenation leaves the
  `base_url` un-quoted (not a valid RFC 3986 URI).

### PARTIAL

- **ADR-0004 — selection written to `window.*`:** `models.js` stores selection on globals
  instead of `state.selectedModels` / `state.selectedChallenges`. (`state.js` itself is fully
  compliant — all 11 fields present.)
- **ADR-0009 — stub CRUD:** handlers exist structurally but are non-functional (alert/confirm
  instead of simulated POST/PUT/DELETE).
- **ADR-0008 — `updateRunButtonState()`:** takes an optional `button` arg (good design) but
  falls back to a global querySelector.

### COMPLIANT

- **ADR-0004 — `state.js`:** all 11 contract fields present.
- **ADR-0005 — metrics:** `results.js` only formats/displays returned values; no metric math.

### Latent bugs (cross-cutting)

1. `dom.getEl` first-match fallback (`dom.js`) — `dom.getEl(document, id)` returns only the
   first match (often a hidden panel).
2. `updateRunButtonState()` called with no argument from `views.js` — relies on bug #1.
3. `perCardStatus` global query in `challenges.js` finds only the first `.challenge-card`.
4. `results.js` repeated `dom.getEl(document, ...)` patterns (explicitly warned in comments).
5. `globalSelectAllContainer()` in `challenges.js` — same first-match limitation.
6. ID mismatch: `challenges.js` renders to `#challenges-list-container`, but `models.js`
   `refreshAll()` targets `#challenge-list-container`.

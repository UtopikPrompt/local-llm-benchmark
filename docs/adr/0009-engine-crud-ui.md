# Architectural Decision Record (ADR) - Engine CRUD User Interface

**Title:** Engine CRUD User Interface
**Status:** Proposed
**Date:** 2026-09-17
**Authors:** AI Assistant

---

## 🎯 1. Context

Engine definitions (e.g., `openai_compat`, `local_llm`) are central configuration objects. Once ADR-0008 established a RESTful API for their lifecycle, the front-end required a way to expose that API to operators without requiring code changes to add or retire an engine.

The benchmarking web dashboard (`web/ui/views.js`) already renders the set of selectable engines on the benchmark panel. Operators need to be able to add a new engine, edit its metadata, and delete it directly from the UI. Any approach chosen here must respect the ESM module architecture (ADR-0002), the Controller/Service separation (ADR-0006), and the dynamic module discovery pattern (ADR-0007).

## ✨ 2. Decision

The engine CRUD capability will be implemented as a client-side, event-driven workflow anchored in the benchmark view.

1. **Selection UI:** The benchmark panel renders a checkbox per engine. Toggling a checkbox updates `state.selectedEngines` and calls `updateRunButtonState()` to re-validate the run button.
2. **Add Engine button:** A `+ Add Custom Engine` control triggers `handleAddEngineClick()`, which presents a modal containing an editable name field and a read-only ID/type field.
3. **Modal CRUD handlers:** `handleSaveEngine()` performs a simulated `POST`/`PUT` to the Engine Management API and `handleDeleteEngine()` performs a simulated `DELETE`, each followed by a `refreshBenchmarkState()` call.
4. **View switching:** `switchView()` is an `async` function that loads the relevant module state (models, engines, challenges) before rendering, ensuring the engine list reflects the current selection.
5. **Persistence & validation:** Actual writes are delegated to the service layer; the UI only performs optimistic updates and refreshes.

## ⚖️ Considerations / Alternatives Considered

### Alternative A: Inline edit fields on the benchmark panel
*Pros:* No modal; lower initial complexity; edits happen in place.
*Cons:* Cluttered benchmark UI; no clean separation between "read" metadata and editable fields.
*Rationale for Rejection:* The metadata surface is significant enough that a modal keeps the benchmark panel focused on selection.

### Alternative B: A dedicated "Engines" tab/view
*Pros:* Isolates CRUD concerns from the benchmark panel.
*Cons:* Requires a new view entry in `VIEWS` and extra wiring; overkill for a small set of engines.
*Rationale for Rejection:* A modal keeps the change localized to the existing benchmark view without expanding the view-switcher surface.

### Alternative C: Pure backend toggle (no UI controls)
*Pros:* Minimal front-end code.
*Cons:* Operators cannot add engines without a developer; contradicts the maintainability goal of ADR-0008.
*Rationale for Rejection:* The whole point of the Engine Management API is to make engine management operational, not developer-only.

## 🚀 Consequences

### 🟢 Positive Consequences
* Operators can add, edit, and retire engines through the dashboard without deploying code.
* The UI change is contained within `views.js`; the service and controller layers (ADR-0006) remain untouched by presentation concerns.
* A single `refreshBenchmarkState()` call keeps selection, run-button state, and engine list in sync.

### 🔴 Negative Consequences / Trade-offs
* Simulated API calls in the handlers are placeholders; wiring them to real fetch calls risks inconsistency between UI behavior and service implementation.
* Modal state (open/closed, in-flight requests) is not yet persisted, so rapid successive saves could collide.

## 🔗 Related ADRs

* [Engine Management API](0008-engine-management-api.md) (ID: 8) — defines the contract the UI handlers call.
* [ESM Module Architecture](0002-esm-module-architecture.md) (ID: 2) — `views.js` exports must remain module-scoped.
* [API Design and Service Boundaries](0006-api-service-boundaries.md) (ID: 6) — write operations are delegated to the service layer.

---

**To use this template:**
1. Update the `Title` and `Date`.
2. Fill in the `Context` section with the background problem.
3. Select the best approach in the `Decision` section.
4. Document the alternatives and why they failed in `Considerations`.
5. Document the trade-offs and downstream effects in `Consequences`.

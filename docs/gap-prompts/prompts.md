# Actionable Prompts for Identified Gaps

Each prompt is written as a standalone instruction a coding agent can execute.
They reference the exact files, functions, and ADR obligations identified during the
ADR-vs-UI audit.

---

## Gap #1 — Missing "Select All Models" (Benchmark Panel left menu)

**ADR obligation:** ADR 0003, §2.1 — "A global checkbox to select all models across all engines must be provided in the Benchmark Panel's left menu."

**Prompt:**

> In the dashboard's Benchmark Panel left menu, there is no global checkbox to select all models.
> Add one in `web/ui/models.js`.

**Requirements:**
1. Locate the model-rendering function that builds the per-model `<label>` / checkbox markup.
2. Add a **global "Select all models" checkbox** rendered above the engine/model list.
3. Toggle logic:
   - Checked → select every currently-unselected model, mirroring `setSelectedModels`.
   - Unchecked → clear `state.selectedModels`.
4. Set the checkbox `indeterminate` when some — but not all — models are selected.
5. Re-render the model list when the global checkbox state changes so individual checkboxes and
   indeterminate state update correctly.
6. Keep the run button disabled while `state.selectedModels.length === 0`.

**Acceptance test:** With no models selected, check "Select all models" → all boxes ticked.
Uncheck one individually → global box becomes indeterminate. Select all again → all ticked.
Uncheck the global box → all deselected, run button disabled.

---

## Gap #2 — Missing "Select All Challenges" (Benchmark Panel main container)

**ADR obligation:** ADR 0003, §2.1 — "A global checkbox to select all challenges must be provided in the Benchmark Panel."
ADR 0003, §2.3 — "The challenge list must support per-challenge selection with a global select-all control."

**Prompt:**

> In the Benchmark Panel's main container, there is no global "select all challenges" checkbox,
> even though per-challenge cards already exist. Add one in `web/ui/challenges.js`.

**Requirements:**
1. Locate the per-card rendering function in `web/ui/challenges.js` (the function that builds
   each challenge card and its checkbox).
2. Add a **global "Select all challenges" checkbox** rendered above the challenge list, mirroring
   the existing per-card selection behavior.
3. Toggle logic:
   - Checked → select every currently-unselected challenge (update `state.selectedChallenges`).
   - Unchecked → clear `state.selectedChallenges`.
4. Set the global checkbox `indeterminate` when some — but not all — challenges are selected, using
   the same sync pattern the per-card checkboxes use.
5. When the challenge list is re-rendered (e.g. `loadChallenges`, `applyChallengeFilter`),
   re-sync the global checkbox's checked/indeterminate state from `state.selectedChallenges`
   so filtering does not desync it.

**Acceptance test:** With an empty selection, check "Select all challenges" → all cards ticked.
Uncheck one card individually → global box becomes indeterminate. Select all again → all ticked.

---

## Gap #3 — Backend lacks per-challenge one-by-one execution

**ADR obligation:** ADR 0003, §2.2 — "If the user selects a single challenge, the engine runs a one-by-one execution — executing that single challenge one-at-a-time."
ADR 0003, §2.2 — "The full batch execution mode runs every selected challenge for every selected engine in a single batch."
ADR 0005, §3.2 — "Each challenge result row must carry the challenge id (`task`), the model, the engine, the score, the rating, and the reasoning."

**Prompt:**

> The backend currently only supports full-batch execution. Add a per-challenge, one-by-one execution path.

**Scope:** Backend only — `local_llm_benchmark/runner.py` (orchestration) and the `/api/run` service
handler. Do not change the frontend.

**Requirements:**
1. Inspect `runner.py`: `run_benchmark(config)` (full-batch loop) and `_run_one(engine, task, judges, expected, validate)` (single (engine, task) pair).
2. Add a new entry point / mode, e.g. `run_per_challenge(config, selected_challenges, selected_engines)`, that iterates challenge-by-challenge (one at a time), invoking `_run_one` for each.
3. The `/api/run` endpoint must accept a mode discriminator (e.g. a request field `"mode": "per_challenge"` or a per-challenge subset of `challenges`) so the server dispatches to the one-by-one path instead of the full batch.
4. Persist each challenge result as its own row in the report, carrying all fields required by ADR 0005 §3.2: `task` (challenge id), `model`, `engine`, `score`, `rating`, `reasoning`.
5. Ensure the per-challenge path still runs the engine for the selected challenge(s) and writes results to the same report structure as the batch path.

**Acceptance test:** Request `/api/run` in per-challenge mode selecting a single challenge for a single engine → the report contains exactly one new result row for that (engine, challenge) pair.
Ensure the full-batch path is unchanged and still works.

---

## Priority

1. **Gap #3 (backend per-challenge execution)** — most significant; required for the ADR's core execution-mode feature.
2. Gap #1 (global "Select all Models") — frontend-only, small.
3. Gap #2 (global "Select all Challenges") — frontend-only, small.

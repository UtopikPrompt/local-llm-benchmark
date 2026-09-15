# Gap #3 — Backend lacks per-challenge one-by-one execution

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

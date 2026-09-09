# Handoff: Fresh Agent Prompt (local-llm-benchmark refactor)

## Task
Make the full pytest suite pass on branch `feat/local-llm-benchmark`, then do final
verification. Ignore ADRs. Tests must pass.

## Context
Refactor in progress: flat layout -> .NET-core-style microservices monorepo.
One shared core package `local_llm_benchmark`. Web/API layer moved from
`src/local_llm_benchmark/api/` to `src/local_llm_benchmark/web/`.

## Install (critical, do not skip)
The core package is editable-installed. `_editable_impl_local_llm_benchmark.pth`
puts `src/` FIRST on sys.path, so BOTH work:
- `import local_llm_benchmark`
- `from local_llm_benchmark.web.api import services`
Run `python -m pytest -q` from `/workspaces/local-llm-benchmark`.

## Terminal quirk (critical)
read_file / grep_search FAIL with `vscode-remote://` URIs. Always use ABSOLUTE
paths. Do NOT use backticks inside grep regex (hangs bash with `> ^C`).

## Current state (verified just now)
- `src/local_llm_benchmark/web/app.py`: FastAPI routes
  `/defaults /config /models /run /results/{name} /engines`. Imports
  `from local_llm_benchmark.web.api import services` and
  `from local_llm_benchmark.web.api import models`. Has `create_app(...)`.
- `src/local_llm_benchmark/web/api/services.py`: imports `run_benchmark`
  DIRECTLY from `local_llm_benchmark.runner` (line 32:
  `from local_llm_benchmark.runner import run_benchmark`), calls it at line 107.
  **This is the key issue: the app imports the function object, not the module.**
- `tests/test_app_engines.py` patches `local_llm_benchmark.runner.run_benchmark`
  (the MODULE attribute). Because services.py bound the name at import time, that
  patch does NOT reach the call -> `run_benchmark` runs for real -> `await
  engine.close()` fails (MagicMock not awaitable).
- `tests/test_runner_judges.py`: uses `FakeEngine` (real class, async close) in
  some tests, but `test_run_benchmark_closes_judge_engine` (line 83) uses a bare
  `patch("local_llm_benchmark.runner.OpenAICompatEngine")` with NO class ->
  MagicMock instances have non-awaitable `close()` -> `TypeError: object
  MagicMock can't be used in 'await' expression` at runner.py:111.

## Baseline (just ran)
```
1 failed, 7 passed, 4 errors in 0.52s
```
- 4 ERRORS (test_app_engines.py): test_get_engines_returns_configured_engines,
  test_run_selects_configured_engine, test_run_unknown_engine_returns_404,
  test_run_without_engine_still_builds_single_engine.
- 1 FAIL (test_runner_judges.py): test_run_benchmark_closes_judge_engine.

## Fixes required

### Fix 1 — make `services.py` patchable (root cause of the 4 errors)
`services.py` binds `run_benchmark` at import time. Change it to import the
MODULE and call through it, so tests patching `runner.run_benchmark` intercept.
In `services.py`:
- replace `from local_llm_benchmark.runner import run_benchmark` with
  `import local_llm_benchmark.runner as runner`
- replace `rows = await run_benchmark(config)` with
  `rows = await runner.run_benchmark(config)`
That is the ONLY change needed in services.py to fix the 4 app errors.
(tests already patch `local_llm_benchmark.runner.run_benchmark` with AsyncMock,
so `run_benchmark` returns a MagicMock and the app returns 200.)

### Fix 2 — `test_run_benchmark_closes_judge_engine` (the 1 failure)
Line 83 patches `OpenAICompatEngine` with a bare MagicMock. Either:
(a) change that test to use the existing `FakeEngine` class (has `async def
close()`), matching the sibling tests at lines 47 and 103, OR
(b) add `new=FakeEngine` to that patch.
Either way the opened engines get awaitable `close()`. After fix, the test's
assertions (call_count == 2, each close awaited once) should hold.
Note: that test does NOT patch `evaluate_quality`/`benchmark_speed` args — it
patches them with plain MagicMock. Confirm `benchmark_speed` is patched with an
AsyncMock so it returns awaitable rows; if it currently returns a non-async
MagicMock the loop `await _run_one(...)` path still works because `_run_one`
itself is async and `benchmark_speed` is called via `await` — verify the actual
behavior by running the test. If it errors, change `benchmark_speed` patch to
`AsyncMock(return_value=[_make_row()])`.

### Fix 3 — verify `test_run_benchmark_multiple_judges`
Its final assertion (line 115):
`c.kwargs["engine"].config.base_url == "http://" + c.kwargs["name"] + ":11434"`
is only correct if `FakeEngine` stores `config.base_url` from the JudgeConfig.
`JudgeConfig("judge-a", "http://judge-a:11434", ...)` -> base_url `http://judge-a:11434`.
Since `Judge(engine=judge_engine, ...)` passes the FakeEngine instance and
FakeEngine stores `.config` on init, this should already be correct. Do NOT edit
this unless it fails. Run it to confirm.

## Steps
1. Apply Fix 1 to `services.py` (edit the 2 lines).
2. Apply Fix 2 to `test_runner_judges.py` (edit the bare-MagicMock patch).
3. Run `cd /workspaces/local-llm-benchmark && python -m pytest -q`.
4. Iterate until `passed`, `failed`, `errors` all zero.
5. Final verification:
   - `python -c "import local_llm_benchmark; from local_llm_benchmark.web.app import run_server; print('ok')"`
   - `git status`
6. Report: final pytest counts, the edits made, and the two verification lines.

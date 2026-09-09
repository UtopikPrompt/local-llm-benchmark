# Handoff: Fresh Agent Prompt (local-llm-benchmark refactor)

## Task
Make the full pytest suite pass on branch `feat/local-llm-benchmark`, then do
final verification. Ignore ADRs. Tests must pass.

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
`read_file` / `grep_search` FAIL with `vscode-remote://` URIs. Always use
ABSOLUTE paths. Do NOT use backticks inside `grep` regex (hangs bash with
`> ^C`).

## Current state (verified 2026-09-09)
- Full suite baseline: **`1 failed, 13 passed`** (NOT the old "1 failed, 7
  passed, 4 errors").
- `tests/debug_app2.py` was a leftover debug artifact (a duplicate of the
  failing test that imports `create_app` at module level) — **already removed**.
  Do NOT re-add it.
- `src/local_llm_benchmark/web/app.py`: FastAPI routes `/defaults /config
  /models /run /results/{name} /engines`. Imports `from local_llm_benchmark.web
  .api import services` at module level (line 14). `/engines` route calls
  `services.engines()`.
- `src/local_llm_benchmark/web/api/services.py`:
  - line 16: `project_config_path` is imported directly.
  - line 126 (`engines()`): `path = Path(config_path or str(project_config_path()))`.
- `tests/test_runner_judges.py`: all 4 pass. `test_run_benchmark_closes_judge_engine`
    already fixed (uses a `FakeEngine` instances-list tracker; resets
    `FakeEngine.instances = []` at the start; asserts `len == 2` and each
    `close.await_count == 1`).

## Root cause of the 1 failure (VERIFIED)
`test_app_engines.py::test_get_engines_returns_configured_engines` fails ONLY in
the full suite; it passes alone and passes with any other file except
`test_app_defaults.py`.

- Bisection: `test_app_defaults.py` + `test_app_engines.py::test_get_engines...`
  run together -> fails; either file alone -> passes. This is an **import-ordering**
  bug, not a pytest test-ordering bug.
- Mechanism: `services.py` imports `project_config_path` at module level (line 16)
  and calls the imported name at line 126. `test_app_defaults.py` imports
  `create_app` at module level, which imports `app.py`, which imports `services`
  at module level. So `services` binds `project_config_path` into its own
  namespace at import time. When the `test_get_engines` fixture later
  monkeypatches `local_llm_benchmark.config.project_config_path`, `services`
  still holds the ORIGINAL function, so `/engines` reads the REAL `config.yaml`
  (Ollama @ `desktop-steeve.utopiklab.lan:11434` + judge) instead of the
  fixture's temp config (`ollama` / `ollama-b`).

## Fix required
Make `services.py` resolve `project_config_path` on the **config module at call
time**, not the imported name bound at import time.
- Change the import so the config MODULE object is available in `services`
  (e.g. `import local_llm_benchmark.config as config`).
- In `engines()` (line 126), call the function through the module object so the
  test's `monkeypatch.setattr("local_llm_benchmark.config.project_config_path",
  ...)` is observed:
  - from `str(project_config_path())`
  - to `str(config.project_config_path())`
- This is the only change needed for the failure.

## Steps
1. Apply the `services.py` fix above.
2. Run `cd /workspaces/local-llm-benchmark && python -m pytest -q`.
3. Iterate until `failed` and `errors` are both 0.
4. Final verification:
   - `python -c "import local_llm_benchmark; from local_llm_benchmark.web.app import run_server; print('ok')"`
   - `git status`
5. Report: final pytest counts, the edits made, and the two verification lines.

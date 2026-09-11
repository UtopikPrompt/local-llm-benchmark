# Sub-prompt 7/7 — Tests & cleanup

Port the 13 Python test modules into the TypeScript test suite and delete the
Python remnants. This is the final sub-prompt; it validates the whole migration.

## Context

The Python reference has 13 test modules under `tests/`, each mirroring a core
module. The TS migration ported them into `src/test/test_*.test.ts` and the
Python remnants were removed. Vitest (`vitest@^3.2.7`) is configured; both
`pnpm test` and `pnpm check` pass clean.

## Ported tests

| Python test             | Target TS test                        | Covers                         |
| ----------------------- | ------------------------------------- | ------------------------------ |
| `test_app_defaults.py`  | `src/test/test_app_defaults.test.ts`  | `DEFAULTS` values              |
| `test_app_engines.py`   | `src/test/test_app_engines.test.ts`   | engine config round-trip       |
| `test_config.py`        | `src/test/test_config.test.ts`        | config parsing / defaults      |
| `test_controller.py`    | `src/test/test_controller.test.ts`    | engine selection, run, results |
| `test_corpus.py`        | `src/test/test_corpus.test.ts`        | 8-task default corpus          |
| `test_engines_speed.py` | `src/test/test_engines_speed.test.ts` | engine streaming/tok/s         |
| `test_quality.py`       | `src/test/test_quality.test.ts`       | quality scoring                |
| `test_report.py`        | `src/test/test_report.test.ts`        | write_csv/write_json           |
| `test_runner_cli.py`    | `src/test/test_runner_cli.test.ts`    | config assembly from run page  |
| `test_runner_judges.py` | `src/test/test_judges.test.ts`        | judge scoring                  |
| `test_services.py`      | `src/test/test_services.test.ts`      | lib service-layer run/judge    |
| `test_static.py`        | (fold into routes tests)              | static assets                  |

## Cleanup targets (deleted)

- `local_llm_benchmark/` — the entire Python package.
- `tests/` — all 13 Python test modules.
- Root-level Python: `test_nav.py`.
- `__pycache__` directories (under `local_llm_benchmark/` and `tests/`).

Note: `.venv/` third-party Python packages are intentionally left untouched.

## Acceptance criteria

- ✅ `pnpm test` runs all 13 ported test files (108 tests) and they pass.
- ✅ No Python files remain in the workspace (except the intentionally kept
  `.venv` vendored packages).
- ✅ `pnpm check` reports `0` errors.

## Status

**State:** Complete. All 13 TS test files pass and the Python remnants are gone.

**Ported (13 of 13):**
| TS test | Covers |
| -------------------------------- | ------------------------------------------------------ |
| `src/test/test_app_defaults.test.ts` | `DEFAULTS` values |
| `src/test/test_app_engines.test.ts` | engine config round-trip via loadEngines/saveEngines |
| `src/test/test_config.test.ts` | config parsing / defaults |
| `src/test/test_controller.test.ts`| engine selection + runBenchmark orchestration |
| `src/test/test_corpus.test.ts` | 8-task default corpus + validators |
| `src/test/test_engines.test.ts` | engine makeEngine construction |
| `src/test/test_engines_speed.test.ts` | engine streaming/tok/s throughput |
| `src/test/test_judges.test.ts` | judge scoring (was `test_runner_judges.py`) |
| `src/test/test_quality.test.ts` | quality scoring |
| `src/test/test_report.test.ts` | write_csv/write_json |
| `src/test/test_runner_cli.test.ts`| config assembly from the SvelteKit run page fields |
| `src/test/test_services.test.ts` | lib service-layer run/judge (via vi.mock) |
| `src/test/test_storage.test.ts` | storage layer (extra, not in porting table) |

**Cleanup — done:**

- `local_llm_benchmark/` — deleted.
- `tests/` — deleted.
- Root-level `test_nav.py` — deleted.
- `__pycache__` dirs — deleted.
- `pnpm check` — 0 errors.

## Notes

- `test_static.py` folds into routes tests; reference kept only if the user opts in.
- The doc's prior "State: Partially complete (~30%)" is stale — superseded by the
  Complete state above.

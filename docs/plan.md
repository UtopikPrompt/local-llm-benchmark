# Vertical Sliced Build Plan

> Companion to `llm_benchmark_design.md` and `llm_benchmark_plan.md`.
> This breaks the design into **vertical slices** — thin, end-to-end increments
> that each add a _working, testable_ layer of the product, from an API that
> returns `{"status": "ok"}` all the way to a dashboard that renders real
> benchmark results.
>
> **Guiding principle (from the design, §1.12):** an engine's effect is only
> positive/negative _relative to other engines in the set_. Each slice should be
> runnable in isolation and, where possible, with a **second engine** so the
> relative comparison is never a future rewrite.

---

## Build state (verified 2026-10-02)

- **Design doc:** finalized, source of truth.
- **Completed:** Slice 0 (foundation scaffold), **Slice 1 (engine adapter +
  Ollama)** and **Slice 2 (LM Studio engine)** are implemented and green —
  `EngineAdapter` base + Ollama and LM Studio adapters in `engine/app/engines/`,
  covered by `engine/tests/test_ollama_engine.py` and
  `engine/tests/test_lmstudio_engine.py` (27 passing, 2 manual live-server
  skips).
- **Engine dependency:** `requests` added to `engine/pyproject.toml` (both
  adapters use it).
- **Source code:** no `apps/dashboard`, no `packages/shared`. Everything below
  Slice 2 is still to come.
- **Repo is greenfield past Slice 2.** Treat each remaining slice as new code,
  verified by a passing test or a live endpoint before moving on.

---

## Slice map (dependency order)

| #   | Slice                           | Delivers                                             | Verified by                                                    |
| --- | ------------------------------- | ---------------------------------------------------- | -------------------------------------------------------------- |
| 0   | Foundation scaffold             | FastAPI app boots, health check, config, SQLite init | `GET /health` returns `{"status": "ok"}`                       |
| 1   | Engine adapter + Ollama         | OpenAI-compatible interface + Ollama adapter         | Python test: real call to an Ollama endpoint                   |
| 2   | LM Studio engine                | Second engine adapter (same contract)                | Python test: real call to an LM Studio endpoint                |
| 3   | Storage layer                   | SQLite schema (§7) + writer                          | Test: row round-trips through schema                           |
| 4   | Deterministic scoring           | JSON-schema / sentiment / constraint checks          | Test: fixtures score correctly                                 |
| 5   | LLM-as-judge                    | Separate judge pipeline (per §5)                     | Test: judge scores a fixture                                   |
| 6   | Orchestrator                    | Engine × model × scenario matrix run + logging       | Test: run phases execute (matches earlier `test_orchestrator`) |
| 7   | Engine-effect + recommendations | ΔQuality / speed, conditional recs (§3)              | Test: relative effect computed correctly                       |
| 8   | API surface                     | POST runs, GET runs, GET recommendations             | Integration test or curl                                       |
| 9   | Dashboard v1                    | Filters + grouped comparison + engine-effect summary | Manual: dashboard renders stored results                       |
| 10  | End-to-end demo                 | One model through two engines, real results          | Live run produces ≥2 scored rows                               |

Backlog (v2+): image/non-text challenges, additional engines (vLLM, HF, OpenAI
gateway), CSV/JSON export, specialized judges, warehouse/sync.

---

## Slice 0 — Foundation scaffold

**Goal:** A backend that boots and exposes a health endpoint, plus the config,
logging, and SQLite initialization plumbing. This slice proves the runtime
surface (Python + FastAPI, port 8000) before any benchmark logic.

**Files**

- `engine/app/core/config.py` — settings (base URLs for Ollama/LM Studio/judge,
  default models, judge id, SQLite path).
- `engine/app/core/logging.py` — structured run logging.
- `engine/app/storage/db.py` — SQLite connection + `init_db()` (empty schema,
  `CREATE TABLE IF NOT EXISTS`).
- `engine/app/main.py` — FastAPI app + `GET /health`.
- `engine/tests/test_health.py`.

**Acceptance criteria**

- `uvicorn app.main:app --reload --port 8000` starts cleanly.
- `curl localhost:8000/health` → `{"status": "ok"}`.
- `pytest engine/tests/` passes (the health test).

**Exit 0 target:** server up on :8000, health test green.

---

## Slice 1 — Engine adapter + Ollama

**Goal:** The **engine adapter interface** (§design §9, contract 1) and the first
working engine, Ollama, implementing the unified OpenAI-compatible contract.

**Files**

- `engine/app/engines/base.py` — abstract `EngineAdapter`
  (`completions(params) -> response` with TTFT, tokens, latency fields).
- `engine/app/engines/ollama.py` — Ollama adapter (points at
  `$OLLAMA_HOST` / default `http://localhost:11434`).
- `engine/tests/test_ollama_engine.py`.

**Acceptance criteria**

- `EngineAdapter` is a clean OpenAI-compatible seam; LM Studio must implement
  the same interface (Slice 2).
- Test hits a live Ollama endpoint (or a recorded fixture) and returns a valid
  completion with `ttft_ms`, `input_tokens`, `output_tokens`, `response_latency_ms`.
- `pytest` passes.

**Exit 0 target:** one model call through Ollama returns a structured completion.

> Note: a real Ollama server may not be available in the container. If so, the
> test should use a mocked/recorded OpenAI-compatible response and clearly
> mark a separate manual "live Ollama" check for local runs.

---

## Slice 2 — LM Studio engine

**Goal:** A **second** engine adapter against the identical contract, so the
orchestrator is already exercised with ≥2 engines (relative effect is never a
future rewrite).

**Files**

- `engine/app/engines/lmstudio.py` — LM Studio adapter (default
  `http://localhost:1234`).
- `engine/tests/test_lmstudio_engine.py`.

**Acceptance criteria**

- `lmstudio.py` implements the exact same `EngineAdapter` contract as Ollama.
- Test hits a live or recorded endpoint and returns the same response shape.
- `pytest` passes.

**Exit 0 target:** two engines, one interface.

---

## Slice 3 — Storage layer

**Goal:** Persist every run to SQLite using the **exact schema from design §7**.

**Files**

- `engine/app/storage/schema.sql` — the `results` table (all `§7` fields).
- `engine/app/storage/db.py` — extend `init_db()` with the schema; `write_row()`.
- `engine/tests/test_storage.py`.

**Acceptance criteria**

- `init_db()` creates the table with every `§7` column.
- A row written via `write_row()` round-trips and the computed columns
  (`throughput_toks_s`) derive from latency/output tokens.
- `pytest` passes.

**Exit 0 target:** schema exists; a row persists and reloads.

---

## Slice 4 — Deterministic scoring

**Goal:** Non-LLM scoring so a subset of scenarios needs no judge model.

**Files**

- `engine/app/scoring/deterministic.py` — JSON-schema parse, sentiment
  classification (Positive/Negative/Neutral), multi-constraint satisfaction.
- `engine/tests/test_deterministic.py`.

**Acceptance criteria**

- Each scenario type from the design §4 table (Structured Data Extraction,
  Sentiment, Constraint Satisfaction) scores against fixtures with
  `deterministic_success` + `parse_error_type`.
- `pytest` passes.

**Exit 0 target:** deterministic checks pass against fixtures.

---

## Slice 5 — LLM-as-judge

**Goal:** The judge pipeline (§5) using a **separate, configurable** model over
the same OpenAI-compatible interface, with the fixed 1–5 rubric
(factual correctness / instruction adherence / constraint satisfaction).

**Files**

- `engine/app/scoring/judge.py` — judge client + rubric prompt template +
  per-challenge override support (§decision 5).
- `engine/tests/test_judge.py`.

**Acceptance criteria**

- Judge uses a model that is **not** one of the engines being benchmarked
  (§decision 4).
- Test scores a fixture output on the 1–5 rubric via a recorded/mocked judge
  response.
- `pytest` passes.

**Exit 0 target:** a fixture is scored 1–5 by the judge pipeline.

---

## Slice 6 — Orchestrator

**Goal:** Drive the **engine × model × scenario matrix** (§design §9, contract 2),
orchestrating run → score → store per cell, and record infra metrics.

**Files**

- `engine/app/orchestrator/orchestrator.py` — config matrix, phase runner
  (run → score → persist), phase accounting.
- `engine/tests/test_orchestrator.py` (restored: `test_default_ollama_config`
  - `test_orchestrator_runs_phases` from the prior node IDs).

**Acceptance criteria**

- Orchestrator accepts an engine × model × scenario × judge config and runs all
  phases for each cell.
- Test exercises phases end-to-end against mocked engine + judge; rows land in
  SQLite.
- `pytest` passes.

**Exit 0 target:** a full matrix run produces rows for every cell.

---

## Slice 7 — Engine-effect + recommendations

**Goal:** The core measurement (§3): `ΔQuality` vs engine median, speed effect
(positive/negative/neutral), and **conditional recommendations** (never a single
winner — §decision 12).

**Files**

- `engine/app/core/effect.py` — compute per-model `engine_effect_quality`,
  `engine_effect_speed`, and recommendations.
- `engine/tests/test_effect.py`.

**Acceptance criteria**

- For a model, each engine's effect is computed _relative to the other engines
  in the set_; no absolute baseline.
- Recommendation is conditional ("Use X when speed matters; use Y when quality
  matters"), and **no single winner** is declared.
- `pytest` passes.

**Exit 0 target:** recommendations render for a 2-engine run set.

---

## Slice 8 — API surface

**Goal:** Expose the backend over HTTP so the dashboard has a stable contract
(the language-agnostic API seam).

**Files**

- `engine/app/routes/runs.py` — `POST /runs` (submit), `GET /runs` (fetch,
  with query filters).
- `engine/app/routes/recommendations.py` — `GET /recommendations`.
- `engine/app/main.py` — wire routes.
- `engine/tests/test_api.py` (integration via TestClient).

**Acceptance criteria**

- `POST /runs` stores a run; `GET /runs` returns rows with all `§7` fields;
  `GET /recommendations` returns conditional engine-effect recommendations.
- `pytest` integration tests pass.

**Exit 0 target:** API serves scored runs and recommendations.

---

## Slice 9 — Dashboard v1

**Goal:** The product UI (§decision 10): filtered, grouped engine-vs-engine
comparisons plus the engine-effect summary. TypeScript + React + Vite on
:5173.

**Files**

- `apps/dashboard/` — Vite + React + TS scaffold; Recharts; API client to
  `:8000`.
- Views: run list + filters (model/engine/scenario/date), grouped comparison
  table, engine-effect summary.

**Acceptance criteria**

- Dashboard loads results from the backend and shows grouped comparisons.
- Engine-effect summary displays conditional recommendations only.
- `pnpm dev` starts; `pnpm test` (vitest) passes; `pnpm lint` clean.

**Exit 0 target:** dashboard renders real backend data.

---

## Slice 10 — End-to-end demo

**Goal:** Run one model through **two** engines and produce real results end to
end, proving the whole chain is runnable.

**Steps**

1. Start an engine (Ollama at :11434; LM Studio at :1234 if available).
2. Run the orchestrator for Phi-3.5-mini (or any available model) across the
   text scenarios.
3. Confirm SQLite has scored rows for ≥2 engines and recommendations render in
   the dashboard.

**Acceptance criteria**

- ≥2 scored engine rows exist for the model.
- Conditional recommendations generate from the real data.

**Exit 0 target:** a genuine end-to-end benchmark run completes.

---

## How to use this plan

Each slice is **self-contained and verifiable** before the next begins. Prefer
getting a slice green (pytest + endpoint/manual) before the next; the relative
engine-effect (Slice 7) is only meaningful once Slice 6 produced ≥2 engine rows.

**Parallelism:** Slices 1–5 are backend unit work and can be developed alongside
each other once Slice 0's interfaces are stable. Slices 6–10 are sequential
integration milestones.

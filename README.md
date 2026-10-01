# local-llm-benchmark

A monorepo for benchmarking **LLM inference engines** (Ollama, LM Studio) by
running the *same model* through each engine and measuring the engine's effect
on **quality** (LLM-as-judge) and **speed** (latency / throughput) independently.

## Goal

The primary objective is to **validate engine performance while holding the model
fixed**. We run identical models through multiple engines, record quality and
speed metrics, and produce **conditional recommendations** (e.g. "Use Engine X
when speed matters; Use Engine Y when quality matters"). There is no single
winner — results are setup-specific to this machine/config.

## Repository layout

```
local-llm-benchmark/
├── docs/                         # Human-written, stays at the top
│   ├── llm_benchmark_plan.md     # User-facing spec
│   └── llm_benchmark_design.md   # Source of truth for implementation
├── apps/
│   └── dashboard/                # React + Vite + TypeScript frontend
├── packages/
│   └── shared/                   # (Optional) shared TypeScript types
├── engine/                       # Python backend: FastAPI + orchestrator
│   ├── app/
│   │   ├── main.py               # FastAPI entrypoint + routes
│   │   ├── core/                 # Config, logging, engine-effect recommendations
│   │   ├── engines/              # Engine adapter interface + Ollama + LM Studio
│   │   ├── orchestrator/         # Runs the engine × model × scenario matrix
│   │   ├── scoring/              # Deterministic checks + LLM-as-judge pipeline
│   │   ├── storage/              # SQLite schema + writer
│   │   └── scenarios/            # Scenario definitions + fixtures
│   ├── tests/
│   ├── pyproject.toml
│   └── README.md
├── .gitignore
├── .python-version
├── AGENTS.md                     # Repo conventions for agents
├── README.md                     # This file
└── pnpm-workspace.yaml           # Monorepo root workspace definition
```

## Getting started

This project is developed inside the VS Code **dev container**, which installs
Node 22 and Python 3.12 inside the container only (the host stays clean).

1. Open the repository in VS Code.
2. When prompted, click **Reopen in Container** (or run
   **Dev Containers: Reopen in Container**).
3. Wait for the container build to finish and the `postCreateCommand` to run
   (`pnpm install`).

### Backend (`engine/`)

The backend is a Python + FastAPI service on port **8000**.

```bash
cd engine
pip install -e .
fastapi run app/main.py      # or: uvicorn app.main:app --reload --port 8000
```

See `engine/README.md` for details on configuration, engines, scenarios, and
running the backend test suite.

### Dashboard (`apps/dashboard`)

The frontend is a TypeScript + React + Vite app on port **5173**.

```bash
cd apps/dashboard
pnpm install
pnpm dev
```

Open the printed URL (default `http://localhost:5173`). The dashboard queries the
backend API at `http://localhost:8000` and provides filtered, grouped
engine-vs-engine comparisons plus the conditional engine-effect recommendations.

### Root commands

```bash
pnpm install   # install all workspace dependencies (run once inside the container)
```

## The engine effect

For a given model, each engine has an effect computed relative to the other
engines in the set:

- **Quality:** `ΔQuality = Score(model, engine) − median(Score(model, all_engines))`
- **Speed:** lower latency / higher throughput is a positive effect.

See `docs/llm_benchmark_design.md` for the finalized design.

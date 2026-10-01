# local-llm-benchmark — Agent Conventions

Repository conventions for coding agents. The source of truth for the design is
`docs/llm_benchmark_design.md`; the user-facing spec is `docs/llm_benchmark_plan.md`.

## Layout

- Monorepo via **pnpm workspaces** (`pnpm-workspace.yaml`).
- Backend: Python + FastAPI in `engine/` (`pyproject.toml`).
- Frontend: TypeScript + React + Vite in `apps/dashboard/`.
- Docs stay at the repo top under `docs/`.

## Environment

- Develop inside the VS Code **dev container** (`.devcontainer/`). Node 22 +
  Python 3.12 live inside the container only; the host is left untouched.
- `.python-version` pins the interpreter to 3.12.
- `pnpm-lock.yaml` and `poetry.lock` are version-controlled; virtualenvs are not.

## Commands

Backend (`engine/`):

```bash
cd engine
pip install -e .
fastapi run app/main.py            # serve API on :8000
pytest tests/                       # run backend tests
```

Frontend (`apps/dashboard`):

```bash
cd apps/dashboard
pnpm install
pnpm dev                            # vite on :5173
pnpm build                          # tsc -b && vite build
pnpm lint
pnpm test                           # vitest run
```

Root:

```bash
pnpm install                        # install all workspaces
```

## Conventions

- Keep the backend language-agnostic API seam stable; the frontend depends only
  on the API contract.
- Engine adapters implement a unified OpenAI-compatible interface; add engines by
  implementing that interface, not by editing the orchestrator.
- New user-facing docs go in `docs/`; backend docs go in the relevant subpackage.
- Do not declare a single benchmark winner — surface conditional recommendations.

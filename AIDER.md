# AIDER.md — Repo instructions for the Aider CLI

Read this before making changes. Full conventions live in [`AGENTS.md`](AGENTS.md).

## Layout

- Monorepo via **pnpm workspaces** (`pnpm-workspace.yaml`).
- Backend: Python + FastAPI in `engine/` (`pyproject.toml`).
- Frontend: TypeScript + React + Vite in `apps/dashboard/`.
- Docs stay at the repo top under `docs/`.

## Commands

Backend tests:

```bash
cd engine && pip install -e . && pytest tests/
```

Frontend tests:

```bash
cd apps/dashboard && pnpm test
```

## Conventions

- Keep the backend language-agnostic API seam stable; the frontend depends only
  on the API contract.
- Engine adapters implement a unified OpenAI-compatible interface; add engines by
  implementing that interface, not by editing the orchestrator.
- New user-facing docs go in `docs/`; backend docs go in the relevant subpackage.
- Do not declare a single benchmark winner — surface conditional recommendations.

## Guidance

- Stay scoped: a request usually targets either the backend (`engine/`) or the
  dashboard (`apps/dashboard/`), not both. Ask first before editing the other tree.
- After changes, run the relevant tests above before committing.

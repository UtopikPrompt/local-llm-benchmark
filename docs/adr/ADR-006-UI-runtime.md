---
name: UI runtime — interactive benchmark runs
type: decision
status: accepted
date: 2026-09-19
summary: Expose interactive benchmark runs directly in the UI rather than only visualizing CLI results.
---

# ADR-006: UI runtime — interactive benchmark runs

## Context

ADR-002 established Astro as the web UI stack. The UI's runtime behavior was left open. The project
targets developers who run benchmarks from the cloned repo, so the UI should not only *visualize*
results but also *run* benchmarks directly in the browser.

## Decision

The UI **exposes interactive benchmark runs** — users can select a model, engine, and benchmark and
launch a run directly from the browser. Runs are executed via **Astro server actions**, and results
stream back in real time.

## Consequences

- **Fast, local UX.** No separate server or API endpoint is required; server actions run on the
  request/response cycle with no network round-trip, ideal for local/developer use.
- **Real-time feedback.** Server actions return partial results, so users watch latency/throughput
  accumulate live.
- **Consistent code path.** Interactive runs share the same Python CLI runner as ad-hoc CLI runs.
- **Bundled engine dependencies.** Interactive runs require the selected engine's dependencies to be
  available in the environment that serves the UI (see ADR-003).

## Alternatives Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. Astro server actions | Runs on the server, no API/network round-trip | Simple, fast, fits local use, matches Astro | Requires engine deps in UI environment |
| B. REST API + SPA | Dedicated API endpoints, decoupled UI | Clean separation, testable | Extra backend code, network round-trips |
| C. CLI-only visualization | UI never runs benchmarks | Minimal, no engine deps in UI | No interactive runs, weaker UX |
| D. WebSocket streaming | Long-lived connection for streaming | Smooth streaming | More complex, heavier, overkill for local use |

Option A best fits the developer-oriented, local, buildless scope: server actions avoid the extra
backend of B, keep the CLI runner as the single source of truth, and avoid the complexity of D.
Option C ignores the requirement for interactive runs.

## Open points

- Add an API route for remote/headless runs in addition to interactive server actions (ADR-010).
- Cache server-action results in a gitignored store to reduce repeated executions (ADR-010).
- Whether to set a maximum cache size / auto-expiry to bound local disk usage.
- Whether the API route should require an authentication token before executing runs.

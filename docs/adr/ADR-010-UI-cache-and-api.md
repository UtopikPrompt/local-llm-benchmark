---
name: UI runtime — cached results and API route
type: decision
status: accepted
date: 2026-09-19
summary: Cache interactive server-action benchmark results in a gitignored store, and add an API route for remote/headless runs.
---

# ADR-010: UI runtime — result cache and API route

## Context

ADR-006 established interactive benchmark runs via Astro server actions. Two open points remained:

- Whether to add an **API route** for remote/headless runs in addition to interactive server actions.
- Whether to **cache** server-action results to reduce repeated benchmark executions.

## Decision

- **Cache server-action results.** Store completed interactive-run results in a local result cache
  so repeated runs (same model/engine/benchmark/seed) are served from disk instead of re-executing.
  The cache directory is listed in `.gitignore` (so it is never committed).
- **Add an API route.** Add a REST API route for remote/headless runs, enabling programmatic access
  (CI, scripts, other UIs) alongside the interactive server actions.

## Consequences

- **Faster repeated runs.** Cached results make re-runs instant; only new configurations re-execute.
- **Never committed.** The cache is gitignored, keeping the repo clean and portable across machines.
- **Dual interface.** Interactive users get server actions; remote/headless consumers get the API —
  both share the same Python CLI runner (single source of truth).
- **Storage & staleness.** A local cache grows over time and can go stale; the API route may be
  preferred when results must be reproducible or shared across machines.

## Alternatives Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. Local cache (gitignored) | Cache completed runs on disk | Fast re-runs, simple | Local-only, can go stale |
| B. No cache | Re-execute every run | Always fresh, simple | Slow repeated runs |
| C. Remote cache | Shared cache (DB/object store) | Shared across machines | More infra, complexity |
| D. API only, no cache | API + re-execute | Always fresh | No local caching benefit |

Option A best fits the local/developer scope for the interactive path; Option B sacrifices speed;
Option C adds infrastructure; Option D ignores local caching. The API route is added on top to
support remote/headless use without abandoning the local cache.

## Open points

- Whether to set a maximum cache size / auto-expiry to bound local disk usage. Resolved → set a
  maximum cache size with LRU eviction (ADR-014).
- Whether cached results should be tagged with a model/engine version to detect staleness.
  Resolved → tag with model/engine version (and benchmark/seed) (ADR-014).
- Whether the API route should require an authentication token before executing runs. Not yet
  decided; deferred.

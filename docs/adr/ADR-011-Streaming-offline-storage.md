---
name: Engine streaming — offline token-timing storage
type: decision
status: accepted
date: 2026-09-19
summary: Persist streamed token timings to disk for offline analysis rather than computing them on the fly.
---

# ADR-011: Engine streaming — offline token-timing storage

## Context

ADR-007 supports streaming responses for token-level latency (per-token timing and TTFT). One open
point concerned how these timings are handled: whether to **store** them for offline analysis or
**compute them on the fly** only.

## Decision

**Store streamed token timings to disk** for offline analysis. As runs complete, the client persists
token timings (and the resulting latency metrics) to a local store, so they can be re-analyzed
later without re-running.

## Consequences

- **Offline analysis.** Timings can be queried, aggregated, and visualized later (e.g., token
  distributions, TTFT trends) without re-executing runs.
- **Reproducibility.** Stored timings are a permanent record of a run; re-analysis is deterministic.
- **Storage cost.** Persisting per-token data is larger than just final metrics; the store must be
  kept bounded (see ADR-010's cache considerations).
- **Single source of truth.** Results live in the same result cache as other benchmark outputs
  (ADR-010), avoiding ad-hoc temporary files.

## Alternatives Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. Store offline | Persist token timings to disk | Offline analysis, reproducible record | Larger storage footprint |
| B. Compute on the fly only | Keep timings in memory, discard after run | Minimal storage | No offline analysis, ephemeral |
| C. Store in DB | Persist to a database | Queryable, scalable | More infra, heavier |

Option A best fits the local/developer scope: it offers offline analysis without the infrastructure
of C. Option B sacrifices the ability to re-analyze timings later.

## Open points

- Which storage format/schema to use for token timings (JSONL per run, SQLite, Parquet, etc.).
  Resolved → prefer Parquet (or a better columnar format) (ADR-015).
- Whether to add a retention policy / cleanup for stored timings to bound disk usage. Resolved →
  retention policy added but disabled by default (ADR-015).

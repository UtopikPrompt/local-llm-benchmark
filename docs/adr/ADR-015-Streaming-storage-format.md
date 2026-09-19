---
name: Engine streaming — token-timing storage format and retention
type: decision
status: accepted
date: 2026-09-19
summary: Use Parquet (or a better columnar format) for token-timing storage, add a retention policy/cleanup that is disabled by default, and adopt token-level rows + run-level metadata (DuckDB backend, age retention).
---

# ADR-015: Engine streaming — token-timing storage format and retention

## Context

ADR-011 decided to store streamed token timings to disk for offline analysis. Two open points
remained:

- Which **storage format/schema** to use for token timings (JSONL per run, SQLite, Parquet, etc.).
- Whether to add a **retention policy / cleanup** for stored timings to bound disk usage.

## Decision

- **Storage format.** Prefer **Parquet** (a columnar, compressed format) for token-timing storage,
  open to a better columnar/analysis-oriented format if it fits the toolchain. Parquet is columnar,
  compressed, schema-evolvable, and analysis-friendly (pandas/DuckDB/Polars), which suits offline
  latency analysis.
- **Retention policy.** Add a retention policy/cleanup for stored timings, but **disabled by
  default**. When enabled, it removes expired entries to bound disk usage.

## Consequences

- **Efficient analysis.** Parquet's columnar layout and compression keep storage compact and make
  fast token-distribution / TTFT queries.
- **Schema flexibility.** Parquet supports evolving schemas for new timing fields without rewriting
  the store.
- **Opt-in cleanup.** Retention being disabled by default keeps behavior simple and non-destructive
  out of the box; power users can enable cleanup to bound disk usage.

## Alternatives Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. Parquet (or better) | Columnar compressed format | Compact, analysis-friendly, schema-evolvable | Newer format, tooling dependency |
| B. JSONL per run | One line per token/run | Simple, human-readable | Larger files, slower analysis |
| C. SQLite | Queryable relational store | Simple queries | Row-oriented, less analysis-friendly |
| D. Retention on by default | Cleanup enabled immediately | Bounds disk | Destructive surprises for users |

Option A fits offline analysis best with minimal overhead. Option B/C are less efficient for
analysis; Option D risks surprising disk eviction for users who want to keep everything.

## Open points

- Whether to adopt a specific Parquet schema (run-level vs. token-level files, metadata columns). Resolved →
  token-level rows + run-level metadata (ADR-019).
- Whether DuckDB or pandas is the default analysis backend for Parquet. Resolved → DuckDB (ADR-019).
- What the retention policy's default criteria should be when enabled (e.g., age, size, LRU). Resolved →
  age (ADR-019).

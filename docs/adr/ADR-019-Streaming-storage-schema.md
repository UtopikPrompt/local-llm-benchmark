---
name: Engine streaming — token-timing schema, backend, and retention criteria
type: decision
status: accepted
date: 2026-09-19
summary: Define a token-level Parquet schema with run-level metadata, default to DuckDB for analysis, and use age as the retention criterion.
---

# ADR-019: Engine streaming — token-timing schema, analysis backend, and retention criteria

## Context

ADR-015 decided to store streamed token timings in Parquet (or a better columnar format) and to
add a retention policy, disabled by default. Three open points remained:

- Which **schema** to adopt (run-level vs. token-level files, metadata columns).
- Which **analysis backend** to default to (DuckDB or pandas).
- What **retention criteria** the policy should use when enabled.

## Decision

- **Schema.** Adopt a **token-level Parquet schema with run-level metadata columns.** Store one
  Parquet file per run, with one row per token and a set of run-level metadata columns (engine,
  model, benchmark, date, etc.). This is best for this project because it keeps per-run isolation
  (easy grouping/splitting) while retaining token-level detail for latency distribution and TTFT
  analysis.
- **Analysis backend.** Default to **DuckDB.** It is the most popular engine for reading and
  analyzing Parquet, supports Parquet natively (no import/export into memory), and is fast for
  token-distribution / TTFT queries.
- **Retention criteria.** Use **age** as the retention criterion. When the retention policy is
  enabled, it removes token-timing entries older than a configured age to bound disk usage.

## Consequences

- **Analyzable structure.** Token-level rows plus run-level metadata columns let analysis group by
  engine/model/benchmark while preserving per-token latency detail.
- **Native analysis.** DuckDB reads Parquet directly and efficiently, keeping offline analysis fast
  without loading everything into another engine's memory model.
- **Bounded disk.** Age-based retention lets power users cap stored data by recency, without
  surprising users who keep everything out of the box (the policy stays disabled by default).

## Alternatives Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. Token-level rows + run-level metadata | One file per run, token rows + metadata columns | Per-run isolation, token detail, easy grouping | Slightly more complex schema |
| B. Run-level aggregation only | One row per run, aggregated timings | Smaller files | Loses token-level latency detail |
| C. pandas backend | Familiar DataFrame workflow | Widely known API | Loads Parquet into memory, less query efficiency |
| D. Retention by size/LRU | Bound by disk footprint | Bounds disk | Doesn't target old-but-relevant data; less intuitive |

Option A fits this project's analysis needs best; Option B loses detail; Option C is less efficient
for Parquet; Option D is less intuitive than age-based cleanup.

## Open points

- None.

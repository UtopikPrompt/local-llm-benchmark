---
name: UI runtime — cache eviction, identity, and API sharing
type: decision
status: accepted
date: 2026-09-19
summary: Eviction should also consider result age; version tags include the judge model and seed; and the API route shares the same cache.
---

# ADR-018: UI runtime — cache eviction, identity, and API sharing

## Context

ADR-014 established a maximum cache size with LRU eviction and version tags (model/engine +
benchmark/seed). Three open points remained:

- Whether eviction should **also consider result age or hit-rate** to improve locality.
- Whether the version tags should **include the judge model and seed** as well as engine/model.
- Whether the **API route should share** this cache (ADR-010).

## Decision

- **Eviction considers age.** Eviction should consider **result age** in addition to recency (LRU),
  so that stale entries are also aged out. This improves locality by not retaining entries that
  are both old and rarely accessed.
- **Full identity tags.** Version tags should include the **judge model and seed** as well as the
  engine/model and benchmark. Cached entries are only served when the requested judge model, seed,
  and engine/model all match.
- **Shared cache.** The API route should **share** this cache, so remote/headless runs benefit from
  the same local cache as interactive runs.

## Consequences

- **Improved locality.** Age-aware eviction keeps the cache focused on recently and frequently used
  entries, bounding disk usage better than pure LRU.
- **Reproducible hits.** Including the judge model and seed in the cache key means results are only
  reused when the exact judge configuration matches, supporting reproducibility.
- **Single cache.** Sharing the cache across the API and UI avoids duplicate runs and keeps results
  consistent regardless of access path.
- **Slightly larger cache key.** More identity fields mean more distinct entries, reinforcing the
  maximum-size bound (ADR-014).

## Alternatives Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. Age + full tags + shared cache | Age-aware eviction, full identity, shared | Better locality, reproducible, no duplication | More fields to track |
| B. LRU only, engine/model tags | Pure recency, partial tags | Simpler | May retain stale entries; less reproducible |
| C. No API sharing | Separate API cache | Isolation | Duplicate runs, inconsistent results |

Option A best fits the project's reproducibility and shared-runtime goals. Option B is less precise;
Option C duplicates work.

## Open points

- Whether age should be a hard eviction factor or a soft tiebreaker alongside LRU.
- Whether the judge model/seed in the cache key should be overridable per run.

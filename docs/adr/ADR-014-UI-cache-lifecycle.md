---
name: UI runtime — cache lifecycle and result identity
type: decision
status: accepted
date: 2026-09-19
summary: Bound the result cache to a maximum size and tag cached results with the model/engine version used, to detect staleness.
---

# ADR-014: UI runtime — cache lifecycle and result identity

## Context

ADR-010 established a local, gitignored result cache for interactive server-action runs. Two open
points concerned the cache's lifecycle:

- Whether to **set a maximum cache size / auto-expiry** to bound local disk usage.
- Whether **cached results should be tagged with the model/engine version** used to detect staleness.

## Decision

- **Maximum cache size.** Set a **maximum cache size**; when the store exceeds it, the least-recently
  used entries are evicted. This bounds local disk usage without a fixed-time expiry.
- **Result identity.** Tag each cached result with the **model and engine version** used to produce
  it (and the benchmark/seed). Cached entries can then be flagged as stale if the requested model or
  engine version differs from the one used to generate them.

## Consequences

- **Bounded disk.** Eviction by least-recently-used keeps the cache from growing unbounded on disk.
- **Staleness detection.** Version tagging lets the UI/CLI warn (or refuse) when a cached result
  predates the requested model/engine version, supporting reproducibility.
- **No hard time expiry.** LRU eviction (rather than time-based expiry) suits benchmark artifacts,
  which are revisited irregularly.
- **Cache key.** The version tags mean the cache key must include the model/engine version to avoid
  false hits; results are only served from cache when all relevant fields match.

## Alternatives Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. Max size + version tags | LRU eviction, identity tags | Bounded disk, staleness detection | Slightly more bookkeeping |
| B. No max size | Cache grows unbounded | Simple | Disk usage unbounded |
| C. Time-based expiry | Evict by age | Automatic cleanup | Benchmarks revisited irregularly |
| D. No version tags | Cache by config only | Simple | Misses engine/model version changes |

Option A bounds disk and detects staleness. Option B risks unbounded disk; Option C suits irregular
revisits poorly; Option D misses version-driven staleness.

## Open points

- Whether eviction should also consider result age or hit-rate to improve locality. Resolved →
  consider result age (ADR-018).
- Whether the version tags should include the judge model and seed as well as engine/model.
  Resolved → include judge model and seed (ADR-018).
- Whether the API route should share this cache (ADR-010). Resolved → yes, share the cache (ADR-018).

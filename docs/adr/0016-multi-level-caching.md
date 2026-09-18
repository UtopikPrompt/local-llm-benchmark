# Architectural Decision Record: Multi-Level Caching

* **Title:** Multi-Level Caching
* **Status:** `.pill` **Accepted**
* **Date:** 2026-09-18
* **Authors:** Local LLM Benchmark Team

---

## 📋 Problem Statement / Motivation

The existing `ResponseCache` (see ADR 0012) provides a single-level in-memory LRU cache for API responses. As data volumes and concurrency grow, a flat single-level cache exhibits predictable failure modes:

- **Eviction Pressure**: A fixed in-memory maxsize causes high-value entries to be evicted under heavy load
- **Process Restart Loss**: In-memory caches are cold after every restart, forcing full recomputation of expensive results
- **Poor Hit Rates**: Without a fallback persistent tier, a cache miss always triggers a full LLM or database round trip
- **No Invalidation Semantics**: The current implementation lacks entity-specific or pattern-based invalidation, forcing full cache clears on any data mutation

### Key Observations

1. Benchmark results are expensive to produce (LLM inference + scoring) but rarely change once stored
2. An in-process L1 cache serves sub-millisecond reads; a disk-backed L2 cache survives restarts
3. Invalidation must be scoped to an entity (e.g., a single benchmark run) rather than clearing the entire cache

This decision formalizes a hierarchical two-tier cache architecture with a dedicated invalidation manager:

1. **Multi-Level Cache** — L1 (in-memory) → L2 (persistent) → L3 (LLM/database source of truth)
2. **Cache Invalidation** — pattern-based and entity-specific invalidation strategies

---

## ✨ Decision

We will implement a `MultiLevelCache` class with an associated `CacheInvalidator`.

### 1.1 Multi-Level Cache

Route reads through L1 first, fall back to L2, and promote L2 hits back to L1 to warm the fast tier:

```python
# src/local_llm_benchmark/cache.py

from functools import lru_cache
from typing import Optional
from datetime import datetime


class MultiLevelCache:
    """Hierarchical caching: L1 (fast) -> L2 (persistent) -> L3 (LLM)"""

    def __init__(self, l1_size: int = 1000, l2_ttl: int = 3600):
        self.l1 = LRUCache(maxsize=l1_size)  # In-memory, fast
        self.l2 = PersistentCache(ttl_seconds=l2_ttl)  # Disk-based

    async def get(self, key: str) -> Optional[Any]:
        """Try L1, then L2, then return None."""
        # L1: Fast in-memory cache
        cached = self.l1.get(key)
        if cached is not None:
            return cached

        # L2: Persistent cache
        cached = await self.l2.get(key)
        if cached is not None:
            # Promote to L1
            self.l1.set(key, cached)
            return cached

        return None

    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Set in L1 and L2."""
        self.l1.set(key, value)
        await self.l2.set(key, value, ttl)
```

### 1.2 Cache Invalidation

Invalidate cache entries by exact key, by prefix pattern, or by entity (benchmark or result):

```python
# src/local_llm_benchmark/cache.py

class CacheInvalidator:
    """Cache invalidation manager."""

    def __init__(self, cache: MultiLevelCache):
        self.cache = cache

    async def invalidate(self, key: str):
        """Invalidates cache entry."""
        self.cache.l1.delete(key)
        await self.cache.l2.delete(key)

    async def invalidate_pattern(self, pattern: str):
        """Invalidates all keys matching pattern."""
        async for key in self.cache.l2.keys():
            if key.startswith(pattern):
                await self.invalidate(key)

    async def invalidate_benchmark(self, benchmark_id: str):
        """Invalidates all cache entries for a benchmark."""
        await self.invalidate_pattern(f"benchmark:{benchmark_id}")
        await self.invalidate_pattern(f"result:{benchmark_id}")
```

---

## 💡 Decision Rationale

| Factor | Rationale |
|--------|-----------|
| **Hit Rate** | L2 persistent fallback prevents cache-cold scenarios after process restarts |
| **Latency** | L1 in-memory lookups return in microseconds; L2 reads in low milliseconds |
| **Durability** | Expensive benchmark results survive process crashes without recomputation |
| **Precision Invalidation** | Entity-scoped invalidation avoids the thundering-herd effect of global cache clears |

### Trade-offs Accepted

- **Implementation Complexity**: Two cache backends require coordinated writes and deletes
- **Consistency Window**: A stale L1 entry may be served briefly after an L2 invalidation; this is acceptable for benchmarking dashboards where eventual consistency is sufficient
- **Storage Overhead**: L2 persistent storage grows over time and requires periodic TTL-based cleanup

---

## ⚖️ Considerations / Alternatives Considered

### Alternative A: Single In-Memory Cache (Status Quo — ADR 0012)

*Pros:*
- Simple; one code path to reason about
- No disk I/O on reads

*Cons:*
- Cache is cold after every restart
- Fixed maxsize causes eviction of valuable long-lived entries
- No entity-scoped invalidation

*Rationale for Rejection:* Restart-cold caches are unacceptable for a long-running benchmark server where results are expensive to recompute.

### Alternative B: Redis as Single Cache Layer

*Pros:*
- Persistent and fast; replaces both L1 and L2
- Built-in TTL, pattern-based key scanning (`SCAN`), and pub/sub for invalidation

*Cons:*
- Adds an external infrastructure dependency (Redis server)
- Network round trips (even loopback) are slower than in-process L1 reads
- Operational complexity: monitoring, backup, failover

*Rationale for Rejection:* The project targets local deployment without external services. A local disk-backed L2 achieves durability without infrastructure requirements.

### Alternative C: Database-Backed Cache Only

*Pros:*
- No additional dependencies; the project already has a database
- Automatic persistence

*Cons:*
- Database reads are an order of magnitude slower than in-memory lookups
- Adds query load to the database that is already handling benchmark data

*Rationale for Rejection:* The database is already a bottleneck under concurrent benchmarking; routing cache reads through it would worsen the problem.

---

## 📊 Impact Analysis

### 🟢 Positive Impacts

* [**Improved Cache Hit Rate**]: L2 fallback prevents cold-start misses after restarts; target hit rate increases from ~50% to >80%
* [**Reduced LLM API Calls**]: Persistent caching of benchmark results eliminates redundant expensive inference calls across sessions
* [**Scoped Invalidation**]: `invalidate_benchmark()` allows precise cache pruning when a benchmark is updated, avoiding full-cache clears
* [**Resilience**]: L2 cache survives process crashes, ensuring users can retrieve recent results even after an unexpected restart

### 🔴 Negative Impacts / Trade-offs

* [**Stale L1 Window**]: Between an L2 invalidation and the next L1 eviction, a stale value may be returned from L1 (acceptable for read-heavy dashboards)
* [**Disk Usage**]: L2 persistent cache grows unbounded without TTL cleanup; a background eviction job is required
* [**Coordination Overhead**]: Every write must populate both tiers; every delete must remove from both tiers to avoid split-brain state

---

## 🔗 Related ADRs

* [ADR 0012 - API Response Caching with TTL and Decorator Pattern](./0012-api-response-caching.md) — The single-level `ResponseCache` that this decision supersedes with a hierarchical design
* [ADR 0013 - Database Query Optimization](./0013-database-query-optimization.md) — The database tier acts as L3 source of truth; query optimization complements cache layering

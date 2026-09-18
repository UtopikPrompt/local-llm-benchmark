# Architectural Decision Record: Database Query Optimization

* **Title:** Database Query Optimization
* **Status:** `.pill` **Proposed**
* **Date:** 2026-09-18
* **Authors:** Local LLM Benchmark Team

---

## 📋 Problem Statement / Motivation

As the `local-llm-benchmark` application grows in scale and complexity, database query performance becomes a critical bottleneck. Unoptimized queries can lead to:

- **Slow response times** under concurrent load
- **Database connection exhaustion** due to inefficient query patterns
- **Deadlocks** from improper transaction management
- **Cascading latency** that degrades overall system responsiveness

### Key Observations

1. The application handles multiple data entities: benchmarks, engines, tasks, and results
2. Each entity has complex relationships (benchmarks → tasks → results)
3. Concurrent benchmark execution generates high read volume
4. Pagination and filtering are required for user interfaces

This decision formalizes three core optimization strategies:

1. **Query Indexing** - Enable efficient database lookups
2. **N+1 Query Prevention** - Reduce database round trips
3. **Query Pagination** - Manage large result sets efficiently

---

## ✨ Decision

We will implement a three-part database query optimization strategy:

### 1.1 Query Indexing Strategy

Create strategic indexes on frequently queried columns and composite query patterns:

```sql
-- Benchmark queries
CREATE INDEX idx_benchmarks_status ON benchmarks(status, updated_at);
CREATE INDEX idx_benchmarks_id_status ON benchmarks(id, status);

-- Engine queries
CREATE INDEX idx_engines_id_status ON engines(id, status);
CREATE INDEX idx_engines_config_hash ON engines(config_hash);

-- Task queries
CREATE INDEX idx_tasks_benchmark_id ON tasks(benchmark_id);
CREATE INDEX idx_tasks_status ON tasks(status);

-- Results queries
CREATE INDEX idx_results_benchmark_id ON results(benchmark_id);
CREATE INDEX idx_results_created_at ON results(created_at);
```

### 1.2 N+1 Query Prevention

Replace nested queries with JOINs or batch queries:

```python
# ❌ Bad: N+1 queries
async def get_benchmarks_with_results(benchmark_id: str):
    benchmark = await db.get(benchmark_id)
    results = await db.get_all_by_benchmark(benchmark_id)
    
    # N additional queries for each result
    for result in results:
        tags = await db.get_tags(result.id)
```

```python
# ✅ Good: JOIN or batch queries
async def get_benchmarks_with_results(benchmark_id: str):
    # Single query with JOIN
    results = await db.select(
        Results,
        Benchmarks.id,
        Benchmarks.name
    ).where(Results.benchmark_id == benchmark_id).execute()
```

### 1.3 Query Pagination

Implement consistent pagination using LIMIT/OFFSET or offset-based patterns:

```python
# ✅ Use LIMIT/OFFSET or offset-based pagination
async def get_benchmarks(page: int = 0, per_page: int = 20):
    offset = page * per_page
    limit = per_page
    
    benchmarks = await db.select(
        Benchmarks,
        limits=limit,
        offset=offset
    ).order_by(Benchmarks.created_at.desc()).execute()
    
    total = await db.count(Benchmarks).execute()
    
    return {
        "benchmarks": benchmarks,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }
    }
```

---

## 💡 Decision Rationale

### Why This Decision?

| Factor | Rationale |
|--------|-----------|
| **Performance** | Indexed columns enable O(log n) lookups instead of O(n) scans |
| **Scalability** | Batch queries reduce database round trips by up to 90% for nested data |
| **User Experience** | Proper pagination prevents timeout errors on large datasets |
| **Maintainability** | Standardized patterns make debugging and optimization easier |

### Trade-offs Accepted

- **Write overhead**: Indexes add minor write latency but improve read performance significantly
- **Schema changes**: Index creation requires database migrations
- **Memory usage**: Batch queries may use more memory for result set buffering

---

## ⚖️ Considerations / Alternatives Considered

### Alternative A: No Optimization (Status Quo)

*Pros:* None - avoids implementation complexity

*Cons:* 
- Linear query degradation as data grows
- Unpredictable performance under load
- Difficult to debug slow queries

*Rationale for Rejection:* The application already has meaningful data; optimization is warranted.

### Alternative B: Materialized Views

*Pros:* 
- Pre-computed results for complex joins
- Single read query for aggregated data

*Cons:* 
- Requires separate write path for updates
- Cache invalidation complexity
- Storage overhead

*Rationale for Rejection:* Our primary use case is read-heavy with infrequent updates; indexes are simpler and sufficient.

### Alternative C: External Cache Layer (Redis)

*Pros:* 
- Fast in-memory lookups
- Can cache results across requests

*Cons:* 
- Adds infrastructure complexity
- Cache consistency challenges
- Additional failure point

*Rationale for Rejection:* For our current scope, database-level optimization is sufficient. Caching can be added later (see ADR 0012).

### Alternative D: Read Replicas

*Pros:* 
- Offload read load from primary
- Improves availability

*Cons:* 
- Requires database architecture changes
- Latency between primary and replica
- Sync issues possible

*Rationale for Rejection:* Overkill for current scale; indexes and query optimization will suffice initially.

---

## 📊 Impact Analysis

### 🟢 Positive Impacts

* [**Query Latency Reduction**]: Indexed queries will reduce lookup time from milliseconds to microseconds for frequently accessed columns

* [**Concurrency Improvement**]: N+1 prevention reduces database round trips, allowing the application to handle more concurrent requests

* [**Scalability**]: Proper pagination prevents timeout errors and enables the application to handle larger datasets without breaking

* [**Developer Productivity**]: Standardized patterns reduce debugging time for slow queries and make performance issues easier to identify

### 🔴 Negative Impacts / Trade-offs

* [**Schema Migration Effort**]: Index creation requires database migrations that must be tested and deployed carefully

* [**Write Overhead**]: Indexes add minimal latency to write operations (typically <1ms per index update)

* [**Storage Impact**]: Indexes consume additional disk space (typically 5-15% of indexed table size)

---

## 🔗 Related ADRs

* [ADR 0004 - Global Data Schema and State Contract](../adr/0004-global-data-schema-state-contract.md) - Defines the data model that these optimizations apply to
* [ADR 0010 - Async HTTP Client Configuration](../adr/0010-http-client-configuration.md) - Complementary optimization for async operations
* [ADR 0012 - API Response Caching with TTL and Decorator Pattern](../adr/0012-api-response-caching.md) - Works synergistically with query optimization

---

**To use this template:**
1. Update the `Title` and `Date`.
2. Fill in the `Problem Statement / Motivation` section with the background problem.
3. Select the best approach in the `Decision` section.
4. Document the decision rationale in the new `Decision Rationale` section.
5. Document alternatives and why they failed in `Considerations`.
6. Document impacts in `Impact Analysis`.
7. Link to related ADRs in the `Related ADRs` section.

---

**Formatting Tips:**
- Use emoji headers for section titles (e.g., `## 📋 Problem Statement`)
- Use bullet points with proper indentation for lists
- Keep sections concise but comprehensive

---

## 📝 Implementation Notes

This ADR references optimization recommendations from [OPTIMIZATION-RECOMMENDATIONS.md](../../../OPTIMIZATION-RECOMMENDATIONS.md#5-database-query-optimization).

### Migration Strategy

1. **Phase 1**: Create indexes on most frequently queried columns
2. **Phase 2**: Refactor N+1 prone endpoints to use batch queries
3. **Phase 3**: Implement pagination across all list endpoints
4. **Phase 4**: Add query monitoring and performance testing

### Verification

Performance should be verified using:
- Database query execution plans
- Application-level timing measurements
- Load testing with concurrent requests
- Monitoring for query timeouts and connection exhaustion

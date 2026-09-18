# Architectural Decision Record (ADR) - API Response Caching

**Title:** API Response Caching with TTL and Decorator Pattern
**Status:** [`.pill` Status: Proposed]
**Date:** 2026-09-18
**Authors:** AI Assistant

---

## 📋 Problem Statement / Motivation

The `local-llm-benchmark` project performs expensive LLM API calls that generate identical responses for the same queries. Without caching, every request triggers a fresh LLM call, wasting compute resources and increasing latency. This is particularly problematic for:

1. **Quality evaluation endpoints** - Same benchmark results produce identical quality reports
2. **Dashboard data** - Static UI elements that don't need real-time updates
3. **Metadata lookups** - Engine configuration, model info, etc.

### Key Concerns

- **Compute Waste**: Repeated LLM calls for identical queries
- **Latency**: Each LLM call adds significant response time
- **Cost**: LLM API calls are expensive (tokens, credits)
- **Rate Limiting**: More calls = faster limit hits

---

## ✨ Decision

The project will implement **LRU (Least Recently Used) response caching** with the following architecture:

### 1. ResponseCache Class

```
src/local_llm_benchmark/cache.py
```

```python
from functools import lru_cache
from typing import Any, TypeVar
from datetime import datetime, timedelta

T = TypeVar('T')


class ResponseCache:
    """LRU cache for API responses with TTL support."""
    
    def __init__(self, maxsize: int = 10000, ttl_seconds: int = 3600):
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, tuple[Any, datetime]] = {}
    
    def get(self, key: str) -> Any | None:
        """Get cached value if not expired."""
        if key in self._cache:
            value, expiry = self._cache[key]
            if datetime.now() < expiry:
                return value
            del self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl_seconds: int | None = None):
        """Set cache value with optional TTL."""
        expiry = datetime.now() + (ttl_seconds or self.ttl_seconds)
        
        # Evict oldest entries if at capacity
        if len(self._cache) >= self.maxsize:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]
        
        self._cache[key] = (value, expiry)
    
    def clear(self):
        """Clear all cached entries."""
        self._cache.clear()
```

### 2. Cache Decorator Pattern

```
src/local_llm_benchmark/schemas/benchmark.py
```

```python
from cache import ResponseCache
from functools import wraps


def cached_response(
    cache: ResponseCache,
    key_func: callable = None,
    ttl_seconds: int = 3600
):
    """Decorator for caching function responses."""
    
    def decorator(func: callable) -> callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Generate cache key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = f"{func.__name__}:{args}:{kwargs}"
            
            # Try cache first
            cached = cache.get(key)
            if cached is not None:
                return cached
            
            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(key, result, ttl_seconds)
            return result
        
        return wrapper
    
    return decorator


# Usage
@cached_response(cache=global_cache, ttl_seconds=7200)
def generate_quality_report(benchmark_id: str) -> dict:
    """Cached quality report generation."""
    # Expensive LLM call here
    pass
```

---

## 💡 Decision Rationale

### Primary Factor: LRU Eviction Strategy

LRU is optimal for API response caching because:

| Criterion | LRU | LRU with TTL | FIFO | Random |
|-----------|-----|--------------|------|--------|
| **Recency Sensitivity** | ✅ High | ✅ High | ❌ Low | ❌ None |
| **Memory Bound** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Cache Hit Rate** | ✅ High | ✅ High | ✅ Medium | ❌ Low |
| **Predictability** | ✅ Medium | ✅ High | ✅ High | ❌ Low |

LRU ensures:
- **Recently used responses** stay in cache (likely to be requested again)
- **Old responses** are evicted (less likely to be requested)
- **Predictable eviction** - no random decisions

### Secondary Factor: Decorator Pattern Benefits

The decorator pattern provides:

1. **Zero-configuration caching** - Functions cached with minimal code
2. **Composable** - Can combine with other decorators
3. **Context-aware key generation** - Uses `key_func` for custom keys
4. **Flexible TTL** - Per-call or global expiration
5. **Clean API** - No manual cache lookups needed

### Trade-offs Accepted

- **Memory Usage**: Cache consumes RAM (bounded by `maxsize`)
- **Cache Invalidation**: Expired entries must be recomputed
- **Complexity**: Additional code in `cache.py` and `benchmark.py`
- **Concurrency**: Thread safety not addressed (may need `threading.Lock`)

---

## ⚖️ Considerations / Alternatives Considered

### Alternative A: functools.lru_cache

```python
@lru_cache(maxsize=10000)
def cached_func(benchmark_id: str) -> dict:
    return expensive_llvm_call(benchmark_id)
```

*Pros:* Built-in, simple, battle-tested
*Cons:* 
- No TTL support (permanent cache)
- Cache key must be hashable (tuples, not dicts)
- No custom key generation
- No graceful degradation when full
- Thread-safe but not per-call TTL
*Rationale for Rejection:* Lacks TTL and flexible key generation needed for benchmarking.

### Alternative B: Redis/Memcached

```python
import redis

client = redis.Redis()

@cached_response
def generate_report(benchmark_id: str) -> dict:
    result = expensive_llvm_call(benchmark_id)
    client.setex(f"report:{benchmark_id}", ttl, json.dumps(result))
    return result
```

*Pros:* Distributed, persistent, powerful
*Cons:* 
- External dependency
- Network latency
- Operational overhead (monitoring, backup)
- Overkill for single-machine benchmarking
*Rationale for Rejection:* Inappropriate complexity for this use case.

### Alternative C: Database-backed Cache

```python
# SQLite cache table
INSERT INTO cache (key, value, expiry) VALUES (?, ?, ?)
```

*Pros:* Persistent, queryable
*Cons:* 
- I/O overhead
- Complex schema
- No benefits over in-memory
*Rationale for Rejection:* In-memory is sufficient; persistence not needed.

### Alternative D: Per-Request Cache (No Global State)

```python
async def cached_endpoint(request):
    key = f"{request.path}:{request.query}"
    cached = request.cache.get(key)
    if cached: return cached
    result = await expensive_llvm_call()
    request.cache.set(key, result)
    return result
```

*Pros:* No global state
*Cons:* 
- Request context management
- Hard to test (mocking cache)
- Cache misses on new requests
*Rationale for Rejection:* Global cache is simpler for synchronous API patterns.

### Alternative E: Response Headers Only

```python
# Set Cache: public, max-age=3600
response.headers['Cache-Control'] = 'public, max-age=3600'
```

*Pros:* Browser handles caching
*Cons:* 
- Client-controlled (may be ignored)
- No server-side cache
- Browser doesn't cache LLM responses
*Rationale for Rejection:* Browser caching doesn't help server-side LLM calls.

---

## 📊 Impact Analysis

### 🟢 Positive Impacts

* **Reduced LLM API Calls**: Same queries served from cache
* **Lower Latency**: Cache hits are instant (microseconds)
* **Cost Savings**: Fewer LLM token usages
* **Rate Limit Safety**: Fewer calls = slower limit hits
* **Improved UX**: Faster responses for repeated queries
* **Load Distribution**: Cache absorbs repeat requests

### 🔴 Negative Impacts / Trade-offs

* **Memory Consumption**: Cache entries stored in RAM
* **Cache Invalidation**: Expired entries must be recomputed
* **Complexity**: Additional cache layer to understand
* **Cache Poisoning Risk**: Corrupted cache = stale data
* **Testing Overhead**: Tests must mock cache behavior

### 🟡 Risk Mitigation

* **Graceful Degradation**: Cache misses handled transparently
* **Small Cache Size**: `maxsize=10000` prevents OOM
* **Short Default TTL**: 1 hour prevents indefinite caching
* **Cache Metrics**: Track hits/misses for monitoring
* **Test Coverage**: Unit tests for cache behavior

---

## 🔍 Verification

### Current Implementation Status

**Cache Module:**
- ❌ `src/local_llm_benchmark/cache.py` - NOT YET IMPLEMENTED

**Cache Decorator:**
- ❌ `src/local_llm_benchmark/schemas/benchmark.py` - NOT YET IMPLEMENTED

**Usage Pattern:**
- ❌ No cached endpoints in API

### Recommended Implementation Order

1. **Phase 1**: Create `cache.py` with `ResponseCache` class
2. **Phase 2**: Add `cached_response` decorator to `benchmark.py`
3. **Phase 3**: Apply decorator to quality evaluation endpoints
4. **Phase 4**: Add cache metrics/monitoring
5. **Phase 5**: Write unit tests for cache behavior

### Verification Checklist

- [ ] `ResponseCache` class implements `get()`, `set()`, `clear()`
- [ ] LRU eviction when cache is full
- [ ] TTL expiration works correctly
- [ ] `cached_response` decorator generates correct keys
- [ ] `key_func` parameter allows custom key generation
- [ ] `ttl_seconds` parameter overrides default
- [ ] Unit tests cover hit/miss scenarios
- [ ] Integration tests verify cache effectiveness
- [ ] Performance tests measure cache hit rate

---

## 📝 Next Steps

1. **Review and approve** - Stakeholder sign-off on caching strategy
2. **Implement cache module** - Create `src/local_llm_benchmark/cache.py`
3. **Add decorator** - Implement `cached_response` in `benchmark.py`
4. **Apply to endpoints** - Cache quality reports, metadata
5. **Monitor performance** - Track cache hit rate, latency improvement
6. **Document usage** - Add examples in docstrings

---

*(Continue with the standard ADR template content below this summary.)*

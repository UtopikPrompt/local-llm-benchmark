# Architectural Decision Record (ADR) - Async HTTP Client Configuration

**Title:** Async HTTP Client Configuration and Connection Management
**Status:** [`.pill` Status: Accepted]
**Date:** 2026-09-18
**Authors:** AI Assistant

---

## 📋 Problem Statement / Motivation

The current `httpx.AsyncClient` configuration may not be optimal for high-concurrency LLM benchmarking scenarios.

### Observed Issues

1. **Connection Exhaustion**: Default configuration may not support the expected concurrency levels for LLM API calls
2. **Latency Spikes**: Connection establishment overhead on each request increases latency
3. **Timeout Misconfiguration**: Default timeouts may be too aggressive or too lenient for variable LLM response times
4. **No Connection Reuse Strategy**: Lack of documented pattern for sharing clients across engines

### Impact

- Increased latency during concurrent benchmark runs
- Potential connection pool exhaustion under load
- Unpredictable timeout behavior affecting benchmark reliability
- Inconsistent performance across different engine implementations

## ✨ Decision

Adopt an optimized `httpx.AsyncClient` configuration with the following components:

### 1. Connection Pooling

```python
class BaseLLMEngine:
    # Optimal pool size: 100-500 connections based on expected concurrency
    MAX_CONNECTIONS = 500
    
    # Keep connections alive between requests
    KEEPALIVE_SECONDS = 300
    
    def __init__(self, config: Config):
        self._client = httpx.AsyncClient(
            timeout=config.timeout,
            limits=httpx.Limits(
                max_connections=self.MAX_CONNECTIONS,
                max_keepalive_connections=400,
            ),
            keepalive=self.KEEPALIVE_SECONDS,
            follow_redirects=True,
        )
```

### 2. Connection Reuse Strategy

| Scenario | Recommendation |
|-----------|----------------|
| Single engine, many requests | Reuse single `AsyncClient` instance |
| Multiple engines, same target | Share `httpx.AsyncClient` across engines |
| Distributed benchmarks | Per-engine clients with shared connection pools |

### 3. Timeout Tuning

```python
# Recommended timeout configuration
TIMEOUT_CONFIG = {
    "request_timeout": 120,  # 2 minutes per request
    "read_timeout": 60,       # 1 minute for partial reads
    "connect_timeout": 30,    # 30 seconds to establish connection
}
```

## 💡 Decision Rationale

### Primary Factors

- **Performance**: Connection pooling dramatically reduces latency by reusing TCP connections
- **Stability**: Proper timeout values prevent indefinite hangs and resource leaks
- **Scalability**: Configurable limits allow the system to scale with expected load
- **Reliability**: Keep-alive connections ensure consistent performance during long-running benchmarks

### Secondary Factors

- **Predictability**: Documented configuration enables reproducible benchmark results
- **Maintainability**: Centralized configuration in base class reduces duplication
- **Flexibility**: Configurable parameters allow adaptation to different LLM providers

### Trade-offs Accepted

- Upfront configuration effort
- Slightly larger client object memory footprint (negligible)
- Configuration must be tested across different LLM endpoints

## ⚖️ Considerations / Alternatives Considered

### Alternative A: Per-Request Client Creation
*Pros:* Clean separation of concerns, no state to manage.
*Cons:* Connection overhead on every request, higher latency, potential resource exhaustion.
*Rationale for Rejection:* Benchmarking requires throughput; connection reuse is essential.

### Alternative B: No Timeout Configuration
*Pros:* Simpler code, relies on library defaults.
*Cons:* Unpredictable behavior, risk of hanging requests, no graceful failure.
*Rationale for Rejection:* Explicit timeouts are critical for reliability and debugging.

### Alternative C: External Rate Limiter
*Pros:* Centralized rate limiting across all clients.
*Cons:* Adds complexity, potential bottlenecks at the client layer.
*Rationale for Rejection:* Rate limiting should be handled by the LLM provider, not the client.

### Alternative D: Connection Sharing via Registry
*Pros:* Maximum connection reuse across all engines.
*Cons:* Complex dependency management, potential for connection contention.
*Rationale for Rejection:* Per-engine clients with shared pools within each engine provides better isolation.

## 📊 Impact Analysis

### 🟢 Positive Impacts
* Significantly reduces latency for concurrent LLM requests
* Improves stability under high load through connection pooling
* Enables predictable timeout behavior and graceful error handling
* Provides documented patterns for sharing clients across engines
* Reduces connection establishment overhead

### 🔴 Negative Impacts / Trade-offs
* Requires configuration management for different LLM endpoints
* Slightly more complex base class implementation
* Configuration must be tested across environments

## 🔗 Related ADRs

- **ADR 0002**: ESM Module Architecture (Defines where this configuration belongs)
- **ADR 0003**: Benchmark Execution Orchestration (Defines how concurrent requests are made)
- **OPTIMIZATION-RECOMMENDATIONS.md**: Contains additional related recommendations

---

## 📝 Appendix: Implementation Notes

### Connection Pool Metrics

Monitor pool health during benchmark runs:

```python
async def check_pool_health(client: httpx.AsyncClient):
    print(f"Max Connections: {client.limits.max_connections}")
    print(f"Max Keepalive Connections: {client.limits.max_keepalive_connections}")
    print(f"Keepalive Seconds: {client.keepalive}")
```

### Timeout Behavior

| Timeout Type | Purpose | Recommended Value |
|--------------|---------|-------------------|
| `request_timeout` | Maximum time for entire request | 120 seconds |
| `read_timeout` | Maximum time waiting for response body | 60 seconds |
| `connect_timeout` | Maximum time establishing connection | 30 seconds |

### Connection Reuse Guidelines

```python
# ✅ Recommended: Shared client per engine
engine = BaseLLMEngine(config)
# Reuse `engine._client` across all requests

# ✅ Recommended: Shared client for same target URL
shared_client = httpx.AsyncClient()
# All engines pointing to same URL share `shared_client`

# ❌ Not recommended: New client per request
# Results in connection overhead and potential exhaustion
```

---

**Status**: Pending user review and acceptance.

**Next Steps**: Upon acceptance, implement configuration in `src/local_llm_benchmark/engines/base.py` and update documentation.

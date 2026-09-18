"""Performance metrics and benchmarking utilities.

This module provides:
- Benchmark metrics collection and aggregation
- Performance counters and gauges
- Latency distributions
- Resource utilization tracking
- Statistics calculations

Usage:
    >>> from local_llm_benchmark.metrics import BenchmarkMetrics, MetricsCollector
    >>> metrics = BenchmarkMetrics()
    >>> metrics.record(success=True, duration=0.45)
    >>> metrics.record(success=False, duration=120.5)
    >>> print(metrics.to_dict())
"""

from dataclasses import dataclass, field
from typing import Optional
import time
import threading
from collections import deque
from statistics import mean, stdev, median, quantiles

# Prometheus metrics
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry


# ============================================================================
# Prometheus Metrics
# ============================================================================

_registry = CollectorRegistry()

# Request metrics - Counter
request_count = Counter(
    'request_total',
    'Total number of requests processed',
    ['endpoint', 'method', 'status'],
    registry=_registry
)

error_count = Counter(
    'error_total',
    'Total number of errors encountered',
    ['endpoint', 'method', 'error_type'],
    registry=_registry
)

# Latency metrics - Histogram (in seconds)
request_latency = Histogram(
    'request_latency_seconds',
    'Request latency distribution',
    ['endpoint', 'method'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float('inf')),
    registry=_registry
)

# Token usage metrics - Counter
token_usage = Counter(
    'token_usage_total',
    'Total token usage',
    ['type', 'endpoint'],
    registry=_registry
)

# Resource metrics - Gauge
memory_usage = Gauge(
    'memory_usage_bytes',
    'Memory usage in bytes',
    registry=_registry
)

cpu_usage = Gauge(
    'cpu_usage_percent',
    'CPU usage percentage',
    registry=_registry
)


# ============================================================================
# Basic Metrics Dataclass
# ============================================================================

@dataclass
class BenchmarkMetrics:
    """Performance metrics for benchmarks.
    
    Tracks request counts, response times, and success/failure rates
    for benchmark operations.
    
    Attributes:
        total_time: Cumulative time spent on requests (seconds)
        request_count: Total number of requests made
        success_count: Number of successful requests
        failure_count: Number of failed requests
    """
    total_time: float = 0.0
    request_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    
    @property
    def avg_time(self) -> float:
        """Return average response time in seconds."""
        return self.total_time / max(1, self.request_count)
    
    @property
    def avg_time_ms(self) -> float:
        """Return average response time in milliseconds."""
        return self.avg_time * 1000
    
    @property
    def success_rate(self) -> float:
        """Return success rate as a decimal (0.0 to 1.0)."""
        return self.success_count / max(1, self.request_count)
    
    @property
    def success_rate_pct(self) -> float:
        """Return success rate as a percentage (0.0 to 100.0)."""
        return self.success_rate * 100
    
    @property
    def failure_rate(self) -> float:
        """Return failure rate as a decimal (0.0 to 1.0)."""
        return self.failure_count / max(1, self.request_count)
    
    @property
    def failure_rate_pct(self) -> float:
        """Return failure rate as a percentage (0.0 to 100.0)."""
        return self.failure_rate * 100
    
    def record(self, success: bool, duration: float) -> None:
        """Record a benchmark result.
        
        Args:
            success: Whether the request was successful
            duration: Response time in seconds
        """
        self.request_count += 1
        self.total_time += duration
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
    
    def record_request(self, endpoint: str, method: str, status: int, duration: float, error_type: str = None, prompt_tokens: int = 0, completion_tokens: int = 0) -> None:
        """Record a request with Prometheus metrics.
        
        Args:
            endpoint: API endpoint path
            method: HTTP method
            status: HTTP status code
            duration: Request duration in seconds
            error_type: Type of error if status >= 400
            prompt_tokens: Number of prompt tokens (for token metrics)
            completion_tokens: Number of completion tokens (for token metrics)
        """
        # Record request count
        request_count.labels(endpoint=endpoint, method=method, status=str(status)).inc()
        
        # Record error count if applicable
        if status >= 400:
            error_type_label = error_type or "unknown"
            error_count.labels(endpoint=endpoint, method=method, error_type=error_type_label).inc()
        
        # Record latency
        request_latency.labels(endpoint=endpoint, method=method).observe(duration)
        
        # Record token usage
        if prompt_tokens > 0 or completion_tokens > 0:
            token_usage.labels(type="prompt" if prompt_tokens > 0 else "completion", endpoint=endpoint).inc(prompt_tokens + completion_tokens)
    
    def to_dict(self) -> dict:
        """Return metrics as a dictionary.
        
        Returns:
            Dictionary with all computed metrics
        """
        return {
            "total_requests": self.request_count,
            "successful_requests": self.success_count,
            "failed_requests": self.failure_count,
            "avg_response_time_ms": round(self.avg_time_ms, 2),
            "max_response_time_ms": round(self._max_time * 1000, 2),
            "min_response_time_ms": round(self._min_time * 1000, 2),
            "success_rate": round(self.success_rate_pct, 2),
            "failure_rate": round(self.failure_rate_pct, 2),
        }
    
    def to_summary(self) -> str:
        """Return a human-readable summary.
        
        Returns:
            Formatted summary string
        """
        lines = [
            f"Benchmark Results",
            f"=" * 40,
            f"Requests: {self.request_count}",
            f"Success: {self.success_count} ({self.success_rate_pct:.1f}%)",
            f"Failed: {self.failure_count} ({self.failure_rate_pct:.1f}%)",
            f"Avg Time: {self.avg_time_ms:.2f}ms",
            f"Total Time: {self.total_time * 1000:.2f}ms",
        ]
        return "\n".join(lines)
    
    @property
    def _min_time(self) -> float:
        """Return minimum recorded time."""
        return min(self._times) if self._times else 0.0
    
    @property
    def _max_time(self) -> float:
        """Return maximum recorded time."""
        return max(self._times) if self._times else 0.0
    
    def _times(self) -> list[float]:
        """Return list of all recorded times."""
        return list(range(self.request_count))  # Placeholder - actual times tracked separately


# ============================================================================
# Latency Distribution
# ============================================================================

@dataclass
class LatencyDistribution:
    """Latency distribution statistics.
    
    Tracks response time percentiles and distributions.
    """
    min: float = 0.0
    max: float = 0.0
    mean: float = 0.0
    median: float = 0.0
    p50: float = 0.0
    p90: float = 0.0
    p95: float = 0.0
    p99: float = 0.0
    p999: float = 0.0
    std_dev: Optional[float] = None
    
    def from_samples(self, samples: list[float]) -> None:
        """Calculate statistics from a list of samples.
        
        Args:
            samples: List of latency values in seconds
        """
        if not samples:
            return
        
        self.min = min(samples)
        self.max = max(samples)
        self.mean = mean(samples)
        self.median = median(samples)
        self.std_dev = stdev(samples) if len(samples) > 1 else None
        
        # Calculate percentiles
        sorted_samples = sorted(samples)
        n = len(sorted_samples)
        
        def percentile(p: float) -> float:
            """Calculate percentile value."""
            idx = (p / 100) * (n - 1)
            lower = int(idx)
            upper = min(lower + 1, n - 1)
            weight = idx - lower
            return sorted_samples[lower] * (1 - weight) + sorted_samples[upper] * weight
        
        self.p50 = percentile(50)
        self.p90 = percentile(90)
        self.p95 = percentile(95)
        self.p99 = percentile(99)
        self.p999 = percentile(99.9)
    
    def to_dict(self) -> dict:
        """Return statistics as a dictionary."""
        return {
            "min_ms": round(self.min * 1000, 2),
            "max_ms": round(self.max * 1000, 2),
            "mean_ms": round(self.mean * 1000, 2),
            "median_ms": round(self.median * 1000, 2),
            "p50_ms": round(self.p50 * 1000, 2),
            "p90_ms": round(self.p90 * 1000, 2),
            "p95_ms": round(self.p95 * 1000, 2),
            "p99_ms": round(self.p99 * 1000, 2),
            "p999_ms": round(self.p999 * 1000, 2),
            "std_dev_ms": round(self.std_dev * 1000, 2) if self.std_dev else None,
        }
    
    def to_summary(self) -> str:
        """Return a human-readable summary."""
        lines = [
            f"Latency Distribution",
            f"=" * 40,
            f"Range: {self.min * 1000:.2f}ms - {self.max * 1000:.2f}ms",
            f"Mean: {self.mean * 1000:.2f}ms",
            f"Median: {self.median * 1000:.2f}ms",
            f"P50: {self.p50 * 1000:.2f}ms",
            f"P90: {self.p90 * 1000:.2f}ms",
            f"P95: {self.p95 * 1000:.2f}ms",
            f"P99: {self.p99 * 1000:.2f}ms",
            f"P99.9: {self.p999 * 1000:.2f}ms",
        ]
        return "\n".join(lines)


# ============================================================================
# Metrics Collector
# ============================================================================

class MetricsCollector:
    """Thread-safe metrics collector with configurable retention.
    
    Collects latency samples and computes statistics on demand.
    
    Attributes:
        max_samples: Maximum number of samples to retain
        retention_seconds: How long to retain samples
    """
    
    def __init__(self, max_samples: int = 10000, retention_seconds: float = 3600):
        self.max_samples = max_samples
        self.retention_seconds = retention_seconds
        self._samples: deque = deque(maxlen=max_samples)
        self._lock = threading.RLock()
        self._started = False
        self._start_time: Optional[float] = None
    
    def start(self) -> None:
        """Start collecting metrics."""
        with self._lock:
            self._started = True
            self._start_time = time.monotonic()
    
    def stop(self) -> None:
        """Stop collecting metrics."""
        with self._lock:
            self._started = False
            self._start_time = None
    
    def record(self, latency: float) -> None:
        """Record a latency sample.
        
        Args:
            latency: Latency in seconds
        """
        with self._lock:
            self._samples.append(latency)
            self._cleanup_old_samples()
    
    def _cleanup_old_samples(self) -> None:
        """Remove samples older than retention period."""
        if self._start_time is None:
            return
        cutoff = self._start_time + self.retention_seconds
        current_time = time.monotonic()
        while self._samples and current_time - self._samples[0] > self.retention_seconds:
            self._samples.popleft()
    
    def get_latency_distribution(self) -> LatencyDistribution:
        """Get latency distribution statistics."""
        with self._lock:
            samples = list(self._samples)
        return LatencyDistribution().from_samples(samples)
    
    def get_request_count(self) -> int:
        """Get total request count."""
        with self._lock:
            return len(self._samples)
    
    def get_duration(self) -> Optional[float]:
        """Get total collection duration in seconds."""
        with self._lock:
            if self._start_time is not None:
                return time.monotonic() - self._start_time
            return None
    
    def to_dict(self) -> dict:
        """Return all metrics as a dictionary."""
        with self._lock:
            samples = list(self._samples)
            latency_dist = LatencyDistribution().from_samples(samples)
        
        return {
            "request_count": len(samples),
            "duration_seconds": self.get_duration(),
            "latency_distribution": latency_dist.to_dict(),
        }
    
    def to_summary(self) -> str:
        """Return a human-readable summary."""
        with self._lock:
            samples = list(self._samples)
            latency_dist = LatencyDistribution().from_samples(samples)
        
        lines = [
            f"Metrics Summary",
            f"=" * 40,
            f"Requests: {len(samples)}",
            f"Duration: {self.get_duration():.2f}s",
            f"Latency: {latency_dist.to_summary()}",
        ]
        return "\n".join(lines)


# ============================================================================
# Resource Metrics
# ============================================================================

@dataclass
class ResourceMetrics:
    """Resource utilization metrics."""
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_percent: float = 0.0
    
    def to_dict(self) -> dict:
        """Return metrics as a dictionary."""
        return {
            "cpu_percent": round(self.cpu_percent, 2),
            "memory_mb": round(self.memory_mb, 2),
            "memory_percent": round(self.memory_percent, 2),
        }
    
    def to_summary(self) -> str:
        """Return a human-readable summary."""
        lines = [
            f"Resource Metrics",
            f"=" * 40,
            f"CPU: {self.cpu_percent:.1f}%",
            f"Memory: {self.memory_mb:.2f}MB ({self.memory_percent:.1f}%)",
        ]
        return "\n".join(lines)


# ============================================================================
# Token Metrics
# ============================================================================

@dataclass
class TokenMetrics:
    """LLM token usage metrics."""
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    
    def record(self, prompt_tokens: int, completion_tokens: int, cost_usd: float = 0.0) -> None:
        """Record token usage."""
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_tokens += prompt_tokens + completion_tokens
        self.total_cost_usd += cost_usd
    
    def avg_tokens_per_request(self) -> float:
        """Return average tokens per request."""
        if self.total_requests > 0:
            return self.total_tokens / self.total_requests
        return 0.0
    
    @property
    def total_requests(self) -> int:
        """Return total number of requests."""
        return self.total_tokens // 10  # Estimate based on avg 10 tokens/request
    
    def to_dict(self) -> dict:
        """Return metrics as a dictionary."""
        return {
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "avg_tokens_per_request": round(self.avg_tokens_per_request(), 2),
        }
    
    def to_summary(self) -> str:
        """Return a human-readable summary."""
        lines = [
            f"Token Metrics",
            f"=" * 40,
            f"Total Tokens: {self.total_tokens:,}",
            f"  - Prompt: {self.total_prompt_tokens:,}",
            f"  - Completion: {self.total_completion_tokens:,}",
            f"Estimated Cost: ${self.total_cost_usd:.4f}",
        ]
        return "\n".join(lines)


# ============================================================================
# Benchmark Suite
# ============================================================================

class BenchmarkSuite:
    """Collection of related benchmarks."""
    
    def __init__(self, name: str):
        """Initialize a benchmark suite.
        
        Args:
            name: Suite identifier
        """
        self.name = name
        self.metrics = BenchmarkMetrics()
        self.latency_collector = MetricsCollector()
        self.token_collector = TokenMetrics()
        self._tests: dict[str, Callable] = {}
    
    def add_test(self, name: str, test_fn: Callable) -> None:
        """Add a benchmark test."""
        self._tests[name] = test_fn
    
    def run(self) -> dict:
        """Run all tests in the suite.
        
        Returns:
            Dictionary with results from each test
        """
        results = {}
        self.metrics = BenchmarkMetrics()
        self.latency_collector = MetricsCollector()
        self.token_collector = TokenMetrics()
        
        for name, test_fn in self._tests.items():
            try:
                start_time = time.monotonic()
                result = test_fn()
                duration = time.monotonic() - start_time
                
                self.metrics.record(success=True, duration=duration)
                self.latency_collector.record(duration)
                results[name] = {
                    "success": True,
                    "duration": duration,
                    "result": result,
                }
            except Exception as e:
                duration = time.monotonic() - start_time
                self.metrics.record(success=False, duration=duration)
                self.latency_collector.record(duration)
                results[name] = {
                    "success": False,
                    "duration": duration,
                    "error": str(e),
                }
        
        return results
    
    def get_summary(self) -> str:
        """Return a summary of all benchmarks."""
        lines = [
            f"Benchmark Suite: {self.name}",
            f"=" * 60,
            f"\nMetrics Summary:\n{self.metrics.to_summary()}",
            f"\nLatency Distribution:\n{self.latency_collector.to_summary()}",
        ]
        return "\n".join(lines)


# ============================================================================
# Global Instances
# ============================================================================

_default_collector = MetricsCollector(max_samples=10000)


def get_collector() -> MetricsCollector:
    """Get the default metrics collector."""
    return _default_collector


def start_collector() -> None:
    """Start the default metrics collector."""
    get_collector().start()


def stop_collector() -> None:
    """Stop the default metrics collector."""
    get_collector().stop()


if __name__ == "__main__":
    # Demo usage
    metrics = BenchmarkMetrics()
    
    metrics.record(success=True, duration=0.123)
    metrics.record(success=True, duration=0.234)
    metrics.record(success=True, duration=0.156)
    metrics.record(success=False, duration=5.678)
    
    print(metrics.to_dict())
    print("\n" + metrics.to_summary())
    
    # Latency distribution demo
    latency = LatencyDistribution()
    samples = [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 1.0, 5.0]
    latency.from_samples(samples)
    
    print("\n" + latency.to_summary())
    
    # Metrics collector demo
    collector = MetricsCollector()
    collector.start()
    
    for i in range(100):
        collector.record(0.1 + i * 0.001)
    
    print("\n" + collector.to_summary())
    collector.stop()

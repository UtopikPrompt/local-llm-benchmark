import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional
import time


@dataclass
class TokenBucket:
    """Token bucket rate limiter."""
    capacity: int
    refill_rate: float  # tokens per second
    tokens: float = field(default_factory=lambda: float(capacity))
    last_update: float = field(default_factory=time.time)
    
    def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens. Returns True if successful."""
        now = time.time()
        
        # Refill tokens
        self.tokens = min(
            float(self.capacity),
            self.tokens + (now - self.last_update) * self.refill_rate
        )
        self.last_update = now
        
        # Check if we have enough tokens
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


class RateLimiter:
    """API rate limiter with per-endpoint buckets."""
    
    def __init__(self, default_burst: int = 100, default_rate: float = 10.0):
        self.default_burst = default_burst
        self.default_rate = default_rate
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = None  # Will be initialized by event loop
    
    def _get_bucket(self, endpoint: str) -> TokenBucket:
        """Get or create rate limit bucket for endpoint."""
        if endpoint not in self._buckets:
            # Custom rate limits can be configured per endpoint
            bucket = TokenBucket(
                capacity=self.default_burst,
                refill_rate=self.default_rate
            )
            self._buckets[endpoint] = bucket
        return self._buckets[endpoint]
    
    async def allow_request(self, endpoint: str = "/api/benchmarks") -> bool:
        """Check if request is allowed. Uses async lock for thread safety."""
        if self._lock is None:
            self._lock = await asyncio.Lock()
        
        async with self._lock:
            bucket = self._get_bucket(endpoint)
            return bucket.acquire()
    
    def reset(self, endpoint: Optional[str] = None):
        """Reset rate limiters. If endpoint is None, resets all."""
        if endpoint:
            self._buckets.pop(endpoint, None)
        else:
            self._buckets.clear()
    
    def get_stats(self, endpoint: str = "/api/benchmarks") -> dict:
        """Get current statistics for an endpoint."""
        bucket = self._get_bucket(endpoint)
        now = time.time()
        
        return {
            "capacity": bucket.capacity,
            "current_tokens": bucket.tokens,
            "refill_rate": bucket.refill_rate,
            "requests_remaining": int(bucket.tokens),
            "requests_allowed_today": self._count_requests(endpoint),
            "uptime_seconds": now - bucket.last_update
        }
    
    def _count_requests(self, endpoint: str) -> int:
        """Count total requests allowed for an endpoint."""
        bucket = self._get_bucket(endpoint)
        return int(bucket.tokens) + int(self.default_burst)

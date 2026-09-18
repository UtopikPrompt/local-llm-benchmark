"""Response caching utilities for the LLM benchmarking system.

Provides LRU cache implementation with TTL support for API responses,
reducing redundant LLM calls and improving latency.
"""

from functools import lru_cache, wraps
from typing import Any, TypeVar, Callable
from datetime import datetime, timedelta
import threading
from dataclasses import dataclass
import httpx
import anyio

from .logger import logger
from .config import Config, HTTPConfig

T = TypeVar('T')


class ResponseCache:
    """LRU cache for API responses with TTL support.
    
    Thread-safe implementation that tracks cache statistics.
    
    Attributes:
        maxsize: Maximum number of entries in the cache
        ttl_seconds: Default time-to-live for cached entries
    """
    
    def __init__(self, maxsize: int = 10000, ttl_seconds: int = 3600):
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'evictions': 0,
            'size': 0
        }
        logger.info("Initializing ResponseCache", extra={"maxsize": maxsize, "ttl_seconds": ttl_seconds})
    
    def get(self, key: str) -> Any | None:
        """Get cached value if not expired.
        
        Args:
            key: Cache key to look up
            
        Returns:
            Cached value if found and not expired, None otherwise
        """
        with self._lock:
            logger.debug("Cache get", extra={"key": key})
            
            if key in self._cache:
                value, expiry = self._cache[key]
                if datetime.now() < expiry:
                    self._stats['hits'] += 1
                    logger.debug("Cache hit", extra={"key": key})
                    return value
                del self._cache[key]
            self._stats['misses'] += 1
            logger.debug("Cache miss", extra={"key": key})
            return None
    
    def set(self, key: str, value: Any, ttl_seconds: int | None = None):
        """Set cache value with optional TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Optional TTL, defaults to instance default
        """
        with self._lock:
            logger.debug("Cache set", extra={"key": key})
            
            expiry = datetime.now() + (ttl_seconds or self.ttl_seconds)
            
            # Evict oldest entries if at capacity
            if len(self._cache) >= self.maxsize:
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]
                self._stats['evictions'] += 1
                logger.debug("Cache eviction", extra={"evicted_key": oldest_key})
            
            self._cache[key] = (value, expiry)
            self._stats['sets'] += 1
            self._stats['size'] = len(self._cache)
    
    def clear(self):
        """Clear all cached entries."""
        with self._lock:
            logger.info("Cache cleared", extra={"size": len(self._cache)})
            self._cache.clear()
            self._stats['hits'] = 0
            self._stats['misses'] = 0
            self._stats['sets'] = 0
            self._stats['evictions'] = 0
    
    def get_stats(self) -> dict:
        """Return cache statistics."""
        with self._lock:
            return self._stats.copy()
    
    def __len__(self) -> int:
        """Return current cache size."""
        with self._lock:
            return len(self._cache)


class CacheDecoratedResponseCache(ResponseCache):
    """ResponseCache enhanced with decorator support."""
    
    def cached(self, key_func: Callable | None = None, ttl_seconds: int = 3600):
        """Decorator for caching function responses.
        
        Args:
            key_func: Optional function to generate cache keys
            ttl_seconds: TTL for cached results
            
        Returns:
            Decorated function
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                # Generate cache key
                if key_func:
                    key = key_func(*args, **kwargs)
                else:
                    key = f"{func.__name__}:{args}:{kwargs}"
                
                # Try cache first
                cached = self.get(key)
                if cached is not None:
                    return cached
                
                # Call function and cache result
                result = func(*args, **kwargs)
                self.set(key, result, ttl_seconds)
                return result
            
            return wrapper
        
        return decorator


class LRUCache:
    """Simple LRU cache implementation using OrderedDict-like behavior.
    
    A drop-in replacement for functools.lru_cache with custom TTL support.
    """
    
    def __init__(self, maxsize: int = 1000, ttl_seconds: int = 3600):
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self._lock = threading.RLock()
        self._order = []  # Track insertion order
    
    def get(self, key: str) -> Any | None:
        """Get and move to front (most recently used) if not expired."""
        with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if datetime.now() < expiry:
                    # Move to front (most recently used)
                    self._order.remove(key)
                    self._order.append(key)
                    return value
                del self._cache[key]
            return None
    
    def set(self, key: str, value: Any, ttl_seconds: int | None = None):
        """Set value and move to front (most recently used)."""
        with self._lock:
            expiry = datetime.now() + (ttl_seconds or self.ttl_seconds)
            
            # Remove existing entry if present
            if key in self._cache:
                del self._cache[key]
            
            # Evict oldest entries if at capacity
            while len(self._cache) >= self.maxsize and self._order:
                oldest_key = self._order.pop(0)
                del self._cache[oldest_key]
            
            # Add new entry
            self._cache[key] = (value, expiry)
            self._order.append(key)
    
    def clear(self):
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            self._order.clear()


def cached_response(
    cache: ResponseCache,
    key_func: Callable | None = None,
    ttl_seconds: int | None = None
) -> Callable:
    """Decorator for caching function responses.
    
    Usage:
        @cached_response(cache=global_cache, ttl_seconds=7200)
        def generate_quality_report(benchmark_id: str) -> dict:
            # Expensive LLM call here
            pass
    
    Args:
        cache: ResponseCache instance
        key_func: Optional function to generate cache keys
        ttl_seconds: Time-to-live for cached responses (can be None to use config default)
    """
    ttl = ttl_seconds or Config().http.cache_ttl_seconds
    
    def decorator(func: Callable) -> Callable:
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
            cache.set(key, result, ttl)
            return result
        
        return wrapper
    
    return decorator


def lru_cache(maxsize: int = 1000, ttl_seconds: int | None = None):
    """Decorator for LRU caching with TTL support.
    
    A drop-in replacement for functools.lru_cache.
    
    Usage:
        @lru_cache(maxsize=100, ttl_seconds=3600)
        def expensive_function(x: int) -> int:
            return x * x
    """
    ttl = ttl_seconds or Config().http.cache_ttl_seconds
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            key = f"{func.__name__}:{args}:{kwargs}"
            
            # Try cache first
            cached = cache.get(key)
            if cached is not None:
                return cached
            
            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(key, result, ttl)
            return result
        
        return wrapper
    
    return decorator


def cache_with_ttl(cache: ResponseCache, ttl_seconds: int | None = None):
    """Context manager for cache operations with automatic cleanup.
    
    Args:
        cache: ResponseCache instance
        ttl_seconds: TTL for cached entries (can be None to use config default)
    """
    ttl = ttl_seconds or Config().http.cache_ttl_seconds
    return cache


# Global cache instance (can be imported and used throughout the application)
_global_cache: ResponseCache | None = None


class TaskGroupManager:
    """Manager for anyio TaskGroup with automatic cleanup.
    
    Provides safe concurrent execution with proper resource cleanup.
    
    Usage:
        async def main():
            async with TaskGroupManager() as manager:
                tasks = [
                    manager.submit(fetch_data(url, "api1")),
                    manager.submit(fetch_data(url, "api2")),
                    manager.submit(fetch_data(url, "api3")),
                ]
                results = await manager.wait(tasks)
    
    Attributes:
        task_group: The underlying anyio TaskGroup
    """
    
    def __init__(self):
        self._task_group: anyio.abc.TaskGroup | None = None
    
    async def __aenter__(self) -> TaskGroupManager:
        """Enter context manager and create task group."""
        self._task_group = anyio.create_task_group()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager and cleanup task group."""
        if self._task_group is not None:
            await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
            self._task_group = None
    
    async def submit(self, coro) -> anyio.abc.Task:
        """Submit a coroutine to the task group."""
        if self._task_group is None:
            raise RuntimeError("TaskGroupManager not entered")
        return await self._task_group.start(coro)
    
    async def wait(self, tasks: list[anyio.abc.Task]) -> list[Any]:
        """Wait for all tasks to complete."""
        if self._task_group is None:
            raise RuntimeError("TaskGroupManager not entered")
        return await anyio.wait(tasks)


class ConnectionPoolManager:
    """Manager for HTTP connection pools with automatic cleanup.
    
    Provides pooled HTTP clients with automatic connection reuse
    and cleanup on exit.
    
    Usage:
        async with ConnectionPoolManager(config) as pool:
            async with pool.client() as client:
                response = await client.get(url)
    
    Args:
        config: HTTP configuration settings
    """
    
    def __init__(self, config: HTTPConfig):
        self.config = config
        self._clients: dict[str, httpx.AsyncClient] = {}
        self._lock = threading.RLock()
    
    async def __aenter__(self) -> ConnectionPoolManager:
        """Enter context manager and initialize clients."""
        await self._ensure_clients()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager and close all clients."""
        await self._close_clients()
    
    async def _ensure_clients(self) -> None:
        """Ensure all HTTP clients are initialized."""
        async with self._lock:
            if not self._clients:
                self._clients = {
                    "default": httpx.AsyncClient(
                        timeout=self.config.timeout,
                        max_connections=self.config.max_connections,
                        keepalive_connections=self.config.keepalive_connections,
                        max_keepalive_connections=self.config.max_connections,
                        keepalive_expiry=60.0
                    )
                }
    
    async def _close_clients(self) -> None:
        """Close all HTTP clients."""
        async with self._lock:
            for client in self._clients.values():
                await client.aclose()
            self._clients.clear()
    
    async def client(self) -> httpx.AsyncClient:
        """Get a client from the pool."""
        return self._clients["default"]


class EngineCache:
    """Cache for engine configurations with automatic cleanup.
    
    Caches engine configurations to avoid repeated initialization.
    
    Usage:
        async with EngineCache() as cache:
            engine_config = await cache.get("llama-3.1-8b")
    
    Attributes:
        cache: LRU cache for engine configurations
    """
    
    def __init__(self, maxsize: int = 100):
        self._cache: dict[str, Any] = {}
        self._lock = threading.RLock()
        self._maxsize = maxsize
        self._order = []  # Track insertion order for LRU
    
    async def __aenter__(self) -> EngineCache:
        """Enter context manager."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager (no cleanup needed for simple cache)."""
        pass
    
    def get(self, key: str) -> Any | None:
        """Get cached configuration."""
        with self._lock:
            if key in self._cache:
                # Move to end (most recently used)
                self._order.remove(key)
                self._order.append(key)
                return self._cache[key]
            return None
    
    def set(self, key: str, value: Any, ttl_seconds: int | None = None):
        """Set configuration in cache."""
        with self._lock:
            expiry = datetime.now() + (ttl_seconds or 3600)
            
            # Remove existing entry if present
            if key in self._cache:
                del self._cache[key]
            
            # Evict oldest entries if at capacity
            while len(self._cache) >= self._maxsize and self._order:
                oldest_key = self._order.pop(0)
                del self._cache[oldest_key]
            
            # Add new entry
            self._cache[key] = (value, expiry)
            self._order.append(key)
    
    def clear(self):
        """Clear all cached configurations."""
        with self._lock:
            self._cache.clear()
            self._order.clear()


# Global cache instance (can be imported and used throughout the application)
_global_cache: ResponseCache | None = None
_global_engine_cache: EngineCache | None = None


def get_global_cache(maxsize: int = 10000, ttl_seconds: int | None = None) -> ResponseCache:
    """Get or create global cache instance.
    
    Uses config values as defaults.
    
    Args:
        maxsize: Maximum cache size
        ttl_seconds: Default TTL for entries (can be None to use config default)
        
    Returns:
        Global cache instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = ResponseCache(maxsize=maxsize, ttl_seconds=ttl_seconds or Config().http.cache_ttl_seconds)
    return _global_cache


def get_global_engine_cache() -> EngineCache:
    """Get or create global engine cache instance.
    
    Returns:
        Global engine cache instance
    """
    global _global_engine_cache
    if _global_engine_cache is None:
        _global_engine_cache = EngineCache(maxsize=100)
    return _global_engine_cache


class HTTPClient:
    """HTTP client wrapper with configurable settings from HTTPConfig.
    
    Provides a context manager for HTTP requests with automatic
    connection pooling and retry logic based on configuration.
    """
    
    def __init__(self, config: HTTPConfig):
        """Initialize HTTP client with configuration.
        
        Args:
            config: HTTP configuration settings
        """
        self.config = config
        self._client: httpx.Client | None = None
        self._httpx_client: httpx.AsyncClient | None = None
    
    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client instance."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.config.timeout,
                max_connections=self.config.max_connections,
                keepalive_connections=self.config.keepalive_connections
            )
        return self._client
    
    def _get_async_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client instance."""
        if self._httpx_client is None:
            self._httpx_client = httpx.AsyncClient(
                timeout=self.config.timeout,
                max_connections=self.config.max_connections,
                keepalive_connections=self.config.keepalive_connections,
                max_keepalive_connections=self.config.max_connections,
                keepalive_expiry=60.0
            )
        return self._httpx_client
    
    def get(self, url: str) -> httpx.Response:
        """Get request with automatic client initialization."""
        return self._get_client().get(url)
    
    def post(self, url: str, **kwargs) -> httpx.Response:
        """Post request with automatic client initialization."""
        return self._get_client().post(url, **kwargs)
    
    def async_get(self, url: str) -> httpx.Response:
        """Get request (async) with automatic client initialization."""
        return self._get_async_client().get(url)
    
    def async_post(self, url: str, **kwargs) -> httpx.Response:
        """Post request (async) with automatic client initialization."""
        return self._get_async_client().post(url, **kwargs)
    
    async def aclose(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None
        if self._httpx_client is not None:
            await self._httpx_client.aclose()
            self._httpx_client = None


def get_http_client(config: HTTPConfig) -> HTTPClient:
    """Get or create HTTP client instance.
    
    Args:
        config: HTTP configuration settings
        
    Returns:
        HTTPClient instance
    """
    return HTTPClient(config)


def clear_global_cache() -> None:
    """Clear the global cache instance."""
    global _global_cache
    if _global_cache:
        _global_cache.clear()


if __name__ == "__main__":
    # Demo and testing
    cache = ResponseCache(maxsize=100, ttl_seconds=3600)
    
    # Test basic operations
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    
    assert cache.get("key1") == "value1"
    assert cache.get("key2") == "value2"
    assert cache.get("key3") is None
    
    # Test stats
    stats = cache.get_stats()
    assert stats["hits"] == 2
    assert stats["misses"] == 1
    assert stats["sets"] == 2
    assert stats["size"] == 2
    
    # Test eviction
    for i in range(105):
        cache.set(f"key{i}", f"value{i}")
    
    assert len(cache) == 100  # Should have evicted 5 entries
    
    # Test stats after eviction
    stats = cache.get_stats()
    assert stats["evictions"] >= 5
    
    print("✓ All cache tests passed!")
    print(f"Cache stats: {stats}")

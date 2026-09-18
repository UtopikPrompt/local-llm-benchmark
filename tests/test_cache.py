"""Tests for the ResponseCache implementation."""

import pytest
from local_llm_benchmark.cache import ResponseCache, LRUCache, cached_response, get_global_cache, clear_global_cache
from datetime import datetime, timedelta
import time


class TestResponseCache:
    """Tests for ResponseCache class."""
    
    def test_basic_set_get(self):
        """Test basic set and get operations."""
        cache = ResponseCache(maxsize=100, ttl_seconds=3600)
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        cache.set("key2", {"nested": "value"})
        assert cache.get("key2") == {"nested": "value"}
    
    def test_get_nonexistent_key(self):
        """Test getting a key that doesn't exist."""
        cache = ResponseCache()
        assert cache.get("nonexistent") is None
    
    def test_ttl_expiration(self):
        """Test that entries expire after TTL."""
        cache = ResponseCache(maxsize=100, ttl_seconds=1)  # 1 second TTL
        
        cache.set("expired_key", "value")
        assert cache.get("expired_key") == "value"
        
        time.sleep(1.1)
        assert cache.get("expired_key") is None
    
    def test_cache_eviction(self):
        """Test cache eviction when at max size."""
        cache = ResponseCache(maxsize=5, ttl_seconds=3600)
        
        # Fill cache
        for i in range(5):
            cache.set(f"key{i}", f"value{i}")
        
        assert len(cache) == 5
        
        # Try to add more
        cache.set("key5", "value5")
        
        assert len(cache) == 5
        assert cache.get("key0") is None  # Should be evicted
        assert cache.get("key4") == "value4"  # Should still exist
    
    def test_cache_statistics(self):
        """Test cache statistics tracking."""
        cache = ResponseCache(maxsize=100, ttl_seconds=3600)
        
        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss
        
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["sets"] == 1
        assert stats["size"] == 1
    
    def test_clear_cache(self):
        """Test clearing cache."""
        cache = ResponseCache(maxsize=100, ttl_seconds=3600)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        assert len(cache) == 2
        
        cache.clear()
        
        assert len(cache) == 0
        assert cache.get("key1") is None
        assert cache.get_stats()["hits"] == 0
    
    def test_cache_key_ordering(self):
        """Test that cache maintains insertion order for eviction."""
        cache = ResponseCache(maxsize=3, ttl_seconds=3600)
        
        for i in range(5):
            cache.set(f"key{i}", f"value{i}")
        
        # Should have evicted key0 and key1
        assert cache.get("key0") is None
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"
    
    def test_different_ttl_per_set(self):
        """Test setting different TTL for individual entries."""
        cache = ResponseCache(maxsize=100, ttl_seconds=3600)
        
        cache.set("short_ttl", "value1", ttl_seconds=1)
        cache.set("long_ttl", "value2", ttl_seconds=10)
        
        time.sleep(1.1)
        
        assert cache.get("short_ttl") is None
        assert cache.get("long_ttl") == "value2"


class TestLRUCache:
    """Tests for LRUCache class."""
    
    def test_lru_ordering(self):
        """Test LRU ordering - accessing moves to front."""
        cache = LRUCache(maxsize=3, ttl_seconds=3600)
        
        cache.set("a", "1")
        cache.set("b", "2")
        cache.set("c", "3")
        
        # Access 'b' - should move to front
        cache.get("b")
        
        # Add 'd' - should evict 'a' (oldest)
        cache.set("d", "4")
        
        assert cache.get("a") is None
        assert cache.get("b") == "2"
        assert cache.get("c") == "3"
        assert cache.get("d") == "4"
    
    def test_cache_size(self):
        """Test cache size property."""
        cache = LRUCache(maxsize=100, ttl_seconds=3600)
        
        assert len(cache) == 0
        
        cache.set("key1", "value1")
        assert len(cache) == 1
        
        cache.set("key2", "value2")
        assert len(cache) == 2


class TestCachedResponseDecorator:
    """Tests for the cached_response decorator."""
    
    def test_decorator_basic(self):
        """Test basic decorator functionality."""
        cache = ResponseCache(maxsize=100, ttl_seconds=3600)
        call_count = [0]
        
        @cached_response(cache=cache, ttl_seconds=3600)
        def expensive_function(x: int) -> int:
            call_count[0] += 1
            return x * x
        
        # First call should execute function
        result1 = expensive_function(5)
        assert result1 == 25
        assert call_count[0] == 1
        
        # Second call should return cached value
        result2 = expensive_function(5)
        assert result2 == 25
        assert call_count[0] == 1  # Function not called again
    
    def test_decorator_different_keys(self):
        """Test decorator with different keys."""
        cache = ResponseCache(maxsize=100, ttl_seconds=3600)
        call_count = [0]
        
        @cached_response(cache=cache, ttl_seconds=3600)
        def process_data(data: str) -> dict:
            call_count[0] += 1
            return {"data": data, "processed": True}
        
        result1 = process_data("hello")
        result2 = process_data("world")
        
        assert result1["data"] == "hello"
        assert result2["data"] == "world"
        assert call_count[0] == 2  # Both executed
    
    def test_decorator_custom_key_func(self):
        """Test decorator with custom key function."""
        cache = ResponseCache(maxsize=100, ttl_seconds=3600)
        call_count = [0]
        
        @cached_response(cache=cache, ttl_seconds=3600, key_func=lambda x, y: f"{x}:{y}")
        def compute(x: int, y: int) -> int:
            call_count[0] += 1
            return x + y
        
        # Same parameters, different order - should cache separately
        result1 = compute(1, 2)
        result2 = compute(2, 1)
        
        assert result1 == 3
        assert result2 == 3
        assert call_count[0] == 2  # Both executed
        
        # Same parameters again - should be cached
        result3 = compute(1, 2)
        assert result3 == 3
        assert call_count[0] == 3  # Third call, still cached
    
    def test_decorator_args_kwargs(self):
        """Test decorator with args and kwargs."""
        cache = ResponseCache(maxsize=100, ttl_seconds=3600)
        call_count = [0]
        
        @cached_response(cache=cache, ttl_seconds=3600)
        def process(*args, **kwargs) -> dict:
            call_count[0] += 1
            return {"args": args, "kwargs": kwargs}
        
        result1 = process(1, 2, a=3, b=4)
        result2 = process(1, 2, a=3, b=4)
        
        assert result1 == result2
        assert call_count[0] == 1


class TestGlobalCache:
    """Tests for global cache utilities."""
    
    def test_get_global_cache(self):
        """Test getting global cache instance."""
        cache1 = get_global_cache(maxsize=100, ttl_seconds=3600)
        cache2 = get_global_cache(maxsize=100, ttl_seconds=3600)
        
        assert cache1 is cache2
        assert len(cache1) == 0
        assert len(cache2) == 0
    
    def test_clear_global_cache(self):
        """Test clearing global cache."""
        get_global_cache(maxsize=100, ttl_seconds=3600).set("key", "value")
        
        assert get_global_cache().get("key") == "value"
        
        clear_global_cache()
        
        assert get_global_cache().get("key") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

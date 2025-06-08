"""
Tests for cache module
"""

import pytest
import asyncio
import time
import json
from unittest.mock import Mock, patch
import sys

from core.cache import (
    CacheBackend, InMemoryCache, CacheKeyBuilder, 
    QueryResultCache, cache_result, get_cache, initialize_cache
)


class TestInMemoryCache:
    """Test in-memory cache implementation"""
    
    @pytest.fixture
    async def cache(self):
        """Create test cache"""
        cache = InMemoryCache(max_size=10, max_memory_mb=1)
        yield cache
        # No cleanup needed for in-memory cache
    
    @pytest.mark.asyncio
    async def test_basic_set_get(self, cache):
        """Test basic set and get operations"""
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"
        
        # Non-existent key
        result = await cache.get("nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_ttl_expiration(self, cache):
        """Test TTL expiration"""
        await cache.set("key1", "value1", ttl=1)
        
        # Should exist immediately
        assert await cache.get("key1") == "value1"
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should be expired
        assert await cache.get("key1") is None
    
    @pytest.mark.asyncio
    async def test_delete(self, cache):
        """Test delete operation"""
        await cache.set("key1", "value1")
        assert await cache.get("key1") == "value1"
        
        await cache.delete("key1")
        assert await cache.get("key1") is None
        
        # Delete non-existent key should not error
        await cache.delete("nonexistent")
    
    @pytest.mark.asyncio
    async def test_clear(self, cache):
        """Test clear operation"""
        # Add multiple items
        for i in range(5):
            await cache.set(f"key{i}", f"value{i}")
        
        # Verify they exist
        assert await cache.get("key0") == "value0"
        assert await cache.get("key4") == "value4"
        
        # Clear cache
        await cache.clear()
        
        # All should be gone
        for i in range(5):
            assert await cache.get(f"key{i}") is None
    
    @pytest.mark.asyncio
    async def test_exists(self, cache):
        """Test exists operation"""
        await cache.set("key1", "value1")
        
        assert await cache.exists("key1") is True
        assert await cache.exists("nonexistent") is False
        
        # Expired key should not exist
        await cache.set("key2", "value2", ttl=1)
        await asyncio.sleep(1.1)
        assert await cache.exists("key2") is False
    
    @pytest.mark.asyncio
    async def test_lru_eviction(self, cache):
        """Test LRU eviction when cache is full"""
        cache = InMemoryCache(max_size=3, max_memory_mb=100)
        
        # Fill cache
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        
        # Access key1 to make it recently used
        await cache.get("key1")
        
        # Add new item, should evict key2 (least recently used)
        await cache.set("key4", "value4")
        
        assert await cache.get("key1") == "value1"  # Still there
        assert await cache.get("key2") is None      # Evicted
        assert await cache.get("key3") == "value3"  # Still there
        assert await cache.get("key4") == "value4"  # New item
    
    @pytest.mark.asyncio
    async def test_memory_limit(self, cache):
        """Test memory limit enforcement"""
        # Create cache with very small memory limit
        cache = InMemoryCache(max_size=1000, max_memory_mb=0.001)  # 1KB
        
        # Try to add large item
        large_value = "x" * 10000  # 10KB
        await cache.set("large", large_value)
        
        # Should not be stored due to memory limit
        # (or cache should evict items to make room)
        stats = cache.get_stats()
        assert stats["memory_usage_mb"] < 0.01  # Less than 10KB
    
    @pytest.mark.asyncio
    async def test_get_stats(self, cache):
        """Test cache statistics"""
        # Initial stats
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["items"] == 0
        
        # Add items and access them
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        
        await cache.get("key1")  # Hit
        await cache.get("key1")  # Hit
        await cache.get("nonexistent")  # Miss
        
        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["items"] == 2
        assert stats["hit_rate"] == 2/3
        assert stats["memory_usage_mb"] > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_access(self, cache):
        """Test concurrent access to cache"""
        async def writer(n):
            for i in range(10):
                await cache.set(f"key{n}_{i}", f"value{n}_{i}")
                await asyncio.sleep(0.001)
        
        async def reader(n):
            for i in range(10):
                await cache.get(f"key{n}_{i}")
                await asyncio.sleep(0.001)
        
        # Run concurrent writers and readers
        tasks = []
        for i in range(5):
            tasks.append(writer(i))
            tasks.append(reader(i))
        
        await asyncio.gather(*tasks)
        
        # Cache should still be consistent
        stats = cache.get_stats()
        assert stats["items"] <= cache.max_size


class TestCacheKeyBuilder:
    """Test cache key building"""
    
    def test_simple_key_building(self):
        """Test simple key building"""
        key = CacheKeyBuilder.build("prefix", "arg1", "arg2")
        assert key == "prefix:arg1:arg2"
    
    def test_complex_key_building(self):
        """Test key building with complex types"""
        key = CacheKeyBuilder.build(
            "query",
            account_id=123456,
            time_range="1 hour",
            filters={"app": "test", "env": "prod"}
        )
        
        # Should create deterministic key
        assert "query:" in key
        assert "account_id:123456" in key
        assert "time_range:1 hour" in key
        
        # Filters should be sorted for consistency
        assert "filters:" in key
    
    def test_key_consistency(self):
        """Test that same inputs produce same key"""
        key1 = CacheKeyBuilder.build(
            "test",
            filters={"b": 2, "a": 1},
            options={"x": "y", "p": "q"}
        )
        
        key2 = CacheKeyBuilder.build(
            "test",
            options={"p": "q", "x": "y"},  # Different order
            filters={"a": 1, "b": 2}        # Different order
        )
        
        assert key1 == key2
    
    def test_hash_long_values(self):
        """Test hashing of long values"""
        long_string = "x" * 1000
        key = CacheKeyBuilder.build("test", query=long_string)
        
        # Key should be reasonable length
        assert len(key) < 200
        assert "test:" in key
    
    def test_none_values(self):
        """Test handling of None values"""
        key = CacheKeyBuilder.build("test", a=None, b="value", c=None)
        
        # None values should be handled
        assert "b:value" in key


class TestQueryResultCache:
    """Test query result cache"""
    
    @pytest.fixture
    async def query_cache(self):
        """Create test query cache"""
        backend = InMemoryCache()
        cache = QueryResultCache(backend)
        yield cache
    
    @pytest.mark.asyncio
    async def test_cache_nerdgraph_query(self, query_cache):
        """Test caching NerdGraph queries"""
        query = "{ actor { user { email } } }"
        variables = {"accountId": 123456}
        result = {"actor": {"user": {"email": "test@example.com"}}}
        
        # Cache the result
        await query_cache.cache_query_result("nerdgraph", query, result, variables)
        
        # Retrieve from cache
        cached = await query_cache.get_cached_result("nerdgraph", query, variables)
        assert cached == result
        
        # Different variables should not match
        cached = await query_cache.get_cached_result("nerdgraph", query, {"accountId": 789})
        assert cached is None
    
    @pytest.mark.asyncio
    async def test_cache_nrql_query(self, query_cache):
        """Test caching NRQL queries"""
        nrql = "SELECT count(*) FROM Transaction SINCE 1 hour ago"
        account_id = 123456
        result = {"results": [{"count": 1000}]}
        
        # Cache the result
        await query_cache.cache_query_result("nrql", nrql, result, account_id=account_id)
        
        # Retrieve from cache
        cached = await query_cache.get_cached_result("nrql", nrql, account_id=account_id)
        assert cached == result
    
    @pytest.mark.asyncio
    async def test_cache_ttl(self, query_cache):
        """Test cache TTL for query results"""
        query = "{ test }"
        result = {"test": "data"}
        
        # Cache with short TTL
        await query_cache.cache_query_result("test", query, result, ttl=1)
        
        # Should exist immediately
        cached = await query_cache.get_cached_result("test", query)
        assert cached == result
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should be expired
        cached = await query_cache.get_cached_result("test", query)
        assert cached is None


class TestCacheDecorator:
    """Test cache decorator"""
    
    @pytest.mark.asyncio
    async def test_cache_decorator(self):
        """Test caching decorator for async functions"""
        call_count = 0
        
        @cache_result(ttl=60)
        async def expensive_function(x, y):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)  # Simulate expensive operation
            return x + y
        
        # First call should execute function
        result1 = await expensive_function(1, 2)
        assert result1 == 3
        assert call_count == 1
        
        # Second call should use cache
        result2 = await expensive_function(1, 2)
        assert result2 == 3
        assert call_count == 1  # Not incremented
        
        # Different arguments should execute function
        result3 = await expensive_function(2, 3)
        assert result3 == 5
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_cache_decorator_key_func(self):
        """Test cache decorator with custom key function"""
        call_count = 0
        
        def custom_key(x, y, z=None):
            # Only use x and y for cache key, ignore z
            return f"sum:{x}:{y}"
        
        @cache_result(key_func=custom_key)
        async def my_function(x, y, z=None):
            nonlocal call_count
            call_count += 1
            return x + y + (z or 0)
        
        # These should use same cache entry
        result1 = await my_function(1, 2, z=3)
        result2 = await my_function(1, 2, z=5)
        
        assert result1 == 6  # 1 + 2 + 3
        assert result2 == 6  # Cached result, ignores z=5
        assert call_count == 1


class TestCacheInitialization:
    """Test cache initialization and global access"""
    
    def test_initialize_cache(self):
        """Test cache initialization"""
        # Reset global cache
        import core.cache
        core.cache._cache = None
        
        # Initialize with defaults
        cache = initialize_cache()
        assert cache is not None
        assert isinstance(cache, CacheBackend)
        
        # Get cache should return same instance
        cache2 = get_cache()
        assert cache2 is cache
    
    def test_initialize_cache_with_params(self):
        """Test cache initialization with parameters"""
        import core.cache
        core.cache._cache = None
        
        cache = initialize_cache(
            backend="memory",
            max_size=500,
            max_memory_mb=50
        )
        
        assert isinstance(cache, InMemoryCache)
        assert cache.max_size == 500
        
    @patch.dict('os.environ', {
        'CACHE_BACKEND': 'memory',
        'CACHE_MAX_SIZE': '200',
        'CACHE_MAX_MEMORY_MB': '20'
    })
    def test_initialize_cache_from_env(self):
        """Test cache initialization from environment"""
        import core.cache
        core.cache._cache = None
        
        cache = initialize_cache()
        
        assert isinstance(cache, InMemoryCache)
        assert cache.max_size == 200
"""
Tests for improved cache implementation
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch
import threading

from core.cache_improved import (
    MemoryLimitedCache, DistributedCache, create_cache
)
from core.errors import CacheError


class TestMemoryLimitedCache:
    """Test memory-limited cache implementation"""
    
    @pytest.mark.asyncio
    async def test_basic_get_set(self):
        """Test basic get/set operations"""
        cache = MemoryLimitedCache(max_items=10)
        
        # Test set and get
        await cache.set("key1", "value1")
        assert await cache.get("key1") == "value1"
        
        # Test missing key
        assert await cache.get("missing") is None
        
        # Test overwrite
        await cache.set("key1", "value2")
        assert await cache.get("key1") == "value2"
    
    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        """Test TTL expiration"""
        cache = MemoryLimitedCache(default_ttl=1)
        
        await cache.set("key1", "value1", ttl=1)
        assert await cache.get("key1") == "value1"
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        assert await cache.get("key1") is None
    
    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        """Test LRU eviction policy"""
        cache = MemoryLimitedCache(max_items=3)
        
        # Fill cache
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        
        # Access key1 to make it recently used
        await cache.get("key1")
        
        # Add new item - should evict key2 (least recently used)
        await cache.set("key4", "value4")
        
        assert await cache.get("key1") == "value1"  # Still there
        assert await cache.get("key2") is None      # Evicted
        assert await cache.get("key3") == "value3"  # Still there
        assert await cache.get("key4") == "value4"  # New item
    
    @pytest.mark.asyncio
    async def test_memory_limit(self):
        """Test memory limit enforcement"""
        # Create cache with 1KB limit
        cache = MemoryLimitedCache(max_items=1000, max_memory_mb=0.001)
        
        # Add items until memory limit
        large_value = "x" * 100  # ~100 bytes
        
        for i in range(20):
            await cache.set(f"key{i}", large_value)
        
        # Check that some items were evicted
        stats = cache.get_stats()
        assert stats['evictions'] > 0
        assert stats['memory_mb'] <= 0.001
    
    @pytest.mark.asyncio
    async def test_value_too_large(self):
        """Test rejection of values that exceed memory limit"""
        cache = MemoryLimitedCache(max_memory_mb=0.001)  # 1KB limit
        
        # Try to add value larger than limit
        huge_value = "x" * 10000  # ~10KB
        
        with pytest.raises(CacheError, match="Value too large"):
            await cache.set("huge", huge_value)
    
    @pytest.mark.asyncio
    async def test_delete_operation(self):
        """Test delete operation"""
        cache = MemoryLimitedCache()
        
        await cache.set("key1", "value1")
        assert await cache.delete("key1") is True
        assert await cache.get("key1") is None
        
        # Delete non-existent key
        assert await cache.delete("missing") is False
    
    @pytest.mark.asyncio
    async def test_clear_operation(self):
        """Test clear operation"""
        cache = MemoryLimitedCache()
        
        # Add multiple items
        for i in range(5):
            await cache.set(f"key{i}", f"value{i}")
        
        # Clear cache
        await cache.clear()
        
        # Verify all items are gone
        for i in range(5):
            assert await cache.get(f"key{i}") is None
        
        stats = cache.get_stats()
        assert stats['items'] == 0
        assert stats['memory_bytes'] == 0
    
    @pytest.mark.asyncio
    async def test_cache_stats(self):
        """Test cache statistics"""
        cache = MemoryLimitedCache()
        
        # Generate some activity
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        
        # Hits
        await cache.get("key1")
        await cache.get("key2")
        
        # Misses
        await cache.get("missing1")
        await cache.get("missing2")
        await cache.get("missing3")
        
        stats = cache.get_stats()
        assert stats['hits'] == 2
        assert stats['misses'] == 3
        assert stats['hit_rate'] == 2/5
        assert stats['items'] == 2
    
    @pytest.mark.asyncio
    async def test_cleanup_expired(self):
        """Test cleanup of expired entries"""
        cache = MemoryLimitedCache()
        
        # Add items with different TTLs
        await cache.set("expire1", "value1", ttl=1)
        await cache.set("expire2", "value2", ttl=1)
        await cache.set("keep", "value3", ttl=10)
        
        # Wait for some to expire
        await asyncio.sleep(1.1)
        
        # Run cleanup
        removed = await cache.cleanup_expired()
        assert removed == 2
        
        # Verify correct items remain
        assert await cache.get("expire1") is None
        assert await cache.get("expire2") is None
        assert await cache.get("keep") == "value3"
    
    @pytest.mark.asyncio
    async def test_thread_safety(self):
        """Test thread-safe concurrent access"""
        cache = MemoryLimitedCache(max_items=100)
        errors = []
        
        async def writer(thread_id: int):
            """Write values from a thread"""
            try:
                for i in range(50):
                    await cache.set(f"thread{thread_id}_key{i}", f"value{i}")
            except Exception as e:
                errors.append(e)
        
        async def reader(thread_id: int):
            """Read values from a thread"""
            try:
                for i in range(50):
                    await cache.get(f"thread{thread_id}_key{i}")
            except Exception as e:
                errors.append(e)
        
        # Run concurrent operations
        tasks = []
        for i in range(5):
            tasks.append(writer(i))
            tasks.append(reader(i))
        
        await asyncio.gather(*tasks)
        
        # Check no errors occurred
        assert len(errors) == 0
        
        # Verify cache state is consistent
        stats = cache.get_stats()
        assert stats['items'] <= 100  # Respects max items


class TestDistributedCache:
    """Test distributed cache implementation"""
    
    @pytest.mark.asyncio
    async def test_fallback_to_memory(self):
        """Test fallback to memory cache when Redis unavailable"""
        cache = DistributedCache()
        
        # Should work even without Redis
        await cache.set("key1", "value1")
        assert await cache.get("key1") == "value1"
        
        await cache.delete("key1")
        assert await cache.get("key1") is None


class TestCacheFactory:
    """Test cache factory function"""
    
    def test_create_memory_cache(self):
        """Test creating memory cache"""
        cache = create_cache(
            backend="memory",
            max_items=500,
            max_memory_mb=50,
            ttl_seconds=600
        )
        
        assert isinstance(cache, MemoryLimitedCache)
        assert cache.max_items == 500
        assert cache.default_ttl == 600
    
    def test_create_redis_cache(self):
        """Test creating Redis cache"""
        cache = create_cache(
            backend="redis",
            redis_url="redis://localhost:6379"
        )
        
        assert isinstance(cache, DistributedCache)
        assert cache.redis_url == "redis://localhost:6379"
    
    def test_invalid_backend(self):
        """Test invalid backend raises error"""
        with pytest.raises(ValueError, match="Unknown cache backend"):
            create_cache(backend="invalid")
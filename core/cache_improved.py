"""
Improved cache implementation with size limits and thread safety

This module provides a production-ready cache with:
- LRU eviction policy
- Memory usage tracking
- Thread safety
- Metrics collection
"""

import asyncio
import json
import time
import sys
import threading
from typing import Any, Dict, Optional, Union, List, Tuple
from collections import OrderedDict
import hashlib
import pickle

from .errors import CacheError


class MemoryLimitedCache:
    """Thread-safe cache with memory limits and LRU eviction"""
    
    def __init__(
        self,
        max_items: int = 1000,
        max_memory_mb: int = 100,
        ttl_seconds: int = 300
    ):
        """
        Initialize cache with limits
        
        Args:
            max_items: Maximum number of items
            max_memory_mb: Maximum memory usage in MB
            ttl_seconds: Default TTL for items
        """
        self.max_items = max_items
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.default_ttl = ttl_seconds
        
        # Thread-safe cache storage
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._lock = threading.RLock()
        
        # Metrics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._current_memory = 0
        
    def _estimate_size(self, value: Any) -> int:
        """Estimate memory size of a value"""
        try:
            return sys.getsizeof(pickle.dumps(value))
        except:
            # Fallback for non-picklable objects
            return sys.getsizeof(str(value))
    
    def _evict_lru(self) -> None:
        """Evict least recently used items"""
        with self._lock:
            while self._cache and (
                len(self._cache) > self.max_items or 
                self._current_memory > self.max_memory_bytes
            ):
                key, item = self._cache.popitem(last=False)
                self._current_memory -= item['size']
                self._evictions += 1
    
    def _is_expired(self, item: Dict[str, Any]) -> bool:
        """Check if item has expired"""
        if item['ttl'] is None:
            return False
        return time.time() > item['expires_at']
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        with self._lock:
            item = self._cache.get(key)
            
            if item is None:
                self._misses += 1
                return None
            
            # Check expiration
            if self._is_expired(item):
                del self._cache[key]
                self._current_memory -= item['size']
                self._misses += 1
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            
            return item['value']
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        ttl = ttl or self.default_ttl
        size = self._estimate_size(value)
        
        with self._lock:
            # Remove old value if exists
            if key in self._cache:
                old_item = self._cache[key]
                self._current_memory -= old_item['size']
                del self._cache[key]
            
            # Check if value is too large
            if size > self.max_memory_bytes:
                raise CacheError(f"Value too large ({size} bytes)")
            
            # Evict if necessary
            self._current_memory += size
            self._evict_lru()
            
            # Store new value
            self._cache[key] = {
                'value': value,
                'size': size,
                'ttl': ttl,
                'expires_at': time.time() + ttl if ttl else None,
                'created_at': time.time()
            }
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
    
    async def delete(self, key: str) -> bool:
        """
        Delete value from cache
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            item = self._cache.get(key)
            if item:
                del self._cache[key]
                self._current_memory -= item['size']
                return True
            return False
    
    async def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._current_memory = 0
            self._evictions += len(self._cache)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0
            
            return {
                'items': len(self._cache),
                'memory_bytes': self._current_memory,
                'memory_mb': self._current_memory / (1024 * 1024),
                'hits': self._hits,
                'misses': self._misses,
                'evictions': self._evictions,
                'hit_rate': hit_rate,
                'max_items': self.max_items,
                'max_memory_mb': self.max_memory_bytes / (1024 * 1024)
            }
    
    async def cleanup_expired(self) -> int:
        """
        Remove expired entries
        
        Returns:
            Number of entries removed
        """
        removed = 0
        with self._lock:
            expired_keys = []
            for key, item in self._cache.items():
                if self._is_expired(item):
                    expired_keys.append(key)
            
            for key in expired_keys:
                item = self._cache[key]
                del self._cache[key]
                self._current_memory -= item['size']
                removed += 1
        
        return removed


class DistributedCache:
    """
    Distributed cache implementation (Redis-backed)
    
    This is a placeholder for future Redis integration
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """Initialize distributed cache"""
        self.redis_url = redis_url
        # TODO: Implement Redis connection
        # For now, fall back to memory cache
        self._fallback = MemoryLimitedCache()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get from distributed cache"""
        # TODO: Implement Redis get
        return await self._fallback.get(key)
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """Set in distributed cache"""
        # TODO: Implement Redis set
        await self._fallback.set(key, value, ttl)
    
    async def delete(self, key: str) -> bool:
        """Delete from distributed cache"""
        # TODO: Implement Redis delete
        return await self._fallback.delete(key)
    
    async def clear(self) -> None:
        """Clear distributed cache"""
        # TODO: Implement Redis clear
        await self._fallback.clear()


def create_cache(
    backend: str = "memory",
    **kwargs
) -> Union[MemoryLimitedCache, DistributedCache]:
    """
    Factory function to create cache instance
    
    Args:
        backend: Cache backend ("memory" or "redis")
        **kwargs: Backend-specific arguments
        
    Returns:
        Cache instance
    """
    if backend == "memory":
        return MemoryLimitedCache(
            max_items=kwargs.get('max_items', 1000),
            max_memory_mb=kwargs.get('max_memory_mb', 100),
            ttl_seconds=kwargs.get('ttl_seconds', 300)
        )
    elif backend == "redis":
        return DistributedCache(
            redis_url=kwargs.get('redis_url', 'redis://localhost:6379')
        )
    else:
        raise ValueError(f"Unknown cache backend: {backend}")


# Example usage and migration guide
"""
Migration from old cache to new cache:

Old code:
```python
from core.cache import get_cache
cache = get_cache()
await cache.set("key", "value")
```

New code:
```python
from core.cache_improved import create_cache
cache = create_cache(
    backend="memory",
    max_items=1000,
    max_memory_mb=100
)
await cache.set("key", "value", ttl=300)
```

The new cache provides:
1. Memory limits to prevent OOM
2. Thread safety for concurrent access
3. LRU eviction policy
4. Metrics for monitoring
5. Automatic expired item cleanup
"""
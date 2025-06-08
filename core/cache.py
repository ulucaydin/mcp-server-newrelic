"""
Caching system for the MCP server
"""

import asyncio
import time
import hashlib
import json
import pickle
from typing import Any, Optional, Dict, Callable, Union, TypeVar, Generic
from datetime import datetime, timedelta
from collections import OrderedDict
import logging
from functools import wraps
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CacheEntry(Generic[T]):
    """Represents a cached value with metadata"""
    
    def __init__(self, value: T, ttl: int, size: Optional[int] = None):
        """
        Initialize cache entry
        
        Args:
            value: The cached value
            ttl: Time to live in seconds
            size: Size of the entry in bytes (for memory management)
        """
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl
        self.size = size or self._estimate_size(value)
        self.hits = 0
        self.last_accessed = self.created_at
    
    def is_expired(self) -> bool:
        """Check if the entry has expired"""
        return time.time() - self.created_at > self.ttl
    
    def access(self) -> T:
        """Access the cached value and update stats"""
        self.hits += 1
        self.last_accessed = time.time()
        return self.value
    
    def _estimate_size(self, value: Any) -> int:
        """Estimate size of value in bytes"""
        try:
            return len(pickle.dumps(value))
        except:
            # Fallback for non-pickleable objects
            return len(str(value))


class CacheBackend(ABC):
    """Abstract base class for cache backends"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set value in cache"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete value from cache"""
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache entries"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        pass


class InMemoryCache(CacheBackend):
    """In-memory LRU cache implementation"""
    
    def __init__(self, max_size: int = 1000, max_memory_mb: int = 100):
        """
        Initialize in-memory cache
        
        Args:
            max_size: Maximum number of entries
            max_memory_mb: Maximum memory usage in MB
        """
        self.max_size = max_size
        self.max_memory = max_memory_mb * 1024 * 1024  # Convert to bytes
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()
        self._total_memory = 0
        
        # Stats
        self.hits = 0
        self.misses = 0
        self.evictions = 0
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        async with self._lock:
            if key not in self._cache:
                self.misses += 1
                return None
            
            entry = self._cache[key]
            
            if entry.is_expired():
                await self._delete_entry(key)
                self.misses += 1
                return None
            
            # Move to end (LRU)
            self._cache.move_to_end(key)
            self.hits += 1
            
            return entry.access()
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set value in cache"""
        async with self._lock:
            # Remove existing entry if present
            if key in self._cache:
                await self._delete_entry(key)
            
            entry = CacheEntry(value, ttl)
            
            # Check memory limit
            while self._total_memory + entry.size > self.max_memory and self._cache:
                await self._evict_lru()
            
            # Check size limit
            while len(self._cache) >= self.max_size:
                await self._evict_lru()
            
            self._cache[key] = entry
            self._total_memory += entry.size
    
    async def delete(self, key: str) -> None:
        """Delete value from cache"""
        async with self._lock:
            await self._delete_entry(key)
    
    async def clear(self) -> None:
        """Clear all cache entries"""
        async with self._lock:
            self._cache.clear()
            self._total_memory = 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        async with self._lock:
            if key not in self._cache:
                return False
            
            entry = self._cache[key]
            if entry.is_expired():
                await self._delete_entry(key)
                return False
            
            return True
    
    async def _delete_entry(self, key: str) -> None:
        """Delete entry and update memory counter"""
        if key in self._cache:
            entry = self._cache[key]
            self._total_memory -= entry.size
            del self._cache[key]
    
    async def _evict_lru(self) -> None:
        """Evict least recently used entry"""
        if self._cache:
            key = next(iter(self._cache))
            await self._delete_entry(key)
            self.evictions += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0
        
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": hit_rate,
            "size": len(self._cache),
            "memory_mb": self._total_memory / (1024 * 1024),
            "max_size": self.max_size,
            "max_memory_mb": self.max_memory / (1024 * 1024)
        }


class MultiTierCache(CacheBackend):
    """Multi-tier cache with L1 (memory) and L2 (external) caches"""
    
    def __init__(self, l1_cache: CacheBackend, l2_cache: Optional[CacheBackend] = None):
        """
        Initialize multi-tier cache
        
        Args:
            l1_cache: Level 1 (fast) cache
            l2_cache: Level 2 (slower but larger) cache
        """
        self.l1 = l1_cache
        self.l2 = l2_cache
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache, checking L1 then L2"""
        # Try L1 first
        value = await self.l1.get(key)
        if value is not None:
            return value
        
        # Try L2 if available
        if self.l2:
            value = await self.l2.get(key)
            if value is not None:
                # Promote to L1
                await self.l1.set(key, value)
                return value
        
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set value in both cache tiers"""
        await self.l1.set(key, value, ttl)
        if self.l2:
            await self.l2.set(key, value, ttl)
    
    async def delete(self, key: str) -> None:
        """Delete from both tiers"""
        await self.l1.delete(key)
        if self.l2:
            await self.l2.delete(key)
    
    async def clear(self) -> None:
        """Clear both tiers"""
        await self.l1.clear()
        if self.l2:
            await self.l2.clear()
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in either tier"""
        if await self.l1.exists(key):
            return True
        if self.l2:
            return await self.l2.exists(key)
        return False


class CacheKeyBuilder:
    """Utility for building consistent cache keys"""
    
    @staticmethod
    def build(prefix: str, *args, **kwargs) -> str:
        """
        Build a cache key from prefix and parameters
        
        Args:
            prefix: Key prefix (e.g., "nrql_query")
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Cache key string
        """
        parts = [prefix]
        
        # Add positional args
        for arg in args:
            parts.append(str(arg))
        
        # Add sorted kwargs for consistency
        for key in sorted(kwargs.keys()):
            parts.append(f"{key}={kwargs[key]}")
        
        # Create a hash for long keys
        key = ":".join(parts)
        if len(key) > 250:  # Max key length
            key_hash = hashlib.md5(key.encode()).hexdigest()
            return f"{prefix}:{key_hash}"
        
        return key


def cached(
    ttl: int = 300,
    prefix: Optional[str] = None,
    key_builder: Optional[Callable] = None,
    cache: Optional[CacheBackend] = None
):
    """
    Decorator for caching function results
    
    Args:
        ttl: Time to live in seconds
        prefix: Cache key prefix (defaults to function name)
        key_builder: Custom key builder function
        cache: Cache backend to use (defaults to global cache)
    
    Usage:
        @cached(ttl=600)
        async def expensive_operation(param: str) -> dict:
            # Do expensive work
            return result
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get cache instance
            cache_instance = cache or _global_cache
            if not cache_instance:
                # No cache available, call function directly
                return await func(*args, **kwargs)
            
            # Build cache key
            key_prefix = prefix or func.__name__
            
            if key_builder:
                cache_key = key_builder(key_prefix, *args, **kwargs)
            else:
                # Skip 'self' for instance methods
                cache_args = args[1:] if args and hasattr(args[0], '__class__') else args
                cache_key = CacheKeyBuilder.build(key_prefix, *cache_args, **kwargs)
            
            # Try to get from cache
            cached_value = await cache_instance.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {key_prefix}: {cache_key}")
                return cached_value
            
            # Call function and cache result
            logger.debug(f"Cache miss for {key_prefix}: {cache_key}")
            result = await func(*args, **kwargs)
            
            # Only cache non-error results
            if not (isinstance(result, dict) and "error" in result):
                await cache_instance.set(cache_key, result, ttl)
            
            return result
        
        # Add cache control methods
        wrapper.invalidate = lambda *args, **kwargs: _invalidate_cache(
            cache or _global_cache, prefix or func.__name__, *args, **kwargs
        )
        
        return wrapper
    
    return decorator


# Backwards compatibility
cache_result = cached


async def _invalidate_cache(cache: CacheBackend, prefix: str, *args, **kwargs):
    """Invalidate cached entries for specific arguments"""
    if not cache:
        return
    
    cache_key = CacheKeyBuilder.build(prefix, *args, **kwargs)
    await cache.delete(cache_key)


class QueryResultCache:
    """Specialized cache for NRQL query results"""
    
    def __init__(self, cache: CacheBackend):
        self.cache = cache
    
    async def get_query_result(
        self, 
        query: str, 
        account_id: int,
        time_range: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get cached query result"""
        # Normalize query for caching
        normalized_query = self._normalize_query(query)
        
        key = CacheKeyBuilder.build(
            "nrql",
            account_id=account_id,
            query_hash=hashlib.md5(normalized_query.encode()).hexdigest(),
            time_range=time_range
        )
        
        return await self.cache.get(key)
    
    async def set_query_result(
        self,
        query: str,
        account_id: int,
        result: Dict[str, Any],
        time_range: Optional[str] = None,
        ttl: int = 300
    ):
        """Cache query result"""
        normalized_query = self._normalize_query(query)
        
        key = CacheKeyBuilder.build(
            "nrql",
            account_id=account_id,
            query_hash=hashlib.md5(normalized_query.encode()).hexdigest(),
            time_range=time_range
        )
        
        await self.cache.set(key, result, ttl)
    
    def _normalize_query(self, query: str) -> str:
        """Normalize NRQL query for consistent caching"""
        # Remove extra whitespace
        query = " ".join(query.split())
        # Convert to uppercase for consistency
        return query.upper()


# Global cache instance
_global_cache: Optional[CacheBackend] = None


def initialize_cache(
    backend: str = "memory",
    **kwargs
) -> CacheBackend:
    """
    Initialize the global cache
    
    Args:
        backend: Cache backend type ("memory", "redis", etc.)
        **kwargs: Backend-specific configuration
        
    Returns:
        Initialized cache backend
    """
    global _global_cache
    
    if backend == "memory":
        _global_cache = InMemoryCache(**kwargs)
    else:
        raise ValueError(f"Unknown cache backend: {backend}")
    
    logger.info(f"Initialized {backend} cache")
    return _global_cache


def get_cache() -> Optional[CacheBackend]:
    """Get the global cache instance"""
    return _global_cache
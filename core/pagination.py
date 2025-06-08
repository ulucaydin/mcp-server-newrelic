"""
Pagination utilities for handling large result sets
"""

from typing import Any, Dict, List, Optional, AsyncIterator, TypeVar, Generic
from dataclasses import dataclass
import math
import hashlib
import json
import asyncio
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class Page(Generic[T]):
    """Represents a page of results"""
    items: List[T]
    total_count: int
    page_number: int
    page_size: int
    has_next: bool
    has_previous: bool
    cursor: Optional[str] = None
    
    @property
    def total_pages(self) -> int:
        """Calculate total number of pages"""
        return math.ceil(self.total_count / self.page_size) if self.page_size > 0 else 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "items": self.items,
            "pagination": {
                "total_count": self.total_count,
                "page_number": self.page_number,
                "page_size": self.page_size,
                "total_pages": self.total_pages,
                "has_next": self.has_next,
                "has_previous": self.has_previous,
                "cursor": self.cursor
            }
        }


class PaginationStrategy(ABC):
    """Abstract base class for pagination strategies"""
    
    @abstractmethod
    async def get_page(self, page_number: int, page_size: int, **kwargs) -> Page:
        """Get a specific page of results"""
        pass
    
    @abstractmethod
    async def get_all(self, page_size: int = 100, **kwargs) -> AsyncIterator[T]:
        """Get all items as an async iterator"""
        pass


class CursorPaginationStrategy(PaginationStrategy):
    """Cursor-based pagination for GraphQL/NerdGraph"""
    
    def __init__(self, fetch_fn):
        """
        Initialize cursor pagination
        
        Args:
            fetch_fn: Async function that takes (cursor, limit) and returns (items, next_cursor, total)
        """
        self.fetch_fn = fetch_fn
        self._cursor_cache = {}  # Cache cursors for page navigation
    
    async def get_page(self, page_number: int, page_size: int, **kwargs) -> Page:
        """Get a specific page using cursor pagination"""
        if page_number < 1:
            raise ValueError("Page number must be >= 1")
        
        # For cursor pagination, we need to iterate to reach the desired page
        cursor = None
        current_page = 1
        
        # Check cache for a nearby cursor
        for cached_page in sorted(self._cursor_cache.keys(), reverse=True):
            if cached_page < page_number:
                cursor = self._cursor_cache[cached_page]
                current_page = cached_page + 1
                break
        
        # Iterate to the desired page
        items = []
        total_count = 0
        
        while current_page <= page_number:
            result_items, next_cursor, total = await self.fetch_fn(
                cursor=cursor, 
                limit=page_size,
                **kwargs
            )
            
            if current_page == page_number:
                items = result_items
                total_count = total
                
                # Cache the cursor for this page
                if next_cursor and current_page not in self._cursor_cache:
                    self._cursor_cache[current_page] = cursor
                
                return Page(
                    items=items,
                    total_count=total_count,
                    page_number=page_number,
                    page_size=page_size,
                    has_next=bool(next_cursor),
                    has_previous=page_number > 1,
                    cursor=next_cursor
                )
            
            cursor = next_cursor
            current_page += 1
            
            if not cursor:
                # No more pages
                return Page(
                    items=[],
                    total_count=total_count,
                    page_number=page_number,
                    page_size=page_size,
                    has_next=False,
                    has_previous=page_number > 1
                )
    
    async def get_all(self, page_size: int = 100, **kwargs) -> AsyncIterator[T]:
        """Get all items as an async iterator"""
        cursor = None
        
        while True:
            items, next_cursor, _ = await self.fetch_fn(
                cursor=cursor,
                limit=page_size,
                **kwargs
            )
            
            for item in items:
                yield item
            
            if not next_cursor:
                break
            
            cursor = next_cursor


class OffsetPaginationStrategy(PaginationStrategy):
    """Offset-based pagination for traditional APIs"""
    
    def __init__(self, fetch_fn, count_fn=None):
        """
        Initialize offset pagination
        
        Args:
            fetch_fn: Async function that takes (offset, limit) and returns items
            count_fn: Optional async function that returns total count
        """
        self.fetch_fn = fetch_fn
        self.count_fn = count_fn
    
    async def get_page(self, page_number: int, page_size: int, **kwargs) -> Page:
        """Get a specific page using offset pagination"""
        if page_number < 1:
            raise ValueError("Page number must be >= 1")
        
        offset = (page_number - 1) * page_size
        
        # Fetch items
        items = await self.fetch_fn(offset=offset, limit=page_size, **kwargs)
        
        # Get total count if available
        total_count = len(items)  # Default to items length
        if self.count_fn:
            try:
                total_count = await self.count_fn(**kwargs)
            except Exception as e:
                logger.warning(f"Failed to get total count: {e}")
        
        return Page(
            items=items,
            total_count=total_count,
            page_number=page_number,
            page_size=page_size,
            has_next=len(items) == page_size,
            has_previous=page_number > 1
        )
    
    async def get_all(self, page_size: int = 100, **kwargs) -> AsyncIterator[T]:
        """Get all items as an async iterator"""
        offset = 0
        
        while True:
            items = await self.fetch_fn(offset=offset, limit=page_size, **kwargs)
            
            if not items:
                break
            
            for item in items:
                yield item
            
            if len(items) < page_size:
                break
            
            offset += page_size


class BatchProcessor:
    """Process large datasets in batches"""
    
    def __init__(self, batch_size: int = 100, max_concurrent: int = 5):
        """
        Initialize batch processor
        
        Args:
            batch_size: Number of items per batch
            max_concurrent: Maximum concurrent batch processing
        """
        self.batch_size = batch_size
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_batch(self, items: List[T], process_fn) -> List[Any]:
        """Process a batch of items"""
        async with self.semaphore:
            return await process_fn(items)
    
    async def process_all(self, items: List[T], process_fn) -> List[Any]:
        """Process all items in batches"""
        results = []
        
        # Split into batches
        batches = [
            items[i:i + self.batch_size]
            for i in range(0, len(items), self.batch_size)
        ]
        
        # Process batches concurrently
        batch_results = await asyncio.gather(
            *[self.process_batch(batch, process_fn) for batch in batches]
        )
        
        # Flatten results
        for batch_result in batch_results:
            results.extend(batch_result)
        
        return results


class StreamingPaginator:
    """Stream large result sets with backpressure control"""
    
    def __init__(self, fetch_strategy: PaginationStrategy, 
                 buffer_size: int = 10, page_size: int = 100):
        """
        Initialize streaming paginator
        
        Args:
            fetch_strategy: Pagination strategy to use
            buffer_size: Number of pages to buffer
            page_size: Items per page
        """
        self.strategy = fetch_strategy
        self.buffer_size = buffer_size
        self.page_size = page_size
        self._buffer = asyncio.Queue(maxsize=buffer_size)
        self._fetch_task = None
    
    async def stream(self, **kwargs) -> AsyncIterator[T]:
        """Stream items with buffering"""
        # Start background fetch task
        self._fetch_task = asyncio.create_task(
            self._fetch_pages(**kwargs)
        )
        
        try:
            while True:
                try:
                    # Get from buffer with timeout
                    page = await asyncio.wait_for(
                        self._buffer.get(),
                        timeout=30.0
                    )
                    
                    if page is None:  # Sentinel value
                        break
                    
                    for item in page.items:
                        yield item
                        
                except asyncio.TimeoutError:
                    logger.warning("Timeout waiting for page buffer")
                    break
                    
        finally:
            if self._fetch_task and not self._fetch_task.done():
                self._fetch_task.cancel()
    
    async def _fetch_pages(self, **kwargs):
        """Background task to fetch pages"""
        page_number = 1
        
        try:
            while True:
                page = await self.strategy.get_page(
                    page_number=page_number,
                    page_size=self.page_size,
                    **kwargs
                )
                
                await self._buffer.put(page)
                
                if not page.has_next:
                    break
                
                page_number += 1
                
        except Exception as e:
            logger.error(f"Error fetching pages: {e}")
        finally:
            # Send sentinel value
            await self._buffer.put(None)


def paginate_results(items: List[T], page: int = 1, 
                    page_size: int = 50) -> Dict[str, Any]:
    """
    Simple pagination helper for in-memory lists
    
    Args:
        items: List of items to paginate
        page: Page number (1-indexed)
        page_size: Items per page
        
    Returns:
        Paginated result dictionary
    """
    if page < 1:
        page = 1
    
    total_items = len(items)
    total_pages = math.ceil(total_items / page_size) if page_size > 0 else 0
    
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    page_items = items[start_idx:end_idx]
    
    return {
        "items": page_items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1
        }
    }


class PaginationCache:
    """Cache for paginated results"""
    
    def __init__(self, cache_backend, ttl: int = 300):
        """
        Initialize pagination cache
        
        Args:
            cache_backend: Cache backend to use
            ttl: Cache TTL in seconds
        """
        self.cache = cache_backend
        self.ttl = ttl
    
    def _generate_key(self, base_key: str, page: int, page_size: int, 
                     filters: Optional[Dict] = None) -> str:
        """Generate cache key for paginated results"""
        key_parts = [base_key, f"page:{page}", f"size:{page_size}"]
        
        if filters:
            # Sort filters for consistent keys
            filter_str = json.dumps(filters, sort_keys=True)
            filter_hash = hashlib.md5(filter_str.encode()).hexdigest()[:8]
            key_parts.append(f"filters:{filter_hash}")
        
        return ":".join(key_parts)
    
    async def get_page(self, base_key: str, page: int, page_size: int,
                      filters: Optional[Dict] = None) -> Optional[Page]:
        """Get cached page"""
        key = self._generate_key(base_key, page, page_size, filters)
        cached = await self.cache.get(key)
        
        if cached:
            # Reconstruct Page object
            return Page(**cached)
        
        return None
    
    async def set_page(self, base_key: str, page: Page,
                      filters: Optional[Dict] = None):
        """Cache a page"""
        key = self._generate_key(base_key, page.page_number, 
                                page.page_size, filters)
        await self.cache.set(key, page.to_dict(), ttl=self.ttl)
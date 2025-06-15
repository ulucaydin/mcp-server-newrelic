"""Patterns service implementation."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional
from urllib.parse import quote

from ..models import (
    Pattern,
    SearchPatternsOptions,
    SearchPatternsResponse,
)

if TYPE_CHECKING:
    from ..client import AsyncUDSClient, SyncUDSClient


class AsyncPatternsService:
    """Async service for pattern operations."""
    
    def __init__(self, client: "AsyncUDSClient"):
        self.client = client
    
    async def search(
        self, options: Optional[SearchPatternsOptions] = None
    ) -> SearchPatternsResponse:
        """Search for patterns."""
        params = {}
        if options:
            if options.query:
                params["query"] = options.query
            if options.category:
                params["category"] = options.category
            if options.tags:
                params["tags"] = options.tags
            if options.limit is not None:
                params["limit"] = str(options.limit)
            if options.offset is not None:
                params["offset"] = str(options.offset)
        
        return await self.client.get(
            "/patterns",
            params=params,
            response_model=SearchPatternsResponse,
        )
    
    async def get(self, pattern_id: str) -> Pattern:
        """Get a specific pattern by ID."""
        return await self.client.get(
            f"/patterns/{quote(pattern_id, safe='')}",
            response_model=Pattern,
        )
    
    async def create(
        self,
        name: str,
        description: str,
        query: str,
        category: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Pattern:
        """Create a new pattern."""
        data = {
            "name": name,
            "description": description,
            "query": query,
            "category": category,
        }
        if tags:
            data["tags"] = tags
        if metadata:
            data["metadata"] = metadata
        
        return await self.client.post("/patterns", json=data, response_model=Pattern)
    
    async def update(
        self,
        pattern_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        query: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Pattern:
        """Update an existing pattern."""
        data = {}
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        if query is not None:
            data["query"] = query
        if category is not None:
            data["category"] = category
        if tags is not None:
            data["tags"] = tags
        if metadata is not None:
            data["metadata"] = metadata
        
        return await self.client.put(
            f"/patterns/{quote(pattern_id, safe='')}",
            json=data,
            response_model=Pattern,
        )
    
    async def delete(self, pattern_id: str) -> None:
        """Delete a pattern."""
        await self.client.delete(f"/patterns/{quote(pattern_id, safe='')}")
    
    async def execute(
        self, pattern_id: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a pattern by ID."""
        data = await self.client.post(
            f"/patterns/{quote(pattern_id, safe='')}/execute",
            json={"variables": variables} if variables else None,
        )
        return data
    
    async def get_categories(self) -> List[str]:
        """Get all pattern categories."""
        data = await self.client.get("/patterns/categories")
        return data
    
    async def get_tags(self) -> List[str]:
        """Get all unique tags."""
        data = await self.client.get("/patterns/tags")
        return data


class SyncPatternsService:
    """Synchronous service for pattern operations."""
    
    def __init__(self, client: "SyncUDSClient"):
        self.client = client
    
    def search(
        self, options: Optional[SearchPatternsOptions] = None
    ) -> SearchPatternsResponse:
        """Search for patterns."""
        params = {}
        if options:
            if options.query:
                params["query"] = options.query
            if options.category:
                params["category"] = options.category
            if options.tags:
                params["tags"] = options.tags
            if options.limit is not None:
                params["limit"] = str(options.limit)
            if options.offset is not None:
                params["offset"] = str(options.offset)
        
        return self.client.get(
            "/patterns",
            params=params,
            response_model=SearchPatternsResponse,
        )
    
    def get(self, pattern_id: str) -> Pattern:
        """Get a specific pattern by ID."""
        return self.client.get(
            f"/patterns/{quote(pattern_id, safe='')}",
            response_model=Pattern,
        )
    
    def create(
        self,
        name: str,
        description: str,
        query: str,
        category: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Pattern:
        """Create a new pattern."""
        data = {
            "name": name,
            "description": description,
            "query": query,
            "category": category,
        }
        if tags:
            data["tags"] = tags
        if metadata:
            data["metadata"] = metadata
        
        return self.client.post("/patterns", json=data, response_model=Pattern)
    
    def update(
        self,
        pattern_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        query: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Pattern:
        """Update an existing pattern."""
        data = {}
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        if query is not None:
            data["query"] = query
        if category is not None:
            data["category"] = category
        if tags is not None:
            data["tags"] = tags
        if metadata is not None:
            data["metadata"] = metadata
        
        return self.client.put(
            f"/patterns/{quote(pattern_id, safe='')}",
            json=data,
            response_model=Pattern,
        )
    
    def delete(self, pattern_id: str) -> None:
        """Delete a pattern."""
        self.client.delete(f"/patterns/{quote(pattern_id, safe='')}")
    
    def execute(
        self, pattern_id: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a pattern by ID."""
        data = self.client.post(
            f"/patterns/{quote(pattern_id, safe='')}/execute",
            json={"variables": variables} if variables else None,
        )
        return data
    
    def get_categories(self) -> List[str]:
        """Get all pattern categories."""
        data = self.client.get("/patterns/categories")
        return data
    
    def get_tags(self) -> List[str]:
        """Get all unique tags."""
        data = self.client.get("/patterns/tags")
        return data
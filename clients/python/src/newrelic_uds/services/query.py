"""Query service implementation."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional
from urllib.parse import quote

from ..models import QueryRequest, QueryResponse

if TYPE_CHECKING:
    from ..client import AsyncUDSClient, SyncUDSClient


class AsyncQueryService:
    """Async service for query operations."""
    
    def __init__(self, client: "AsyncUDSClient"):
        self.client = client
    
    async def execute(self, request: QueryRequest) -> QueryResponse:
        """Execute a query."""
        return await self.client.post(
            "/query",
            json=request.model_dump(by_alias=True, exclude_none=True),
            response_model=QueryResponse,
        )
    
    async def validate(self, query: str) -> Dict[str, Any]:
        """Validate a query without executing it."""
        data = await self.client.post("/query/validate", json={"query": query})
        return data
    
    async def suggest(
        self,
        partial: str,
        event_type: Optional[str] = None,
        cursor_position: Optional[int] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get query suggestions based on partial input."""
        request_data = {"partial": partial}
        if event_type:
            request_data["eventType"] = event_type
        if cursor_position is not None:
            request_data["cursorPosition"] = cursor_position
        
        data = await self.client.post("/query/suggest", json=request_data)
        return data
    
    async def format(self, query: str) -> Dict[str, Any]:
        """Format a query."""
        data = await self.client.post("/query/format", json={"query": query})
        return data
    
    async def get_history(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        from_time: Optional[str] = None,
        to_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get query history."""
        params = {}
        if limit is not None:
            params["limit"] = str(limit)
        if offset is not None:
            params["offset"] = str(offset)
        if from_time:
            params["from"] = from_time
        if to_time:
            params["to"] = to_time
        
        data = await self.client.get("/query/history", params=params)
        return data
    
    async def export(
        self, query_id: str, format: str = "csv"
    ) -> bytes:
        """Export query results."""
        response = await self.client.request(
            "GET",
            f"/query/{quote(query_id, safe='')}/export",
            params={"format": format},
        )
        return response.content


class SyncQueryService:
    """Synchronous service for query operations."""
    
    def __init__(self, client: "SyncUDSClient"):
        self.client = client
    
    def execute(self, request: QueryRequest) -> QueryResponse:
        """Execute a query."""
        return self.client.post(
            "/query",
            json=request.model_dump(by_alias=True, exclude_none=True),
            response_model=QueryResponse,
        )
    
    def validate(self, query: str) -> Dict[str, Any]:
        """Validate a query without executing it."""
        data = self.client.post("/query/validate", json={"query": query})
        return data
    
    def suggest(
        self,
        partial: str,
        event_type: Optional[str] = None,
        cursor_position: Optional[int] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get query suggestions based on partial input."""
        request_data = {"partial": partial}
        if event_type:
            request_data["eventType"] = event_type
        if cursor_position is not None:
            request_data["cursorPosition"] = cursor_position
        
        data = self.client.post("/query/suggest", json=request_data)
        return data
    
    def format(self, query: str) -> Dict[str, Any]:
        """Format a query."""
        data = self.client.post("/query/format", json={"query": query})
        return data
    
    def get_history(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        from_time: Optional[str] = None,
        to_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get query history."""
        params = {}
        if limit is not None:
            params["limit"] = str(limit)
        if offset is not None:
            params["offset"] = str(offset)
        if from_time:
            params["from"] = from_time
        if to_time:
            params["to"] = to_time
        
        data = self.client.get("/query/history", params=params)
        return data
    
    def export(self, query_id: str, format: str = "csv") -> bytes:
        """Export query results."""
        response = self.client.request(
            "GET",
            f"/query/{quote(query_id, safe='')}/export",
            params={"format": format},
        )
        return response.content
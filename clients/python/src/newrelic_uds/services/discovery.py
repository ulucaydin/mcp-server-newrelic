"""Discovery service implementation."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional
from urllib.parse import quote

from ..models import (
    ListSchemasOptions,
    ListSchemasResponse,
    QualityMetrics,
    Schema,
)

if TYPE_CHECKING:
    from ..client import AsyncUDSClient, SyncUDSClient


class AsyncDiscoveryService:
    """Async service for schema discovery operations."""
    
    def __init__(self, client: "AsyncUDSClient"):
        self.client = client
    
    async def list_schemas(
        self, options: Optional[ListSchemasOptions] = None
    ) -> ListSchemasResponse:
        """List discovered schemas."""
        params = {}
        if options:
            if options.event_type:
                params["eventType"] = options.event_type
            if options.min_record_count is not None:
                params["minRecordCount"] = str(options.min_record_count)
            if options.max_schemas is not None:
                params["maxSchemas"] = str(options.max_schemas)
            if options.sort_by:
                params["sortBy"] = options.sort_by
            if options.include_metadata is not None:
                params["includeMetadata"] = str(options.include_metadata).lower()
        
        return await self.client.get(
            "/discovery/schemas",
            params=params,
            response_model=ListSchemasResponse,
        )
    
    async def get_schema(self, name: str) -> Schema:
        """Get a specific schema by name."""
        return await self.client.get(
            f"/discovery/schemas/{quote(name, safe='')}",
            response_model=Schema,
        )
    
    async def analyze_quality(self, name: str) -> QualityMetrics:
        """Analyze the quality of a schema."""
        return await self.client.post(
            f"/discovery/schemas/{quote(name, safe='')}/analyze",
            response_model=QualityMetrics,
        )
    
    async def compare_schemas(
        self, schema1: str, schema2: str
    ) -> Dict[str, Any]:
        """Compare two schemas."""
        data = await self.client.post(
            "/discovery/schemas/compare",
            json={"schema1": schema1, "schema2": schema2},
        )
        return data
    
    async def get_recommendations(
        self, event_type: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get schema recommendations."""
        params = {"eventType": event_type} if event_type else None
        data = await self.client.get("/discovery/recommendations", params=params)
        return data


class SyncDiscoveryService:
    """Synchronous service for schema discovery operations."""
    
    def __init__(self, client: "SyncUDSClient"):
        self.client = client
    
    def list_schemas(
        self, options: Optional[ListSchemasOptions] = None
    ) -> ListSchemasResponse:
        """List discovered schemas."""
        params = {}
        if options:
            if options.event_type:
                params["eventType"] = options.event_type
            if options.min_record_count is not None:
                params["minRecordCount"] = str(options.min_record_count)
            if options.max_schemas is not None:
                params["maxSchemas"] = str(options.max_schemas)
            if options.sort_by:
                params["sortBy"] = options.sort_by
            if options.include_metadata is not None:
                params["includeMetadata"] = str(options.include_metadata).lower()
        
        return self.client.get(
            "/discovery/schemas",
            params=params,
            response_model=ListSchemasResponse,
        )
    
    def get_schema(self, name: str) -> Schema:
        """Get a specific schema by name."""
        return self.client.get(
            f"/discovery/schemas/{quote(name, safe='')}",
            response_model=Schema,
        )
    
    def analyze_quality(self, name: str) -> QualityMetrics:
        """Analyze the quality of a schema."""
        return self.client.post(
            f"/discovery/schemas/{quote(name, safe='')}/analyze",
            response_model=QualityMetrics,
        )
    
    def compare_schemas(self, schema1: str, schema2: str) -> Dict[str, Any]:
        """Compare two schemas."""
        data = self.client.post(
            "/discovery/schemas/compare",
            json={"schema1": schema1, "schema2": schema2},
        )
        return data
    
    def get_recommendations(
        self, event_type: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get schema recommendations."""
        params = {"eventType": event_type} if event_type else None
        data = self.client.get("/discovery/recommendations", params=params)
        return data
"""Dashboard service implementation."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional
from urllib.parse import quote

from ..models import (
    Dashboard,
    ListDashboardsOptions,
    ListDashboardsResponse,
    Widget,
)

if TYPE_CHECKING:
    from ..client import AsyncUDSClient, SyncUDSClient


class AsyncDashboardService:
    """Async service for dashboard operations."""
    
    def __init__(self, client: "AsyncUDSClient"):
        self.client = client
    
    async def list(
        self, options: Optional[ListDashboardsOptions] = None
    ) -> ListDashboardsResponse:
        """List all dashboards."""
        params = {}
        if options:
            if options.search:
                params["search"] = options.search
            if options.tags:
                params["tags"] = options.tags
            if options.limit is not None:
                params["limit"] = str(options.limit)
            if options.offset is not None:
                params["offset"] = str(options.offset)
        
        return await self.client.get(
            "/dashboards",
            params=params,
            response_model=ListDashboardsResponse,
        )
    
    async def get(self, dashboard_id: str) -> Dashboard:
        """Get a specific dashboard by ID."""
        return await self.client.get(
            f"/dashboards/{quote(dashboard_id, safe='')}",
            response_model=Dashboard,
        )
    
    async def create(
        self,
        name: str,
        widgets: List[Dict[str, Any]],
        description: Optional[str] = None,
        layout: Optional[Dict[str, Any]] = None,
        variables: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dashboard:
        """Create a new dashboard."""
        data = {
            "name": name,
            "widgets": widgets,
        }
        if description:
            data["description"] = description
        if layout:
            data["layout"] = layout
        if variables:
            data["variables"] = variables
        if metadata:
            data["metadata"] = metadata
        
        return await self.client.post(
            "/dashboards", json=data, response_model=Dashboard
        )
    
    async def update(
        self,
        dashboard_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        widgets: Optional[List[Dict[str, Any]]] = None,
        layout: Optional[Dict[str, Any]] = None,
        variables: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dashboard:
        """Update an existing dashboard."""
        data = {}
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        if widgets is not None:
            data["widgets"] = widgets
        if layout is not None:
            data["layout"] = layout
        if variables is not None:
            data["variables"] = variables
        if metadata is not None:
            data["metadata"] = metadata
        
        return await self.client.put(
            f"/dashboards/{quote(dashboard_id, safe='')}",
            json=data,
            response_model=Dashboard,
        )
    
    async def delete(self, dashboard_id: str) -> None:
        """Delete a dashboard."""
        await self.client.delete(f"/dashboards/{quote(dashboard_id, safe='')}")
    
    async def clone(self, dashboard_id: str, new_name: str) -> Dashboard:
        """Clone a dashboard."""
        return await self.client.post(
            f"/dashboards/{quote(dashboard_id, safe='')}/clone",
            json={"name": new_name},
            response_model=Dashboard,
        )
    
    async def export(
        self, dashboard_id: str, format: str = "json"
    ) -> str:
        """Export a dashboard."""
        response = await self.client.request(
            "GET",
            f"/dashboards/{quote(dashboard_id, safe='')}/export",
            params={"format": format},
        )
        return response.text
    
    async def import_dashboard(
        self, data: str, format: str = "json"
    ) -> Dashboard:
        """Import a dashboard."""
        headers = {
            "Content-Type": (
                "application/json" if format == "json" else "application/x-yaml"
            )
        }
        response = await self.client.request(
            "POST",
            "/dashboards/import",
            json=data if format == "json" else None,
            headers=headers,
        )
        return Dashboard(**response.json())
    
    async def get_tags(self) -> List[str]:
        """Get all dashboard tags."""
        data = await self.client.get("/dashboards/tags")
        return data
    
    async def render_widget(
        self,
        dashboard_id: str,
        widget_id: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Render a dashboard widget."""
        data = await self.client.post(
            f"/dashboards/{quote(dashboard_id, safe='')}/widgets/{quote(widget_id, safe='')}/render",
            json={"variables": variables} if variables else None,
        )
        return data


class SyncDashboardService:
    """Synchronous service for dashboard operations."""
    
    def __init__(self, client: "SyncUDSClient"):
        self.client = client
    
    def list(
        self, options: Optional[ListDashboardsOptions] = None
    ) -> ListDashboardsResponse:
        """List all dashboards."""
        params = {}
        if options:
            if options.search:
                params["search"] = options.search
            if options.tags:
                params["tags"] = options.tags
            if options.limit is not None:
                params["limit"] = str(options.limit)
            if options.offset is not None:
                params["offset"] = str(options.offset)
        
        return self.client.get(
            "/dashboards",
            params=params,
            response_model=ListDashboardsResponse,
        )
    
    def get(self, dashboard_id: str) -> Dashboard:
        """Get a specific dashboard by ID."""
        return self.client.get(
            f"/dashboards/{quote(dashboard_id, safe='')}",
            response_model=Dashboard,
        )
    
    def create(
        self,
        name: str,
        widgets: List[Dict[str, Any]],
        description: Optional[str] = None,
        layout: Optional[Dict[str, Any]] = None,
        variables: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dashboard:
        """Create a new dashboard."""
        data = {
            "name": name,
            "widgets": widgets,
        }
        if description:
            data["description"] = description
        if layout:
            data["layout"] = layout
        if variables:
            data["variables"] = variables
        if metadata:
            data["metadata"] = metadata
        
        return self.client.post("/dashboards", json=data, response_model=Dashboard)
    
    def update(
        self,
        dashboard_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        widgets: Optional[List[Dict[str, Any]]] = None,
        layout: Optional[Dict[str, Any]] = None,
        variables: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dashboard:
        """Update an existing dashboard."""
        data = {}
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        if widgets is not None:
            data["widgets"] = widgets
        if layout is not None:
            data["layout"] = layout
        if variables is not None:
            data["variables"] = variables
        if metadata is not None:
            data["metadata"] = metadata
        
        return self.client.put(
            f"/dashboards/{quote(dashboard_id, safe='')}",
            json=data,
            response_model=Dashboard,
        )
    
    def delete(self, dashboard_id: str) -> None:
        """Delete a dashboard."""
        self.client.delete(f"/dashboards/{quote(dashboard_id, safe='')}")
    
    def clone(self, dashboard_id: str, new_name: str) -> Dashboard:
        """Clone a dashboard."""
        return self.client.post(
            f"/dashboards/{quote(dashboard_id, safe='')}/clone",
            json={"name": new_name},
            response_model=Dashboard,
        )
    
    def export(self, dashboard_id: str, format: str = "json") -> str:
        """Export a dashboard."""
        response = self.client.request(
            "GET",
            f"/dashboards/{quote(dashboard_id, safe='')}/export",
            params={"format": format},
        )
        return response.text
    
    def import_dashboard(self, data: str, format: str = "json") -> Dashboard:
        """Import a dashboard."""
        headers = {
            "Content-Type": (
                "application/json" if format == "json" else "application/x-yaml"
            )
        }
        response = self.client.request(
            "POST",
            "/dashboards/import",
            json=data if format == "json" else None,
            headers=headers,
        )
        return Dashboard(**response.json())
    
    def get_tags(self) -> List[str]:
        """Get all dashboard tags."""
        data = self.client.get("/dashboards/tags")
        return data
    
    def render_widget(
        self,
        dashboard_id: str,
        widget_id: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Render a dashboard widget."""
        data = self.client.post(
            f"/dashboards/{quote(dashboard_id, safe='')}/widgets/{quote(widget_id, safe='')}/render",
            json={"variables": variables} if variables else None,
        )
        return data
"""Service modules for the UDS client."""

from .dashboard import AsyncDashboardService, SyncDashboardService
from .discovery import AsyncDiscoveryService, SyncDiscoveryService
from .patterns import AsyncPatternsService, SyncPatternsService
from .query import AsyncQueryService, SyncQueryService

__all__ = [
    "AsyncDiscoveryService",
    "SyncDiscoveryService",
    "AsyncPatternsService",
    "SyncPatternsService",
    "AsyncQueryService",
    "SyncQueryService",
    "AsyncDashboardService",
    "SyncDashboardService",
]
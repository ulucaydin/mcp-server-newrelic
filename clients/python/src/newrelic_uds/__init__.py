"""New Relic UDS Python Client Library.

A modern, async-first Python client for the New Relic Unified Data Service (UDS) API.
"""

from .client import AsyncUDSClient, SyncUDSClient
from .models import (
    APIError,
    ClientConfig,
    Dashboard,
    HealthStatus,
    Pattern,
    QueryRequest,
    QueryResponse,
    Schema,
)

__version__ = "1.0.0"
__all__ = [
    "AsyncUDSClient",
    "SyncUDSClient",
    "ClientConfig",
    "APIError",
    "HealthStatus",
    "Schema",
    "Pattern",
    "QueryRequest",
    "QueryResponse",
    "Dashboard",
]
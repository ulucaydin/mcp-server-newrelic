"""
Pytest configuration and fixtures for New Relic MCP Server tests
"""

import pytest
import asyncio
import os
import sys
from typing import Dict, Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastmcp import FastMCP
from core.nerdgraph_client import NerdGraphClient
from core.account_manager import AccountManager
from core.session_manager import SessionManager
from core.entity_definitions import EntityDefinitionsCache
from core.cache import get_cache
from core.health import initialize_health_monitor
from core.audit import initialize_audit_logger


@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mock_nerdgraph():
    """Mock NerdGraph client"""
    mock = AsyncMock(spec=NerdGraphClient)
    
    # Mock common responses
    mock.query.return_value = {
        "actor": {
            "user": {"email": "test@example.com"}
        }
    }
    
    mock.execute_nrql.return_value = {
        "actor": {
            "account": {
                "nrql": {
                    "results": [{"count": 100}]
                }
            }
        }
    }
    
    # Mock close method
    mock.close = AsyncMock()
    
    return mock


@pytest.fixture
def mock_account_manager():
    """Mock account manager"""
    manager = MagicMock(spec=AccountManager)
    manager.get_current_credentials.return_value = {
        "api_key": "test-api-key",
        "account_id": "123456",
        "nerdgraph_url": "https://api.newrelic.com/graphql"
    }
    manager.current_account = "test"
    manager.list_accounts.return_value = {
        "test": {
            "account_id": "123456",
            "region": "US",
            "is_current": True
        }
    }
    return manager


@pytest.fixture
def mock_session_manager():
    """Mock session manager"""
    return MagicMock(spec=SessionManager)


@pytest.fixture
def mock_entity_definitions():
    """Mock entity definitions cache"""
    cache = MagicMock(spec=EntityDefinitionsCache)
    cache.get_golden_metrics.return_value = [
        {"metric": "apm.service.transaction.duration", "name": "Response Time"},
        {"metric": "apm.service.error.rate", "name": "Error Rate"}
    ]
    return cache


@pytest.fixture
async def test_services(mock_nerdgraph, mock_account_manager, 
                       mock_session_manager, mock_entity_definitions):
    """Create test services dictionary"""
    # Initialize real cache
    cache = get_cache()
    
    # Initialize health monitor with mocks
    health_monitor = initialize_health_monitor(
        nerdgraph_client=mock_nerdgraph,
        cache=cache
    )
    
    # Initialize audit logger for testing
    audit_logger = initialize_audit_logger(
        log_file=None,  # No file logging in tests
        enable_console=False,  # Disable console logging
        enable_metrics=False  # Disable metrics
    )
    
    return {
        "account_manager": mock_account_manager,
        "session_manager": mock_session_manager,
        "nerdgraph": mock_nerdgraph,
        "entity_definitions": mock_entity_definitions,
        "account_id": "123456",
        "cache": cache,
        "health_monitor": health_monitor,
        "audit_logger": audit_logger
    }


@pytest.fixture
async def test_app(test_services) -> AsyncGenerator[FastMCP, None]:
    """Create test MCP application"""
    app = FastMCP(
        name="test-newrelic-mcp",
        version="1.0.0",
        description="Test New Relic MCP Server"
    )
    
    # Store services for testing
    app._services = test_services
    
    yield app
    
    # Cleanup
    if hasattr(app, '_cleanup_handlers'):
        for handler in app._cleanup_handlers:
            await handler()


@pytest.fixture
def sample_nerdgraph_response():
    """Sample NerdGraph response for testing"""
    return {
        "data": {
            "actor": {
                "account": {
                    "name": "Test Account",
                    "id": 123456
                }
            }
        }
    }


@pytest.fixture
def sample_entity_response():
    """Sample entity response for testing"""
    return {
        "actor": {
            "entitySearch": {
                "results": {
                    "entities": [
                        {
                            "guid": "MTIzNDU2fEFQTXxBUFBMSUNBVElPTnwxMjM0NTY3",
                            "name": "Test App",
                            "entityType": "APM_APPLICATION",
                            "domain": "APM",
                            "accountId": 123456,
                            "tags": [
                                {"key": "environment", "value": "production"}
                            ]
                        }
                    ],
                    "nextCursor": None
                },
                "count": 1
            }
        }
    }


@pytest.fixture
def sample_incident_response():
    """Sample incident response for testing"""
    return {
        "actor": {
            "account": {
                "alerts": {
                    "incidents": {
                        "incidents": [
                            {
                                "incidentId": "INC-001",
                                "title": "High Error Rate",
                                "priority": "CRITICAL",
                                "state": "OPEN",
                                "policyName": "Default Policy",
                                "conditionName": "Error Rate > 5%",
                                "entity": {
                                    "guid": "MTIzNDU2fEFQTXxBUFBMSUNBVElPTnwxMjM0NTY3",
                                    "name": "Test App",
                                    "type": "APPLICATION"
                                },
                                "startedAt": "2025-01-01T00:00:00Z",
                                "updatedAt": "2025-01-01T00:05:00Z"
                            }
                        ],
                        "nextCursor": None,
                        "totalCount": 1
                    }
                }
            }
        }
    }


@pytest.fixture
def env_setup(monkeypatch):
    """Set up test environment variables"""
    monkeypatch.setenv("NEW_RELIC_API_KEY", "test-api-key")
    monkeypatch.setenv("NEW_RELIC_ACCOUNT_ID", "123456")
    monkeypatch.setenv("LOG_LEVEL", "ERROR")  # Reduce log noise in tests
    monkeypatch.setenv("MCP_TRANSPORT", "stdio")  # Default to stdio transport
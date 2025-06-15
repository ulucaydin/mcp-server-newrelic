"""Pytest configuration and fixtures."""

import pytest
from httpx import Response

from newrelic_uds import AsyncUDSClient, ClientConfig, SyncUDSClient


@pytest.fixture
def client_config():
    """Provide a test client configuration."""
    return ClientConfig(
        base_url="http://localhost:8080/api/v1",
        api_key="test-api-key",
        timeout=5.0,
        max_retries=2,
        retry_wait=0.1,
        retry_max_wait=1.0,
    )


@pytest.fixture
def async_client(client_config):
    """Create an async client for testing."""
    return AsyncUDSClient(client_config)


@pytest.fixture
def sync_client(client_config):
    """Create a sync client for testing."""
    return SyncUDSClient(client_config)


@pytest.fixture
def mock_response():
    """Create a mock response factory."""
    
    def _mock_response(
        status_code: int = 200,
        json_data: dict = None,
        text_data: str = None,
        headers: dict = None,
    ) -> Response:
        """Create a mock response."""
        response = Response(
            status_code=status_code,
            headers=headers or {},
        )
        
        if json_data is not None:
            response._content = str(json_data).encode()
            response.headers["content-type"] = "application/json"
        elif text_data is not None:
            response._content = text_data.encode()
            response.headers["content-type"] = "text/plain"
        
        return response
    
    return _mock_response


@pytest.fixture
def sample_schema():
    """Provide a sample schema for testing."""
    return {
        "name": "Transaction",
        "eventType": "Transaction",
        "attributes": [
            {
                "name": "timestamp",
                "data_type": "timestamp",
                "nullable": False,
                "cardinality": 1000000,
            },
            {
                "name": "duration",
                "data_type": "number",
                "nullable": False,
                "cardinality": 10000,
            },
        ],
        "record_count": 1000000,
        "first_seen": "2024-01-01T00:00:00Z",
        "last_seen": "2024-12-01T00:00:00Z",
        "quality": {
            "overall_score": 0.85,
            "completeness": 0.9,
            "consistency": 0.85,
            "validity": 0.8,
            "uniqueness": 0.85,
        },
    }


@pytest.fixture
def sample_pattern():
    """Provide a sample pattern for testing."""
    return {
        "id": "pat-123",
        "name": "Error Rate Pattern",
        "description": "Calculate error rate over time",
        "query": "SELECT rate(errors) FROM Transaction",
        "category": "monitoring",
        "tags": ["errors", "performance"],
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_dashboard():
    """Provide a sample dashboard for testing."""
    return {
        "id": "dash-123",
        "name": "Production Monitoring",
        "description": "Key metrics for production",
        "widgets": [
            {
                "id": "widget-1",
                "type": "line-chart",
                "title": "Response Time",
                "query": "SELECT avg(duration) FROM Transaction TIMESERIES",
                "visualization": {
                    "type": "line",
                    "options": {"showLegend": True},
                },
            }
        ],
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
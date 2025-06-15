"""Tests for the main client classes."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx

from newrelic_uds import AsyncUDSClient, SyncUDSClient, APIError, ClientConfig


class TestAsyncUDSClient:
    """Tests for the async client."""
    
    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test client initialization with default config."""
        client = AsyncUDSClient()
        assert client.config.base_url == "http://localhost:8080/api/v1"
        assert client.config.user_agent == "newrelic-uds-python/1.0.0"
        assert client.config.timeout == 30.0
        assert client.config.max_retries == 3
    
    @pytest.mark.asyncio
    async def test_client_with_custom_config(self):
        """Test client initialization with custom config."""
        config = ClientConfig(
            base_url="https://api.example.com",
            api_key="test-key",
            timeout=60.0,
            max_retries=5,
        )
        client = AsyncUDSClient(config)
        assert client.config.base_url == "https://api.example.com"
        assert client.config.api_key == "test-key"
        assert client.headers["Authorization"] == "Bearer test-key"
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        async with AsyncUDSClient() as client:
            assert client._client is not None
            assert isinstance(client._client, httpx.AsyncClient)
        
        # Client should be closed after context
        assert client._client is None
    
    @pytest.mark.asyncio
    async def test_health_check(self, async_client):
        """Test health check endpoint."""
        health_data = {
            "status": "healthy",
            "version": "1.0.0",
            "uptime": "24h",
            "components": {"discovery": {"status": "healthy"}},
        }
        
        with patch.object(
            async_client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = health_data
            
            health = await async_client.health()
            mock_get.assert_called_once_with("/health", response_model=pytest.Any)
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self, async_client):
        """Test API error handling."""
        error_response = Mock(spec=httpx.Response)
        error_response.status_code = 404
        error_response.json.return_value = {
            "error": "not_found",
            "message": "Resource not found",
            "details": {"resource": "schema"},
        }
        
        async_client._handle_error_response(error_response)  # Should not raise
        
        error_response.status_code = 404
        with pytest.raises(APIError) as exc_info:
            async_client._handle_error_response(error_response)
        
        assert exc_info.value.error == "not_found"
        assert exc_info.value.message == "Resource not found"
        assert exc_info.value.status_code == 404
    
    @pytest.mark.asyncio
    async def test_set_api_key(self, async_client):
        """Test updating API key."""
        async_client.set_api_key("new-api-key")
        assert async_client.config.api_key == "new-api-key"
        assert async_client.headers["Authorization"] == "Bearer new-api-key"
    
    @pytest.mark.asyncio
    async def test_retry_logic(self, async_client):
        """Test retry logic on network errors."""
        # Mock the client's request method to fail twice then succeed
        attempts = 0
        
        async def mock_request(*args, **kwargs):
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise httpx.NetworkError("Connection failed")
            
            response = Mock(spec=httpx.Response)
            response.status_code = 200
            response.json.return_value = {"status": "healthy"}
            return response
        
        with patch.object(async_client.client, "request", side_effect=mock_request):
            response = await async_client.request("GET", "/health")
            assert response.status_code == 200
            assert attempts == 3  # Should retry twice before succeeding


class TestSyncUDSClient:
    """Tests for the sync client."""
    
    def test_client_initialization(self):
        """Test client initialization with default config."""
        client = SyncUDSClient()
        assert client.config.base_url == "http://localhost:8080/api/v1"
        assert client.config.user_agent == "newrelic-uds-python/1.0.0"
        assert client.config.timeout == 30.0
        assert client.config.max_retries == 3
    
    def test_context_manager(self):
        """Test sync context manager."""
        with SyncUDSClient() as client:
            assert client._client is not None
            assert isinstance(client._client, httpx.Client)
    
    def test_health_check(self, sync_client):
        """Test health check endpoint."""
        health_data = {
            "status": "healthy",
            "version": "1.0.0",
            "uptime": "24h",
            "components": {"discovery": {"status": "healthy"}},
        }
        
        with patch.object(sync_client, "get") as mock_get:
            mock_get.return_value = health_data
            
            health = sync_client.health()
            mock_get.assert_called_once_with("/health", response_model=pytest.Any)
    
    def test_api_error_handling(self, sync_client):
        """Test API error handling."""
        error_response = Mock(spec=httpx.Response)
        error_response.status_code = 404
        error_response.json.return_value = {
            "error": "not_found",
            "message": "Resource not found",
            "details": {"resource": "schema"},
        }
        
        sync_client._handle_error_response(error_response)  # Should not raise
        
        error_response.status_code = 404
        with pytest.raises(APIError) as exc_info:
            sync_client._handle_error_response(error_response)
        
        assert exc_info.value.error == "not_found"
        assert exc_info.value.message == "Resource not found"
        assert exc_info.value.status_code == 404
    
    def test_retry_logic(self, sync_client):
        """Test retry logic on network errors."""
        # Mock the client's request method to fail twice then succeed
        attempts = 0
        
        def mock_request(*args, **kwargs):
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise httpx.NetworkError("Connection failed")
            
            response = Mock(spec=httpx.Response)
            response.status_code = 200
            response.json.return_value = {"status": "healthy"}
            return response
        
        with patch.object(sync_client._client, "request", side_effect=mock_request):
            response = sync_client.request("GET", "/health")
            assert response.status_code == 200
            assert attempts == 3  # Should retry twice before succeeding
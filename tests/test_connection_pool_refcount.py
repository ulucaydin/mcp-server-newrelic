"""
Tests for NerdGraphClient connection pool reference counting
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock

from core.nerdgraph_client import NerdGraphClient


@pytest.mark.asyncio
class TestConnectionPoolRefCounting:
    """Test connection pool reference counting"""
    
    @pytest.fixture
    def mock_httpx_client(self):
        """Create mock httpx client"""
        client = AsyncMock()
        client.aclose = AsyncMock()
        client.post = AsyncMock()
        return client
    
    @pytest.fixture(autouse=True)
    def cleanup_pools(self):
        """Clean up connection pools after each test"""
        yield
        # Clear all pools
        NerdGraphClient._connection_pools.clear()
        NerdGraphClient._pool_ref_counts.clear()
    
    async def test_pool_creation_and_ref_counting(self):
        """Test that pools are created and ref counted properly"""
        api_key = "test-api-key-12345678"
        endpoint = "https://api.test.com/graphql"
        
        # Create first client
        client1 = NerdGraphClient(api_key=api_key, endpoint=endpoint)
        pool_key = f"{endpoint}:{api_key[:8]}"
        
        # Check pool was created with ref count 1
        assert pool_key in NerdGraphClient._connection_pools
        assert NerdGraphClient._pool_ref_counts[pool_key] == 1
        
        # Create second client with same credentials
        client2 = NerdGraphClient(api_key=api_key, endpoint=endpoint)
        
        # Check same pool is used with ref count 2
        assert client1.client is client2.client
        assert NerdGraphClient._pool_ref_counts[pool_key] == 2
        
        # Create third client with different key
        client3 = NerdGraphClient(api_key="different-key-87654321", endpoint=endpoint)
        different_pool_key = f"{endpoint}:different"
        
        # Check new pool was created
        assert different_pool_key in NerdGraphClient._connection_pools
        assert NerdGraphClient._pool_ref_counts[different_pool_key] == 1
        assert client3.client is not client1.client
    
    @patch('core.nerdgraph_client.httpx.AsyncClient')
    async def test_pool_cleanup_on_close(self, mock_async_client_class):
        """Test that pools are cleaned up when ref count reaches 0"""
        mock_client = AsyncMock()
        mock_async_client_class.return_value = mock_client
        
        api_key = "test-api-key-12345678"
        endpoint = "https://api.test.com/graphql"
        pool_key = f"{endpoint}:{api_key[:8]}"
        
        # Create two clients
        client1 = NerdGraphClient(api_key=api_key, endpoint=endpoint)
        client2 = NerdGraphClient(api_key=api_key, endpoint=endpoint)
        
        assert NerdGraphClient._pool_ref_counts[pool_key] == 2
        
        # Close first client
        await client1.close()
        
        # Pool should still exist with ref count 1
        assert pool_key in NerdGraphClient._connection_pools
        assert NerdGraphClient._pool_ref_counts[pool_key] == 1
        assert mock_client.aclose.call_count == 0
        
        # Close second client
        await client2.close()
        
        # Pool should be removed
        assert pool_key not in NerdGraphClient._connection_pools
        assert pool_key not in NerdGraphClient._pool_ref_counts
        mock_client.aclose.assert_called_once()
    
    async def test_close_without_pool_key(self):
        """Test closing a client that doesn't have a pool key"""
        client = NerdGraphClient(api_key="test-key", endpoint="https://test.com")
        
        # Remove pool_key attribute to simulate edge case
        delattr(client, 'pool_key')
        
        # Should not raise error
        await client.close()
    
    @patch('core.nerdgraph_client.httpx.AsyncClient')
    async def test_close_all_pools(self, mock_async_client_class):
        """Test closing all connection pools"""
        # Create mock clients
        mock_client1 = AsyncMock()
        mock_client2 = AsyncMock()
        mock_clients = [mock_client1, mock_client2]
        mock_async_client_class.side_effect = mock_clients
        
        # Create multiple clients
        client1 = NerdGraphClient(api_key="key1", endpoint="https://api1.com")
        client2 = NerdGraphClient(api_key="key2", endpoint="https://api2.com")
        
        # Verify pools exist
        assert len(NerdGraphClient._connection_pools) == 2
        assert len(NerdGraphClient._pool_ref_counts) == 2
        
        # Close all pools
        await NerdGraphClient.close_all_pools()
        
        # Verify all pools are closed and cleared
        assert len(NerdGraphClient._connection_pools) == 0
        assert len(NerdGraphClient._pool_ref_counts) == 0
        mock_client1.aclose.assert_called_once()
        mock_client2.aclose.assert_called_once()
    
    async def test_concurrent_pool_access(self):
        """Test thread-safe concurrent access to pools"""
        api_key = "test-api-key-12345678"
        endpoint = "https://api.test.com/graphql"
        
        # Create multiple clients concurrently
        async def create_client():
            return NerdGraphClient(api_key=api_key, endpoint=endpoint)
        
        # Create 10 clients concurrently
        clients = await asyncio.gather(*[create_client() for _ in range(10)])
        
        pool_key = f"{endpoint}:{api_key[:8]}"
        
        # Check ref count is correct
        assert NerdGraphClient._pool_ref_counts[pool_key] == 10
        
        # Close all clients concurrently
        await asyncio.gather(*[client.close() for client in clients])
        
        # Check pool is cleaned up
        assert pool_key not in NerdGraphClient._connection_pools
        assert pool_key not in NerdGraphClient._pool_ref_counts
    
    async def test_pool_reuse_after_cleanup(self):
        """Test that pools can be recreated after cleanup"""
        api_key = "test-api-key-12345678"
        endpoint = "https://api.test.com/graphql"
        pool_key = f"{endpoint}:{api_key[:8]}"
        
        # Create and close a client
        client1 = NerdGraphClient(api_key=api_key, endpoint=endpoint)
        await client1.close()
        
        # Verify pool is cleaned up
        assert pool_key not in NerdGraphClient._connection_pools
        
        # Create new client with same credentials
        client2 = NerdGraphClient(api_key=api_key, endpoint=endpoint)
        
        # Verify new pool is created
        assert pool_key in NerdGraphClient._connection_pools
        assert NerdGraphClient._pool_ref_counts[pool_key] == 1
        
        # Clean up
        await client2.close()
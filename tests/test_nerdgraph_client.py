"""
Tests for NerdGraph client
"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
import json
import time

from core.nerdgraph_client import NerdGraphClient, QueryComplexityAnalyzer
from core.errors import NerdGraphError, ValidationError, RateLimitError, MCPError, ErrorCode


class TestQueryComplexityAnalyzer:
    """Test query complexity analysis"""
    
    def test_simple_query_complexity(self):
        """Test complexity analysis for simple query"""
        query = """
        {
            actor {
                user {
                    email
                }
            }
        }
        """
        
        result = QueryComplexityAnalyzer.analyze_complexity(query)
        
        assert result["depth"] == 3  # Three levels of nesting
        assert result["selections"] > 0
        assert not result["is_complex"]
    
    def test_complex_query_detection(self):
        """Test detection of complex queries"""
        # Create a deeply nested query
        query = "{" * 15 + "field" + "}" * 15
        
        result = QueryComplexityAnalyzer.analyze_complexity(query)
        
        assert result["depth"] > QueryComplexityAnalyzer.MAX_QUERY_DEPTH
        assert result["is_complex"]
    
    def test_many_selections_query(self):
        """Test query with many selections"""
        fields = [f"field{i}" for i in range(150)]
        query = f"""
        {{
            actor {{
                {', '.join(fields)}
            }}
        }}
        """
        
        result = QueryComplexityAnalyzer.analyze_complexity(query)
        
        assert result["selections"] > QueryComplexityAnalyzer.MAX_SELECTION_SETS
        assert result["is_complex"]


class TestNerdGraphClient:
    """Test NerdGraph client functionality"""
    
    @pytest.fixture
    async def client(self):
        """Create test client"""
        client = NerdGraphClient(
            api_key="test-key",
            endpoint="https://api.test.com/graphql",
            account_id="123456",
            enable_cache=False  # Disable cache for testing
        )
        yield client
        # Cleanup connection pools
        await NerdGraphClient.close_all_pools()
    
    @pytest.mark.asyncio
    async def test_client_initialization(self, client):
        """Test client initialization"""
        assert client.api_key == "test-key"
        assert client.endpoint == "https://api.test.com/graphql"
        assert client.account_id == "123456"
        assert client.timeout == 30.0
        assert client.request_count == 0
    
    @pytest.mark.asyncio
    async def test_successful_query(self, client):
        """Test successful GraphQL query"""
        mock_response = {
            "data": {
                "actor": {
                    "user": {"email": "test@example.com"}
                }
            }
        }
        
        # Mock httpx client
        with patch.object(client.client, 'post') as mock_post:
            mock_response_obj = AsyncMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = AsyncMock()
            mock_post.return_value = mock_response_obj
            
            result = await client.query("{ actor { user { email } } }")
            
            assert result == mock_response["data"]
            assert client.request_count == 1
            mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_query_with_variables(self, client):
        """Test query with variables"""
        query = """
        query($accountId: Int!) {
            actor {
                account(id: $accountId) {
                    name
                }
            }
        }
        """
        variables = {"accountId": 123456}
        
        mock_response = {
            "data": {
                "actor": {
                    "account": {"name": "Test Account"}
                }
            }
        }
        
        with patch.object(client.client, 'post') as mock_post:
            mock_response_obj = AsyncMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = AsyncMock()
            mock_post.return_value = mock_response_obj
            
            result = await client.query(query, variables)
            
            assert result == mock_response["data"]
            
            # Check request payload
            call_args = mock_post.call_args
            request_data = json.loads(call_args.kwargs['json'])
            assert request_data["query"] == query
            assert request_data["variables"] == variables
    
    @pytest.mark.asyncio
    async def test_graphql_errors(self, client):
        """Test handling of GraphQL errors"""
        mock_response = {
            "data": None,
            "errors": [
                {
                    "message": "Field 'invalid' doesn't exist",
                    "path": ["actor", "invalid"]
                }
            ]
        }
        
        with patch.object(client.client, 'post') as mock_post:
            mock_response_obj = AsyncMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = AsyncMock()
            mock_post.return_value = mock_response_obj
            
            with pytest.raises(NerdGraphError) as exc_info:
                await client.query("{ actor { invalid } }")
            
            assert "GraphQL query failed" in str(exc_info.value)
            assert exc_info.value.graphql_errors == mock_response["errors"]
    
    @pytest.mark.asyncio
    async def test_http_errors(self, client):
        """Test handling of HTTP errors"""
        # Test 401 Unauthorized
        with patch.object(client.client, 'post') as mock_post:
            mock_response_obj = AsyncMock()
            mock_response_obj.status_code = 401
            mock_response_obj.text = "Unauthorized"
            mock_response_obj.raise_for_status.side_effect = httpx.HTTPStatusError(
                "401 Unauthorized",
                request=MagicMock(),
                response=mock_response_obj
            )
            mock_post.return_value = mock_response_obj
            
            with pytest.raises(MCPError) as exc_info:
                await client.query("{ actor { user { email } } }")
            
            assert exc_info.value.code == ErrorCode.AUTHENTICATION_FAILED
            assert "Invalid API key" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_rate_limit_error(self, client):
        """Test rate limit handling"""
        with patch.object(client.client, 'post') as mock_post:
            mock_response_obj = AsyncMock()
            mock_response_obj.status_code = 429
            mock_response_obj.text = "Rate limit exceeded"
            mock_response_obj.raise_for_status.side_effect = httpx.HTTPStatusError(
                "429 Too Many Requests",
                request=MagicMock(),
                response=mock_response_obj
            )
            mock_post.return_value = mock_response_obj
            
            with pytest.raises(RateLimitError) as exc_info:
                await client.query("{ actor { user { email } } }")
            
            assert "rate limit exceeded" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_timeout_error(self, client):
        """Test timeout handling"""
        with patch.object(client.client, 'post') as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Request timed out")
            
            with pytest.raises(MCPError) as exc_info:
                await client.query("{ actor { user { email } } }")
            
            assert exc_info.value.code == ErrorCode.NERDGRAPH_TIMEOUT
            assert "timed out" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_execute_nrql(self, client):
        """Test NRQL query execution"""
        nrql = "SELECT count(*) FROM Transaction SINCE 1 hour ago"
        account_id = 123456
        
        mock_response = {
            "data": {
                "actor": {
                    "account": {
                        "nrql": {
                            "results": [{"count": 1000}],
                            "metadata": {
                                "facets": [],
                                "eventTypes": ["Transaction"],
                                "messages": [],
                                "timeWindow": {
                                    "begin": 1234567890,
                                    "end": 1234571490
                                }
                            }
                        }
                    }
                }
            }
        }
        
        with patch.object(client.client, 'post') as mock_post:
            mock_response_obj = AsyncMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = AsyncMock()
            mock_post.return_value = mock_response_obj
            
            result = await client.execute_nrql(nrql, account_id)
            
            assert result == mock_response["data"]
            
            # Check that NRQL was included in the query
            call_args = mock_post.call_args
            request_data = json.loads(call_args.kwargs['json'])
            assert request_data["variables"]["nrql"] == nrql
            assert request_data["variables"]["accountId"] == account_id
    
    @pytest.mark.asyncio
    async def test_batch_query(self, client):
        """Test batch query execution"""
        queries = {
            "user": ("{ actor { user { email } } }", None),
            "account": ("{ actor { account(id: $id) { name } } }", {"id": 123456})
        }
        
        mock_response = {
            "data": {
                "user": {
                    "actor": {
                        "user": {"email": "test@example.com"}
                    }
                },
                "account": {
                    "actor": {
                        "account": {"name": "Test Account"}
                    }
                }
            }
        }
        
        with patch.object(client.client, 'post') as mock_post:
            mock_response_obj = AsyncMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = AsyncMock()
            mock_post.return_value = mock_response_obj
            
            result = await client.batch_query(queries)
            
            assert result == mock_response["data"]
    
    @pytest.mark.asyncio
    async def test_get_metrics(self, client):
        """Test metrics retrieval"""
        # Make some requests to generate metrics
        with patch.object(client.client, 'post') as mock_post:
            mock_response_obj = AsyncMock()
            mock_response_obj.json.return_value = {"data": {}}
            mock_response_obj.raise_for_status = AsyncMock()
            mock_post.return_value = mock_response_obj
            
            # Successful request
            await client.query("{ test }")
            
            # Failed request
            mock_response_obj.json.return_value = {"errors": [{"message": "error"}]}
            try:
                await client.query("{ test }")
            except:
                pass
        
        metrics = client.get_metrics()
        
        assert metrics["request_count"] == 2
        assert metrics["error_count"] == 1
        assert metrics["error_rate"] == 0.5
        assert "average_latency_ms" in metrics
        assert "connection_pool_size" in metrics
    
    @pytest.mark.asyncio
    async def test_connection_pool_sharing(self):
        """Test that connection pools are shared between clients"""
        # Create two clients with same endpoint/key prefix
        client1 = NerdGraphClient(
            api_key="test-key-12345678",
            endpoint="https://api.test.com/graphql"
        )
        client2 = NerdGraphClient(
            api_key="test-key-12345678",
            endpoint="https://api.test.com/graphql"
        )
        
        # They should share the same connection pool
        assert client1.client is client2.client
        
        # Cleanup
        await NerdGraphClient.close_all_pools()
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager usage"""
        async with NerdGraphClient(
            api_key="test-key",
            endpoint="https://api.test.com/graphql"
        ) as client:
            assert client.api_key == "test-key"
        
        # Connection should be cleaned up
        # (actual close is a no-op due to connection pooling)
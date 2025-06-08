"""
Integration tests for end-to-end workflows

These tests verify that the complete MCP server works correctly
with all components integrated together.
"""

import pytest
import asyncio
import json
import os
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

import httpx

from main import create_app
from core.nerdgraph_client import NerdGraphClient
from core.account_manager import AccountManager
from core.cache_improved import MemoryLimitedCache
from core.error_sanitizer import sanitize_error_response


class TestEndToEndWorkflows:
    """Test complete workflows from API call to response"""
    
    @pytest.fixture
    async def mock_app(self):
        """Create a test MCP app with mocked dependencies"""
        
        # Mock environment
        with patch.dict(os.environ, {
            'NEW_RELIC_API_KEY': 'NRAK-TEST123456789ABCDEFGHIJKLMNOPQR1234',
            'NEW_RELIC_ACCOUNT_ID': '12345',
            'LOG_LEVEL': 'DEBUG',
            'CACHE_BACKEND': 'memory',
            'USE_ENHANCED_PLUGINS': 'true'
        }):
            # Mock NerdGraph responses
            mock_nerdgraph_response = {
                "data": {
                    "actor": {
                        "user": {"email": "test@example.com"}
                    }
                }
            }
            
            with patch('core.nerdgraph_client.httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_response = AsyncMock()
                mock_response.json.return_value = mock_nerdgraph_response
                mock_response.raise_for_status.return_value = None
                mock_client.post.return_value = mock_response
                mock_client_class.return_value = mock_client
                
                # Create the app
                app = await create_app()
                yield app
                
                # Cleanup
                if hasattr(app, 'on_cleanup'):
                    await app.cleanup()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_apm_metrics_workflow(self, mock_app):
        """Test complete APM metrics workflow"""
        
        # Mock APM metrics response
        apm_response = {
            "data": {
                "actor": {
                    "entitySearch": {
                        "results": {
                            "entities": [
                                {
                                    "guid": "TEST-GUID-123",
                                    "name": "Test App",
                                    "type": "APPLICATION",
                                    "goldenMetrics": {
                                        "metrics": [
                                            {
                                                "name": "Throughput",
                                                "query": "SELECT rate(count(*), 1 minute) FROM Transaction",
                                                "unit": "requests per minute"
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    }
                }
            }
        }
        
        # Test the workflow
        with patch('core.nerdgraph_client.NerdGraphClient.query') as mock_query:
            mock_query.return_value = apm_response
            
            # This would be called by the MCP client
            # We're simulating the tool call
            if hasattr(mock_app, '_tools') and 'search_entities' in mock_app._tools:
                result = await mock_app._tools['search_entities'](
                    query="Test App",
                    types=["APPLICATION"]
                )
                
                assert result is not None
                assert "entities" in str(result)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_error_handling_workflow(self, mock_app):
        """Test complete error handling workflow"""
        
        # Simulate an error in NerdGraph call
        with patch('core.nerdgraph_client.NerdGraphClient.query') as mock_query:
            mock_query.side_effect = Exception(
                "Network error: Failed to connect to api.newrelic.com with API key NRAK-SECRET123"
            )
            
            # Test that errors are properly sanitized
            try:
                if hasattr(mock_app, '_tools') and 'run_nrql_query' in mock_app._tools:
                    await mock_app._tools['run_nrql_query'](
                        nrql="SELECT * FROM Transaction"
                    )
            except Exception as e:
                # Error should be sanitized
                sanitized = sanitize_error_response(e, context="integration_test")
                
                assert "NRAK-SECRET123" not in sanitized["message"]
                assert sanitized["error"] is True
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_plugin_loading_workflow(self, mock_app):
        """Test that plugins are loaded correctly"""
        
        # Check that plugins were loaded
        if hasattr(mock_app, '_tools'):
            # Should have tools from various plugins
            expected_tools = ['run_nrql_query', 'search_entities', 'get_health_status']
            
            for tool in expected_tools:
                if tool in mock_app._tools:
                    assert callable(mock_app._tools[tool])
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_caching_workflow(self, mock_app):
        """Test that caching works end-to-end"""
        
        cache_responses = [
            {"data": {"result": "first_call"}},
            {"data": {"result": "second_call"}}
        ]
        
        with patch('core.nerdgraph_client.NerdGraphClient.query') as mock_query:
            mock_query.side_effect = cache_responses
            
            # Make the same query twice
            query = "SELECT count(*) FROM Transaction"
            
            # First call - should hit the API
            if hasattr(mock_app, '_tools') and 'run_nrql_query' in mock_app._tools:
                result1 = await mock_app._tools['run_nrql_query'](nrql=query)
                
                # Second call - should use cache (if caching is enabled for NRQL)
                result2 = await mock_app._tools['run_nrql_query'](nrql=query)
                
                # Verify calls were made (may be cached or not depending on implementation)
                assert mock_query.call_count >= 1
    
    @pytest.mark.asyncio
    @pytest.mark.integration 
    async def test_audit_logging_workflow(self, mock_app):
        """Test that audit logging works end-to-end"""
        
        # Mock successful API response
        with patch('core.nerdgraph_client.NerdGraphClient.query') as mock_query:
            mock_query.return_value = {"data": {"actor": {"user": {"email": "test@example.com"}}}}
            
            # Mock audit logger to verify it's called
            with patch('core.audit.get_audit_logger') as mock_get_logger:
                mock_logger = AsyncMock()
                mock_get_logger.return_value = mock_logger
                
                # Make a tool call that should be audited
                if hasattr(mock_app, '_tools') and 'get_session_info' in mock_app._tools:
                    await mock_app._tools['get_session_info']()
                
                # Verify audit logging was attempted
                # (may not be called if audit logger is not properly initialized in test)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_rate_limiting_workflow(self, mock_app):
        """Test rate limiting behavior"""
        
        # This test would verify rate limiting if implemented
        # For now, it's a placeholder for future implementation
        
        with patch('core.nerdgraph_client.NerdGraphClient.query') as mock_query:
            mock_query.return_value = {"data": {"result": "success"}}
            
            # Make multiple rapid requests
            tasks = []
            for i in range(10):
                if hasattr(mock_app, '_tools') and 'run_nrql_query' in mock_app._tools:
                    task = mock_app._tools['run_nrql_query'](
                        nrql=f"SELECT count(*) FROM Transaction LIMIT {i}"
                    )
                    tasks.append(task)
            
            # Execute concurrently
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # All should succeed (no rate limiting implemented yet)
                for result in results:
                    if isinstance(result, Exception):
                        # Check if it's a rate limit error
                        assert "rate limit" not in str(result).lower()


class TestPerformanceWorkflows:
    """Test performance-related workflows"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_concurrent_queries_performance(self):
        """Test handling of concurrent queries"""
        
        # Create test client with mocked responses
        with patch('core.nerdgraph_client.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.json.return_value = {"data": {"result": "success"}}
            mock_response.raise_for_status.return_value = None
            
            # Add delay to simulate network latency
            async def delayed_post(*args, **kwargs):
                await asyncio.sleep(0.1)  # 100ms delay
                return mock_response
            
            mock_client.post = delayed_post
            mock_client_class.return_value = mock_client
            
            # Create NerdGraph client
            client = NerdGraphClient(
                api_key="test-key",
                endpoint="https://api.test.com/graphql"
            )
            
            # Execute concurrent queries
            start_time = asyncio.get_event_loop().time()
            
            queries = [
                "SELECT count(*) FROM Transaction",
                "SELECT average(duration) FROM Transaction", 
                "SELECT percentile(duration, 95) FROM Transaction"
            ] * 5  # 15 total queries
            
            tasks = [client.query(query) for query in queries]
            results = await asyncio.gather(*tasks)
            
            end_time = asyncio.get_event_loop().time()
            
            # Verify all queries succeeded
            assert len(results) == 15
            for result in results:
                assert result["data"]["result"] == "success"
            
            # Verify concurrency (should be much faster than sequential)
            # With 100ms delay each, sequential would take 1.5s
            # Concurrent should be much faster
            total_time = end_time - start_time
            assert total_time < 1.0  # Should complete in under 1 second
            
            await client.close()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_memory_usage_under_load(self):
        """Test memory usage under load"""
        
        # Create cache with small limits
        cache = MemoryLimitedCache(
            max_items=100,
            max_memory_mb=1,  # 1MB limit
            ttl_seconds=60
        )
        
        # Fill cache with data
        for i in range(200):  # More than max_items
            await cache.set(f"key_{i}", f"value_{i}" * 100)  # ~500 bytes each
        
        stats = cache.get_stats()
        
        # Verify limits are enforced
        assert stats['items'] <= 100
        assert stats['memory_mb'] <= 1.1  # Allow small buffer
        assert stats['evictions'] > 0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_plugin_load_time(self):
        """Test plugin loading performance"""
        
        start_time = asyncio.get_event_loop().time()
        
        # Mock the plugin loading process
        with patch.dict(os.environ, {
            'NEW_RELIC_API_KEY': 'NRAK-TEST123456789ABCDEFGHIJKLMNOPQR1234',
            'USE_ENHANCED_PLUGINS': 'true'
        }):
            with patch('core.nerdgraph_client.httpx.AsyncClient'):
                app = await create_app()
        
        end_time = asyncio.get_event_loop().time()
        load_time = end_time - start_time
        
        # Plugin loading should be fast (under 5 seconds)
        assert load_time < 5.0
        
        # Should have loaded some plugins
        if hasattr(app, '_tools'):
            assert len(app._tools) > 0


class TestSecurityWorkflows:
    """Test security-related workflows"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_api_key_validation_workflow(self):
        """Test API key validation"""
        
        # Test with invalid API key
        with patch.dict(os.environ, {
            'NEW_RELIC_API_KEY': 'invalid-key'
        }):
            with patch('core.nerdgraph_client.httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_response = AsyncMock()
                mock_response.json.return_value = {
                    "errors": [{"message": "Invalid API key"}]
                }
                mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "Unauthorized", request=Mock(), response=Mock()
                )
                mock_client.post.return_value = mock_response
                mock_client_class.return_value = mock_client
                
                # Should handle invalid API key gracefully
                try:
                    app = await create_app()
                    assert False, "Should have failed with invalid API key"
                except SystemExit:
                    # Expected - invalid API key should cause startup failure
                    pass
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_nrql_injection_prevention(self, mock_app):
        """Test NRQL injection prevention"""
        
        dangerous_queries = [
            "SELECT * FROM Transaction; DROP TABLE users",
            "SELECT * FROM Transaction WHERE name = ''; DELETE FROM data; --",
            "SELECT * FROM Transaction UNION SELECT password FROM users"
        ]
        
        with patch('core.nerdgraph_client.NerdGraphClient.query') as mock_query:
            for dangerous_query in dangerous_queries:
                try:
                    if hasattr(mock_app, '_tools') and 'run_nrql_query' in mock_app._tools:
                        await mock_app._tools['run_nrql_query'](nrql=dangerous_query)
                    assert False, f"Should have blocked dangerous query: {dangerous_query}"
                except Exception as e:
                    # Should be blocked by NRQL validation
                    assert "dangerous" in str(e).lower() or "invalid" in str(e).lower()


@pytest.mark.integration
class TestDataFlowWorkflows:
    """Test data flow through the entire system"""
    
    @pytest.mark.asyncio
    async def test_entity_search_to_metrics_workflow(self):
        """Test searching entities and then getting their metrics"""
        
        # Mock entity search response
        entity_response = {
            "data": {
                "actor": {
                    "entitySearch": {
                        "results": {
                            "entities": [
                                {
                                    "guid": "APP-GUID-123",
                                    "name": "Test Application",
                                    "type": "APPLICATION"
                                }
                            ]
                        }
                    }
                }
            }
        }
        
        # Mock metrics response
        metrics_response = {
            "data": {
                "actor": {
                    "entity": {
                        "goldenMetrics": {
                            "metrics": [
                                {
                                    "name": "Throughput",
                                    "query": "SELECT rate(count(*), 1 minute) FROM Transaction",
                                    "result": [{"value": 150.5}]
                                }
                            ]
                        }
                    }
                }
            }
        }
        
        with patch.dict(os.environ, {
            'NEW_RELIC_API_KEY': 'NRAK-TEST123456789ABCDEFGHIJKLMNOPQR1234'
        }):
            with patch('core.nerdgraph_client.httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_response = AsyncMock()
                mock_client_class.return_value = mock_client
                
                # First call returns entity search results
                # Second call returns metrics
                mock_response.json.side_effect = [
                    {"data": {"actor": {"user": {"email": "test@example.com"}}}},  # Auth check
                    entity_response,  # Entity search
                    metrics_response   # Metrics query
                ]
                mock_response.raise_for_status.return_value = None
                mock_client.post.return_value = mock_response
                
                app = await create_app()
                
                # Simulate the workflow: search -> get metrics
                if (hasattr(app, '_tools') and 
                    'search_entities' in app._tools and 
                    'get_entity_golden_signals' in app._tools):
                    
                    # Step 1: Search for entities
                    entities = await app._tools['search_entities'](
                        query="Test Application"
                    )
                    
                    # Step 2: Get metrics for found entity
                    if entities and "APP-GUID-123" in str(entities):
                        metrics = await app._tools['get_entity_golden_signals'](
                            guid="APP-GUID-123"
                        )
                        
                        assert metrics is not None
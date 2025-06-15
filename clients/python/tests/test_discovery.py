"""Tests for the discovery service."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from newrelic_uds.models import (
    ListSchemasOptions,
    ListSchemasResponse,
    Schema,
    QualityMetrics,
)


class TestAsyncDiscoveryService:
    """Tests for the async discovery service."""
    
    @pytest.mark.asyncio
    async def test_list_schemas(self, async_client, sample_schema):
        """Test listing schemas."""
        response_data = {
            "schemas": [sample_schema],
            "metadata": {
                "total_schemas": 1,
                "execution_time": "100ms",
                "cache_hit": False,
            },
        }
        
        with patch.object(
            async_client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = ListSchemasResponse(**response_data)
            
            # Test without options
            result = await async_client.discovery.list_schemas()
            mock_get.assert_called_with(
                "/discovery/schemas",
                params={},
                response_model=ListSchemasResponse,
            )
            
            # Test with options
            options = ListSchemasOptions(
                event_type="Transaction",
                min_record_count=1000,
                max_schemas=10,
                sort_by="recordCount",
                include_metadata=True,
            )
            
            result = await async_client.discovery.list_schemas(options)
            mock_get.assert_called_with(
                "/discovery/schemas",
                params={
                    "eventType": "Transaction",
                    "minRecordCount": "1000",
                    "maxSchemas": "10",
                    "sortBy": "recordCount",
                    "includeMetadata": "true",
                },
                response_model=ListSchemasResponse,
            )
    
    @pytest.mark.asyncio
    async def test_get_schema(self, async_client, sample_schema):
        """Test getting a specific schema."""
        with patch.object(
            async_client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = Schema(**sample_schema)
            
            result = await async_client.discovery.get_schema("Transaction")
            mock_get.assert_called_with(
                "/discovery/schemas/Transaction",
                response_model=Schema,
            )
            
            # Test with special characters in name
            await async_client.discovery.get_schema("My Schema/With+Chars")
            mock_get.assert_called_with(
                "/discovery/schemas/My%20Schema%2FWith%2BChars",
                response_model=Schema,
            )
    
    @pytest.mark.asyncio
    async def test_analyze_quality(self, async_client):
        """Test analyzing schema quality."""
        quality_data = {
            "overall_score": 0.85,
            "completeness": 0.9,
            "consistency": 0.85,
            "validity": 0.8,
            "uniqueness": 0.85,
        }
        
        with patch.object(
            async_client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = QualityMetrics(**quality_data)
            
            result = await async_client.discovery.analyze_quality("Transaction")
            mock_post.assert_called_with(
                "/discovery/schemas/Transaction/analyze",
                response_model=QualityMetrics,
            )
            assert result.overall_score == 0.85
    
    @pytest.mark.asyncio
    async def test_compare_schemas(self, async_client):
        """Test comparing two schemas."""
        comparison_data = {
            "differences": [
                {
                    "type": "attribute_added",
                    "attribute": "newField",
                    "details": {"dataType": "string"},
                }
            ],
            "similarity": 0.95,
        }
        
        with patch.object(
            async_client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = comparison_data
            
            result = await async_client.discovery.compare_schemas(
                "Transaction", "TransactionV2"
            )
            mock_post.assert_called_with(
                "/discovery/schemas/compare",
                json={"schema1": "Transaction", "schema2": "TransactionV2"},
            )
            assert result["similarity"] == 0.95
    
    @pytest.mark.asyncio
    async def test_get_recommendations(self, async_client):
        """Test getting recommendations."""
        recommendations_data = {
            "recommendations": [
                {
                    "type": "add_index",
                    "priority": "high",
                    "description": "Add index on timestamp",
                    "impact": "Improve query performance by 50%",
                }
            ]
        }
        
        with patch.object(
            async_client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = recommendations_data
            
            # Without event type
            result = await async_client.discovery.get_recommendations()
            mock_get.assert_called_with(
                "/discovery/recommendations", params=None
            )
            
            # With event type
            result = await async_client.discovery.get_recommendations("Transaction")
            mock_get.assert_called_with(
                "/discovery/recommendations", params={"eventType": "Transaction"}
            )


class TestSyncDiscoveryService:
    """Tests for the sync discovery service."""
    
    def test_list_schemas(self, sync_client, sample_schema):
        """Test listing schemas."""
        response_data = {
            "schemas": [sample_schema],
            "metadata": {
                "total_schemas": 1,
                "execution_time": "100ms",
                "cache_hit": False,
            },
        }
        
        with patch.object(sync_client, "get") as mock_get:
            mock_get.return_value = ListSchemasResponse(**response_data)
            
            # Test without options
            result = sync_client.discovery.list_schemas()
            mock_get.assert_called_with(
                "/discovery/schemas",
                params={},
                response_model=ListSchemasResponse,
            )
            
            # Test with options
            options = ListSchemasOptions(
                event_type="Transaction",
                min_record_count=1000,
                include_metadata=True,
            )
            
            result = sync_client.discovery.list_schemas(options)
            assert mock_get.called
    
    def test_get_schema(self, sync_client, sample_schema):
        """Test getting a specific schema."""
        with patch.object(sync_client, "get") as mock_get:
            mock_get.return_value = Schema(**sample_schema)
            
            result = sync_client.discovery.get_schema("Transaction")
            mock_get.assert_called_with(
                "/discovery/schemas/Transaction",
                response_model=Schema,
            )
            assert result.name == "Transaction"
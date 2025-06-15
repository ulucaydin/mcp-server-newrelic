"""Tests for query generation components"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from intelligence.query.base import (
    QueryIntent, QueryContext, QueryType, IntentType, 
    TimeRange, TimeRangeType, QueryEntity, AggregationType,
    Filter, FilterOperator, QueryResult
)
from intelligence.query.intent_parser import IntentParser
from intelligence.query.nrql_builder import NRQLBuilder
from intelligence.query.query_optimizer import QueryOptimizer
from intelligence.query.query_generator import QueryGenerator


class TestIntentParser:
    """Test natural language intent parsing"""
    
    @pytest.fixture
    def parser(self):
        return IntentParser()
    
    def test_parse_simple_query(self, parser):
        """Test parsing simple queries"""
        query = "Show me average response time"
        intent = parser.parse(query)
        
        assert intent.intent_type == IntentType.EXPLORE
        assert intent.query_type == QueryType.SELECT
        assert len(intent.entities) >= 1
        assert intent.entities[0].name == 'response_time'
        assert intent.entities[0].aggregation == AggregationType.AVERAGE
    
    def test_parse_time_range(self, parser):
        """Test time range parsing"""
        queries_and_ranges = [
            ("Show me errors in the last hour", TimeRangeType.LAST_HOUR),
            ("What happened yesterday", TimeRangeType.LAST_DAY),
            ("Metrics for last week", TimeRangeType.LAST_WEEK),
            ("Last 30 days performance", TimeRangeType.LAST_MONTH),
            ("This quarter's data", TimeRangeType.LAST_QUARTER)
        ]
        
        for query, expected_range in queries_and_ranges:
            intent = parser.parse(query)
            assert intent.time_range.type == expected_range
    
    def test_parse_aggregations(self, parser):
        """Test aggregation parsing"""
        queries_and_aggs = [
            ("Count of errors", AggregationType.COUNT),
            ("Sum of transactions", AggregationType.SUM),
            ("Average response time", AggregationType.AVERAGE),
            ("Maximum CPU usage", AggregationType.MAX),
            ("Minimum latency", AggregationType.MIN),
            ("95th percentile of duration", AggregationType.PERCENTILE)
        ]
        
        for query, expected_agg in queries_and_aggs:
            intent = parser.parse(query)
            assert len(intent.entities) >= 1
            assert intent.entities[0].aggregation == expected_agg
    
    def test_parse_filters(self, parser):
        """Test filter parsing"""
        query = "Show errors where service is 'api' and status > 400"
        intent = parser.parse(query)
        
        assert len(intent.filters) >= 2
        
        # Check service filter
        service_filter = next((f for f in intent.filters if f.field == 'service'), None)
        assert service_filter is not None
        assert service_filter.operator == FilterOperator.EQUALS
        assert service_filter.value == 'api'
        
        # Check status filter
        status_filter = next((f for f in intent.filters if f.field == 'status'), None)
        assert status_filter is not None
        assert status_filter.operator == FilterOperator.GREATER_THAN
        assert status_filter.value == 400
    
    def test_parse_group_by(self, parser):
        """Test group by parsing"""
        queries = [
            "Average response time by service",
            "Count errors grouped by host",
            "Show metrics per application"
        ]
        
        for query in queries:
            intent = parser.parse(query)
            assert intent.query_type == QueryType.FACET
            assert len(intent.group_by) >= 1
    
    def test_parse_complex_query(self, parser):
        """Test parsing complex query"""
        query = """
        Show me the 95th percentile response time and error rate 
        for the web service in production 
        over the last 24 hours grouped by endpoint
        """
        
        intent = parser.parse(query)
        
        # Check intent type
        assert intent.intent_type in [IntentType.MONITOR, IntentType.ANALYZE]
        
        # Check entities
        assert len(intent.entities) >= 2
        entity_names = {e.name for e in intent.entities}
        assert 'response_time' in entity_names or 'duration' in entity_names
        assert 'error_rate' in entity_names or 'errors' in entity_names
        
        # Check filters
        assert len(intent.filters) >= 1
        
        # Check time range
        assert intent.time_range.type == TimeRangeType.LAST_DAY
        
        # Check grouping
        assert intent.query_type == QueryType.FACET
        assert 'endpoint' in intent.group_by
    
    def test_intent_confidence(self, parser):
        """Test confidence scoring"""
        # Clear query should have high confidence
        clear_query = "Show me average response time for api service"
        intent1 = parser.parse(clear_query)
        assert intent1.confidence > 0.8
        
        # Ambiguous query should have lower confidence
        ambiguous_query = "things stuff data"
        intent2 = parser.parse(ambiguous_query)
        assert intent2.confidence < 0.5
    
    def test_troubleshooting_intent(self, parser):
        """Test troubleshooting intent detection"""
        queries = [
            "Why are there so many errors?",
            "What's causing the high latency?",
            "Debug slow queries",
            "Investigate CPU spikes"
        ]
        
        for query in queries:
            intent = parser.parse(query)
            assert intent.intent_type == IntentType.TROUBLESHOOT


class TestNRQLBuilder:
    """Test NRQL query building"""
    
    @pytest.fixture
    def builder(self):
        return NRQLBuilder()
    
    @pytest.fixture
    def simple_intent(self):
        """Create a simple query intent"""
        return QueryIntent(
            intent_type=IntentType.EXPLORE,
            query_type=QueryType.SELECT,
            entities=[
                QueryEntity(
                    name="duration",
                    aggregation=AggregationType.AVERAGE
                )
            ],
            event_types=["Transaction"],
            filters=[],
            time_range=TimeRange(type=TimeRangeType.LAST_HOUR),
            raw_query="Show average duration"
        )
    
    def test_build_simple_select(self, builder, simple_intent):
        """Test building simple SELECT query"""
        nrql = builder.build(simple_intent)
        
        assert "SELECT" in nrql
        assert "average(duration)" in nrql
        assert "FROM Transaction" in nrql
        assert "SINCE 1 hour ago" in nrql
    
    def test_build_with_filters(self, builder):
        """Test building query with WHERE clause"""
        intent = QueryIntent(
            intent_type=IntentType.MONITOR,
            query_type=QueryType.SELECT,
            entities=[QueryEntity(name="count", aggregation=AggregationType.COUNT)],
            event_types=["Transaction"],
            filters=[
                Filter(field="appName", operator=FilterOperator.EQUALS, value="production"),
                Filter(field="duration", operator=FilterOperator.GREATER_THAN, value=1000)
            ],
            time_range=TimeRange(type=TimeRangeType.LAST_DAY),
            raw_query="Count transactions in production with duration > 1000"
        )
        
        nrql = builder.build(intent)
        
        assert "WHERE" in nrql
        assert "appName = 'production'" in nrql
        assert "duration > 1000" in nrql
        assert "AND" in nrql
    
    def test_build_facet_query(self, builder):
        """Test building FACET query"""
        intent = QueryIntent(
            intent_type=IntentType.ANALYZE,
            query_type=QueryType.FACET,
            entities=[QueryEntity(name="duration", aggregation=AggregationType.AVERAGE)],
            event_types=["Transaction"],
            filters=[],
            group_by=["service", "host"],
            time_range=TimeRange(type=TimeRangeType.LAST_HOUR),
            raw_query="Average duration by service and host"
        )
        
        nrql = builder.build(intent)
        
        assert "FACET" in nrql
        assert "service" in nrql
        assert "host" in nrql
    
    def test_build_timeseries_query(self, builder):
        """Test building TIMESERIES query"""
        intent = QueryIntent(
            intent_type=IntentType.MONITOR,
            query_type=QueryType.TIMESERIES,
            entities=[QueryEntity(name="count", aggregation=AggregationType.COUNT)],
            event_types=["Transaction"],
            filters=[],
            time_range=TimeRange(type=TimeRangeType.LAST_DAY),
            raw_query="Transaction count over time"
        )
        
        nrql = builder.build(intent)
        
        assert "TIMESERIES" in nrql
        assert "SELECT count(*)" in nrql
    
    def test_build_percentile_query(self, builder):
        """Test building percentile query"""
        intent = QueryIntent(
            intent_type=IntentType.ANALYZE,
            query_type=QueryType.PERCENTILE,
            entities=[
                QueryEntity(
                    name="duration",
                    aggregation=AggregationType.PERCENTILE,
                    percentile_value=95
                )
            ],
            event_types=["Transaction"],
            filters=[],
            time_range=TimeRange(type=TimeRangeType.LAST_HOUR),
            raw_query="95th percentile duration"
        )
        
        nrql = builder.build(intent)
        
        assert "percentile(duration, 95)" in nrql
    
    def test_build_multiple_aggregations(self, builder):
        """Test building query with multiple aggregations"""
        intent = QueryIntent(
            intent_type=IntentType.MONITOR,
            query_type=QueryType.SELECT,
            entities=[
                QueryEntity(name="duration", aggregation=AggregationType.AVERAGE),
                QueryEntity(name="duration", aggregation=AggregationType.MAX),
                QueryEntity(name="count", aggregation=AggregationType.COUNT)
            ],
            event_types=["Transaction"],
            filters=[],
            time_range=TimeRange(type=TimeRangeType.LAST_HOUR),
            raw_query="Average and max duration with count"
        )
        
        nrql = builder.build(intent)
        
        assert "average(duration)" in nrql
        assert "max(duration)" in nrql
        assert "count(*)" in nrql
    
    def test_build_with_limit(self, builder):
        """Test building query with LIMIT"""
        intent = QueryIntent(
            intent_type=IntentType.EXPLORE,
            query_type=QueryType.SELECT,
            entities=[QueryEntity(name="*", aggregation=None)],
            event_types=["Transaction"],
            filters=[],
            time_range=TimeRange(type=TimeRangeType.LAST_HOUR),
            limit=100,
            raw_query="Show transactions"
        )
        
        nrql = builder.build(intent)
        
        assert "LIMIT 100" in nrql
    
    def test_escape_special_characters(self, builder):
        """Test escaping special characters in values"""
        intent = QueryIntent(
            intent_type=IntentType.EXPLORE,
            query_type=QueryType.SELECT,
            entities=[QueryEntity(name="count", aggregation=AggregationType.COUNT)],
            event_types=["Transaction"],
            filters=[
                Filter(field="message", operator=FilterOperator.CONTAINS, value="error's")
            ],
            time_range=TimeRange(type=TimeRangeType.LAST_HOUR),
            raw_query="Count errors"
        )
        
        nrql = builder.build(intent)
        
        # Should escape quotes properly
        assert "error\\'s" in nrql or 'error\'s' in nrql


class TestQueryOptimizer:
    """Test query optimization"""
    
    @pytest.fixture
    def optimizer(self):
        return QueryOptimizer({'performance_mode': 'balanced'})
    
    @pytest.fixture
    def sample_intent(self):
        return QueryIntent(
            intent_type=IntentType.ANALYZE,
            query_type=QueryType.SELECT,
            entities=[QueryEntity(name="duration", aggregation=AggregationType.AVERAGE)],
            event_types=["Transaction"],
            filters=[],
            time_range=TimeRange(type=TimeRangeType.LAST_MONTH),
            raw_query="Average duration last month"
        )
    
    @pytest.fixture
    def sample_context(self):
        return QueryContext(
            available_schemas=[
                {
                    'name': 'Transaction',
                    'records_per_hour': 1_000_000,
                    'common_facets': ['appName', 'host', 'service']
                }
            ],
            cost_constraints={'max_cost': 100.0}
        )
    
    def test_cost_optimization(self, sample_intent, sample_context):
        """Test cost-optimized query"""
        optimizer = QueryOptimizer({'performance_mode': 'cost'})
        original_nrql = "SELECT average(duration) FROM Transaction SINCE 1 month ago"
        
        optimized_nrql, metadata = optimizer.optimize(
            original_nrql, sample_intent, sample_context
        )
        
        # Should reduce time range or add sampling
        assert metadata['cost_reduction'] > 0
        assert any(opt in metadata['optimizations_applied'] for opt in [
            'reduced_time_range_to_SINCE 1 week ago',
            'reduced_time_range_to_SINCE 2 weeks ago',
            'added_sampling_0.1',
            'added_sampling_0.01'
        ])
    
    def test_speed_optimization(self, sample_intent, sample_context):
        """Test speed-optimized query"""
        optimizer = QueryOptimizer({'performance_mode': 'speed'})
        original_nrql = "SELECT average(duration) FROM Transaction WHERE appName = 'prod' SINCE 1 day ago"
        
        # Modify intent to have filters
        sample_intent.filters = [
            Filter(field="appName", operator=FilterOperator.EQUALS, value="prod")
        ]
        
        optimized_nrql, metadata = optimizer.optimize(
            original_nrql, sample_intent, sample_context
        )
        
        # Should add LIMIT if not present
        if 'LIMIT' not in original_nrql:
            assert 'LIMIT' in optimized_nrql
            assert 'added_limit' in str(metadata['optimizations_applied'])
    
    def test_balanced_optimization(self, optimizer, sample_intent, sample_context):
        """Test balanced optimization"""
        original_nrql = "SELECT average(duration) FROM Transaction SINCE 1 month ago"
        
        optimized_nrql, metadata = optimizer.optimize(
            original_nrql, sample_intent, sample_context
        )
        
        # Should apply moderate optimizations
        assert len(metadata['optimizations_applied']) > 0
        assert metadata['optimization_mode'] == 'balanced'
    
    def test_timeseries_optimization(self, optimizer):
        """Test TIMESERIES query optimization"""
        intent = QueryIntent(
            intent_type=IntentType.MONITOR,
            query_type=QueryType.TIMESERIES,
            entities=[QueryEntity(name="count", aggregation=AggregationType.COUNT)],
            event_types=["Transaction"],
            filters=[],
            time_range=TimeRange(type=TimeRangeType.LAST_WEEK),
            raw_query="Count over time"
        )
        
        original_nrql = "SELECT count(*) FROM Transaction TIMESERIES SINCE 1 week ago"
        
        optimized_nrql, metadata = optimizer.optimize(
            original_nrql, intent, QueryContext()
        )
        
        # Should optimize bucket size
        assert 'TIMESERIES 1 hour' in optimized_nrql or 'TIMESERIES 1 day' in optimized_nrql
        assert 'set_timeseries_bucket' in str(metadata['optimizations_applied'])
    
    def test_expensive_aggregation_replacement(self):
        """Test replacement of expensive aggregations"""
        optimizer = QueryOptimizer({
            'performance_mode': 'cost',
            'aggressive': True
        })
        
        intent = QueryIntent(
            intent_type=IntentType.ANALYZE,
            query_type=QueryType.SELECT,
            entities=[
                QueryEntity(name="userId", aggregation=AggregationType.UNIQUE_COUNT)
            ],
            event_types=["PageView"],
            filters=[],
            time_range=TimeRange(type=TimeRangeType.LAST_DAY),
            raw_query="Unique users"
        )
        
        original_nrql = "SELECT uniqueCount(userId) FROM PageView SINCE 1 day ago"
        
        optimized_nrql, metadata = optimizer.optimize(
            original_nrql, intent, QueryContext()
        )
        
        # Might replace uniqueCount with approximateCount
        if 'approximateCount' in optimized_nrql:
            assert 'replaced_uniqueCount_with_approximateCount' in str(metadata['optimizations_applied'])
    
    def test_validation_prevents_breaking_changes(self, optimizer, sample_intent, sample_context):
        """Test that optimization doesn't break query semantics"""
        original_nrql = "SELECT count(*) FROM Transaction WHERE appName = 'critical' SINCE 1 hour ago"
        
        # Add critical filter to intent
        sample_intent.filters = [
            Filter(field="appName", operator=FilterOperator.EQUALS, value="critical")
        ]
        sample_intent.event_types = ["Transaction"]
        
        optimized_nrql, metadata = optimizer.optimize(
            original_nrql, sample_intent, sample_context
        )
        
        # Should preserve critical elements
        assert "FROM Transaction" in optimized_nrql
        assert "appName = 'critical'" in optimized_nrql


class TestQueryGenerator:
    """Test the main query generator"""
    
    @pytest.fixture
    def generator(self):
        return QueryGenerator()
    
    def test_generate_simple_query(self, generator):
        """Test generating simple query"""
        result = generator.generate("Show me average response time")
        
        assert result.nrql != ""
        assert "SELECT" in result.nrql
        assert "average" in result.nrql.lower()
        assert result.confidence > 0.5
    
    def test_generate_with_context(self, generator):
        """Test generating query with context"""
        context = QueryContext(
            available_schemas=[
                {
                    'name': 'APICall',
                    'records_per_hour': 100_000,
                    'common_facets': ['endpoint', 'method', 'status']
                }
            ]
        )
        
        result = generator.generate(
            "Show API errors by endpoint",
            context=context
        )
        
        assert "APICall" in result.nrql
        assert "endpoint" in result.nrql
        assert result.estimated_cost is not None
    
    def test_query_suggestions(self, generator):
        """Test query suggestions"""
        suggestions = generator.suggest_queries("Show me")
        
        assert len(suggestions) > 0
        assert all(s.startswith("Show me") for s in suggestions)
    
    def test_query_explanation(self, generator):
        """Test NRQL query explanation"""
        nrql = "SELECT average(duration) FROM Transaction WHERE appName = 'prod' SINCE 1 hour ago FACET service"
        
        explanation = generator.explain_query(nrql)
        
        assert 'summary' in explanation
        assert 'components' in explanation
        assert 'Transaction' in explanation['data_source']
        assert 'hour ago' in explanation['time_range']
        assert len(explanation['filters']) > 0
        assert len(explanation['grouping']) > 0
    
    def test_caching(self, generator):
        """Test query result caching"""
        query = "Show me errors in the last hour"
        
        # First call
        result1 = generator.generate(query)
        assert not result1.metadata.get('cache_hit', False)
        
        # Second call should hit cache
        result2 = generator.generate(query)
        assert result2.metadata.get('cache_hit', False)
        assert result1.nrql == result2.nrql
    
    def test_batch_generation(self, generator):
        """Test batch query generation"""
        queries = [
            "Show average response time",
            "Count errors by service",
            "CPU usage over time"
        ]
        
        results = generator.generate_batch(queries)
        
        assert len(results) == 3
        assert all(r.nrql != "" for r in results)
        assert all(r.confidence > 0 for r in results)
    
    def test_error_handling(self, generator):
        """Test error handling"""
        # Empty query
        result = generator.generate("")
        assert result.nrql == ""
        assert len(result.warnings) > 0
        
        # Nonsensical query
        result = generator.generate("xyz abc 123")
        assert result.confidence < 0.5
    
    def test_warnings_and_suggestions(self, generator):
        """Test warning and suggestion generation"""
        # Expensive query
        result = generator.generate(
            "Show me percentile of all metrics for all services in the last quarter"
        )
        
        # Should warn about expensive operation
        assert len(result.warnings) > 0
        assert any('expensive' in w.lower() for w in result.warnings)
        
        # Should suggest optimizations
        assert len(result.suggestions) > 0
    
    def test_alternative_queries(self, generator):
        """Test alternative query generation"""
        result = generator.generate("Show transactions")
        
        # Should provide alternatives
        assert len(result.alternatives) > 0
        
        # Alternatives should be valid NRQL
        for alt in result.alternatives:
            assert "SELECT" in alt
            assert "FROM" in alt
    
    @pytest.mark.parametrize("natural_query,expected_elements", [
        ("Show errors where status > 500", ["WHERE", "status > 500"]),
        ("Top 10 services by error rate", ["LIMIT 10", "FACET"]),
        ("Response time trend", ["TIMESERIES"]),
        ("Compare this week to last week", ["COMPARE WITH"]),
        ("95th percentile latency", ["percentile", "95"])
    ])
    def test_various_query_patterns(self, generator, natural_query, expected_elements):
        """Test various query patterns"""
        result = generator.generate(natural_query)
        
        for element in expected_elements:
            assert element in result.nrql
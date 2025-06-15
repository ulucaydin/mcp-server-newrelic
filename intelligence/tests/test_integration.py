"""Integration tests with mock NRDB data"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from unittest.mock import Mock, patch, MagicMock

from intelligence.patterns.engine import PatternEngine
from intelligence.query.query_generator import QueryGenerator
from intelligence.visualization.data_shape_analyzer import DataShapeAnalyzer
from intelligence.visualization.chart_recommender import ChartRecommender
from intelligence.visualization.layout_optimizer import (
    LayoutOptimizer, Widget, LayoutConstraints, 
    WidgetSize, WidgetPriority, LayoutStrategy
)


class MockNRDBClient:
    """Mock NRDB client for testing"""
    
    def __init__(self):
        self.queries_executed = []
        self.mock_data = self._generate_mock_data()
    
    def _generate_mock_data(self):
        """Generate realistic mock NRDB data"""
        # Transaction data
        transaction_data = self._generate_transaction_data()
        
        # Metric data
        metric_data = self._generate_metric_data()
        
        # Log data
        log_data = self._generate_log_data()
        
        return {
            'Transaction': transaction_data,
            'Metric': metric_data,
            'Log': log_data
        }
    
    def _generate_transaction_data(self):
        """Generate mock transaction data"""
        np.random.seed(42)
        n_records = 10000
        
        # Time range: last 7 days
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)
        timestamps = pd.date_range(start_time, end_time, periods=n_records)
        
        # Services and endpoints
        services = ['web', 'api', 'auth', 'payment', 'search']
        endpoints = ['/home', '/api/users', '/api/products', '/checkout', '/search']
        
        # Generate data with patterns
        data = []
        for i, ts in enumerate(timestamps):
            # Add daily pattern (business hours)
            hour = ts.hour
            is_business_hours = 9 <= hour <= 17
            base_load = 100 if is_business_hours else 30
            
            # Add weekly pattern (weekdays vs weekends)
            is_weekend = ts.weekday() >= 5
            if is_weekend:
                base_load *= 0.3
            
            # Response time with service-specific characteristics
            service = np.random.choice(services)
            if service == 'payment':
                response_time = np.random.gamma(3, 50)  # Slower
            elif service == 'search':
                response_time = np.random.gamma(2, 30)  # Medium
            else:
                response_time = np.random.gamma(1.5, 20)  # Fast
            
            # Add anomalies
            if i % 1000 == 0:  # Periodic spikes
                response_time *= 5
            
            # Error probability
            error_prob = 0.01
            if service == 'payment' and not is_business_hours:
                error_prob = 0.05  # Higher error rate for payment at night
            
            data.append({
                'timestamp': ts,
                'service': service,
                'endpoint': np.random.choice(endpoints),
                'duration': response_time,
                'error': np.random.random() < error_prob,
                'statusCode': 500 if np.random.random() < error_prob else 200,
                'host': f"host-{np.random.randint(1, 11)}",
                'region': np.random.choice(['us-east', 'us-west', 'eu-central']),
                'throughput': base_load + np.random.normal(0, 10)
            })
        
        return pd.DataFrame(data)
    
    def _generate_metric_data(self):
        """Generate mock metric data"""
        np.random.seed(43)
        n_records = 5000
        
        # Time range: last 24 hours
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)
        timestamps = pd.date_range(start_time, end_time, periods=n_records)
        
        data = []
        for i, ts in enumerate(timestamps):
            # CPU usage with daily pattern
            hour = ts.hour
            base_cpu = 30 + 20 * np.sin(2 * np.pi * hour / 24)
            
            # Memory usage correlated with CPU
            memory = base_cpu * 1.5 + np.random.normal(0, 5)
            
            # Disk I/O with spikes
            disk_io = np.random.gamma(2, 10)
            if i % 500 == 0:  # Periodic backup spikes
                disk_io *= 10
            
            for host in [f"host-{j}" for j in range(1, 6)]:
                data.append({
                    'timestamp': ts,
                    'host': host,
                    'cpu.usage': max(0, min(100, base_cpu + np.random.normal(0, 10))),
                    'memory.usage': max(0, min(100, memory + np.random.normal(0, 5))),
                    'disk.io': disk_io + np.random.gamma(1, 5),
                    'network.in': np.random.gamma(3, 100),
                    'network.out': np.random.gamma(3, 80)
                })
        
        return pd.DataFrame(data)
    
    def _generate_log_data(self):
        """Generate mock log data"""
        np.random.seed(44)
        n_records = 2000
        
        # Time range: last 6 hours
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=6)
        timestamps = pd.date_range(start_time, end_time, periods=n_records)
        
        log_levels = ['INFO', 'WARN', 'ERROR', 'DEBUG']
        log_weights = [0.6, 0.2, 0.1, 0.1]
        
        messages = {
            'INFO': ['Request processed', 'Cache hit', 'User logged in', 'Task completed'],
            'WARN': ['High memory usage', 'Slow query', 'Rate limit approaching', 'Deprecated API'],
            'ERROR': ['Database connection failed', 'Payment processing error', 'Invalid request', 'Timeout'],
            'DEBUG': ['Method entered', 'Variable value', 'SQL query', 'Cache miss']
        }
        
        data = []
        for ts in timestamps:
            level = np.random.choice(log_levels, p=log_weights)
            message = np.random.choice(messages[level])
            
            data.append({
                'timestamp': ts,
                'level': level,
                'message': message,
                'service': np.random.choice(['web', 'api', 'auth', 'payment']),
                'host': f"host-{np.random.randint(1, 11)}",
                'trace.id': f"trace-{np.random.randint(1000, 9999)}"
            })
        
        return pd.DataFrame(data)
    
    def query(self, nrql):
        """Execute mock NRQL query"""
        self.queries_executed.append(nrql)
        
        # Parse NRQL to determine which data to return
        if 'FROM Transaction' in nrql:
            base_data = self.mock_data['Transaction']
        elif 'FROM Metric' in nrql:
            base_data = self.mock_data['Metric']
        elif 'FROM Log' in nrql:
            base_data = self.mock_data['Log']
        else:
            return pd.DataFrame()  # Empty result
        
        # Apply time filter
        if 'SINCE' in nrql:
            # Simple time filtering (would be more complex in reality)
            if '1 hour ago' in nrql:
                cutoff = datetime.now() - timedelta(hours=1)
            elif '1 day ago' in nrql:
                cutoff = datetime.now() - timedelta(days=1)
            elif '1 week ago' in nrql:
                cutoff = datetime.now() - timedelta(weeks=1)
            else:
                cutoff = datetime.now() - timedelta(days=30)
            
            base_data = base_data[base_data['timestamp'] >= cutoff]
        
        # Apply WHERE filters
        if 'WHERE' in nrql:
            # Simple filter parsing (would be more complex in reality)
            if "service = 'api'" in nrql:
                base_data = base_data[base_data['service'] == 'api']
            if "error = true" in nrql:
                base_data = base_data[base_data['error'] == True]
        
        # Apply aggregations
        if 'SELECT' in nrql:
            if 'count(*)' in nrql.lower():
                return pd.DataFrame({'count': [len(base_data)]})
            elif 'average(duration)' in nrql.lower():
                return pd.DataFrame({'average': [base_data['duration'].mean()]})
            elif 'percentile(duration' in nrql.lower():
                # Extract percentile value
                import re
                match = re.search(r'percentile\(duration,\s*(\d+)\)', nrql.lower())
                if match:
                    p = int(match.group(1))
                    return pd.DataFrame({'percentile': [base_data['duration'].quantile(p/100)]})
        
        # Return sample of data if no aggregation
        return base_data.head(100)


class TestEndToEndIntegration:
    """End-to-end integration tests"""
    
    @pytest.fixture
    def mock_nrdb(self):
        return MockNRDBClient()
    
    @pytest.fixture
    def pattern_engine(self):
        return PatternEngine()
    
    @pytest.fixture
    def query_generator(self):
        return QueryGenerator()
    
    @pytest.fixture
    def visualization_pipeline(self):
        return {
            'shape_analyzer': DataShapeAnalyzer(),
            'chart_recommender': ChartRecommender(),
            'layout_optimizer': LayoutOptimizer()
        }
    
    def test_pattern_detection_on_nrdb_data(self, mock_nrdb, pattern_engine):
        """Test pattern detection on mock NRDB data"""
        # Get transaction data
        transaction_data = mock_nrdb.mock_data['Transaction']
        
        # Run pattern analysis
        results = pattern_engine.analyze(transaction_data)
        
        # Verify patterns detected
        assert results['summary']['total_patterns'] > 0
        
        pattern_types = {p['type'] for p in results['patterns']}
        
        # Should detect known patterns in the data
        assert 'seasonality' in pattern_types  # Daily/weekly patterns
        assert 'anomaly_point' in pattern_types  # Spikes we injected
        assert 'correlation' in pattern_types  # Service-response time correlation
        
        # Check insights
        assert len(results['insights']) > 0
        insights_text = ' '.join(results['insights']).lower()
        assert any(word in insights_text for word in ['daily', 'weekly', 'pattern', 'anomaly'])
    
    def test_query_generation_with_context(self, mock_nrdb, query_generator):
        """Test query generation with NRDB context"""
        # Create context from mock data
        from intelligence.query.base import QueryContext
        
        context = QueryContext(
            available_schemas=[
                {
                    'name': 'Transaction',
                    'records_per_hour': 1400,  # ~10k records in 7 days
                    'common_facets': ['service', 'endpoint', 'host', 'region']
                },
                {
                    'name': 'Metric',
                    'records_per_hour': 1250,  # ~5k records in 24 hours  
                    'common_facets': ['host']
                }
            ]
        )
        
        # Test various natural language queries
        test_queries = [
            "Show me average response time by service",
            "Find errors in the payment service",
            "What's the CPU usage trend?",
            "Top 5 slowest endpoints"
        ]
        
        for nl_query in test_queries:
            result = query_generator.generate(nl_query, context)
            
            # Verify NRQL generated
            assert result.nrql != ""
            assert result.confidence > 0.5
            
            # Verify cost estimation
            assert result.estimated_cost is not None
            
            # Execute the query on mock NRDB
            query_result = mock_nrdb.query(result.nrql)
            assert query_result is not None
    
    def test_visualization_recommendation_pipeline(self, mock_nrdb, visualization_pipeline):
        """Test complete visualization recommendation pipeline"""
        # Get data
        metric_data = mock_nrdb.mock_data['Metric']
        
        # Step 1: Analyze data shape
        shape_analyzer = visualization_pipeline['shape_analyzer']
        data_shape = shape_analyzer.analyze(metric_data)
        
        # Verify shape analysis
        assert data_shape.has_time_series
        assert 'cpu.usage' in data_shape.primary_metrics
        assert 'host' in data_shape.primary_dimensions
        
        # Step 2: Get chart recommendations
        chart_recommender = visualization_pipeline['chart_recommender']
        recommendations = chart_recommender.recommend(data_shape)
        
        # Verify recommendations
        assert len(recommendations) > 0
        chart_types = [r.chart_type.value for r in recommendations]
        
        # Should recommend time series charts for metric data
        assert any('timeseries' in ct for ct in chart_types)
        
        # Step 3: Create dashboard layout
        layout_optimizer = visualization_pipeline['layout_optimizer']
        
        # Create widgets from recommendations
        widgets = []
        for i, rec in enumerate(recommendations[:5]):
            widget = Widget(
                id=f"widget_{i}",
                title=f"{rec.chart_type.value} - {rec.reasoning[:50]}",
                chart_type=rec.chart_type,
                data_query=f"SELECT * FROM Metric",  # Simplified
                priority=WidgetPriority.HIGH if i < 2 else WidgetPriority.MEDIUM
            )
            widgets.append(widget)
        
        # Optimize layout
        constraints = LayoutConstraints(
            max_columns=4,
            max_rows=10,
            maintain_aspect_ratio=True
        )
        
        layout = layout_optimizer.optimize(widgets, constraints, LayoutStrategy.GRID)
        
        # Verify layout
        assert len(layout.placements) == len(widgets)
        assert layout.space_utilization > 0.5
        assert layout.visual_balance > 0.6
    
    def test_anomaly_detection_workflow(self, mock_nrdb, pattern_engine, query_generator):
        """Test anomaly detection workflow"""
        # Step 1: Detect anomalies in transaction data
        transaction_data = mock_nrdb.mock_data['Transaction']
        patterns = pattern_engine.analyze(transaction_data)
        
        # Find anomaly patterns
        anomaly_patterns = [p for p in patterns['patterns'] if 'anomaly' in p['type']]
        assert len(anomaly_patterns) > 0
        
        # Step 2: Generate queries to investigate anomalies
        anomaly_queries = []
        for pattern in anomaly_patterns[:3]:
            # Generate investigation query based on pattern
            if pattern['columns']:
                column = pattern['columns'][0]
                nl_query = f"Show me {column} values where anomalies were detected"
                result = query_generator.generate(nl_query)
                anomaly_queries.append(result)
        
        assert len(anomaly_queries) > 0
        
        # Step 3: Execute investigation queries
        for query_result in anomaly_queries:
            data = mock_nrdb.query(query_result.nrql)
            assert data is not None
    
    def test_correlation_analysis_workflow(self, mock_nrdb, pattern_engine):
        """Test correlation analysis workflow"""
        # Get metric data which should have correlations
        metric_data = mock_nrdb.mock_data['Metric']
        
        # Focus on numeric columns for correlation
        numeric_cols = ['cpu.usage', 'memory.usage', 'disk.io', 'network.in', 'network.out']
        correlation_data = metric_data[numeric_cols]
        
        # Run pattern analysis
        patterns = pattern_engine.analyze(correlation_data)
        
        # Find correlation patterns
        correlation_patterns = [p for p in patterns['patterns'] if 'correlation' in p['type']]
        assert len(correlation_patterns) > 0
        
        # Verify CPU-memory correlation was detected
        cpu_memory_correlation = next(
            (p for p in correlation_patterns 
             if 'cpu.usage' in p['columns'] and 'memory.usage' in p['columns']),
            None
        )
        assert cpu_memory_correlation is not None
        assert cpu_memory_correlation['confidence'] > 0.7
    
    def test_performance_monitoring_scenario(self, mock_nrdb, pattern_engine, query_generator):
        """Test complete performance monitoring scenario"""
        # Scenario: Monitor service performance and identify issues
        
        # Step 1: Get baseline performance metrics
        baseline_query = "Show average response time by service over the last week"
        baseline_result = query_generator.generate(baseline_query)
        baseline_data = mock_nrdb.query(baseline_result.nrql)
        
        # Step 2: Detect performance patterns
        transaction_data = mock_nrdb.mock_data['Transaction']
        service_perf = transaction_data.groupby('service').agg({
            'duration': ['mean', 'std', 'count'],
            'error': 'sum'
        }).reset_index()
        
        patterns = pattern_engine.analyze(transaction_data[['service', 'duration', 'error']])
        
        # Step 3: Generate alert queries for problematic services
        # Payment service should have higher error rates
        alert_query = "Show error rate for payment service when not during business hours"
        alert_result = query_generator.generate(alert_query)
        
        # Verify query addresses the issue
        assert 'payment' in alert_result.nrql
        assert 'error' in alert_result.nrql.lower()
    
    def test_log_analysis_workflow(self, mock_nrdb, pattern_engine):
        """Test log analysis workflow"""
        # Get log data
        log_data = mock_nrdb.mock_data['Log']
        
        # Analyze log patterns
        patterns = pattern_engine.analyze(log_data)
        
        # Should detect patterns in log levels
        pattern_types = {p['type'] for p in patterns['patterns']}
        
        # Convert to numeric for pattern detection
        log_data['level_numeric'] = log_data['level'].map({
            'DEBUG': 0, 'INFO': 1, 'WARN': 2, 'ERROR': 3
        })
        
        # Re-analyze with numeric levels
        patterns = pattern_engine.analyze(log_data[['timestamp', 'level_numeric', 'service']])
        
        # Verify some patterns detected
        assert len(patterns['patterns']) > 0
    
    def test_multi_stage_analysis(self, mock_nrdb, pattern_engine, query_generator, visualization_pipeline):
        """Test multi-stage analysis pipeline"""
        # Stage 1: Initial exploration
        explore_query = "Show me all available metrics"
        explore_result = query_generator.generate(explore_query)
        
        # Stage 2: Pattern detection on metric data
        metric_data = mock_nrdb.mock_data['Metric']
        patterns = pattern_engine.analyze(metric_data)
        
        # Stage 3: Generate focused queries based on patterns
        interesting_patterns = [p for p in patterns['patterns'] if p['confidence'] > 0.8]
        
        focused_queries = []
        for pattern in interesting_patterns[:3]:
            if pattern['type'] == 'trend':
                query = f"Show {pattern['columns'][0]} trend over time"
            elif pattern['type'] == 'anomaly_point':
                query = f"Find anomalies in {pattern['columns'][0]}"
            else:
                query = f"Analyze {pattern['columns'][0]}"
            
            result = query_generator.generate(query)
            focused_queries.append(result)
        
        # Stage 4: Visualize results
        shape_analyzer = visualization_pipeline['shape_analyzer']
        chart_recommender = visualization_pipeline['chart_recommender']
        
        for query_result in focused_queries:
            # Get data
            data = mock_nrdb.query(query_result.nrql)
            if not data.empty:
                # Analyze shape
                shape = shape_analyzer.analyze(data)
                
                # Get visualization recommendations
                charts = chart_recommender.recommend(shape)
                assert len(charts) > 0
    
    @pytest.mark.parametrize("scenario", [
        "high_traffic",
        "error_spike", 
        "performance_degradation",
        "resource_exhaustion"
    ])
    def test_incident_scenarios(self, mock_nrdb, pattern_engine, query_generator, scenario):
        """Test various incident detection scenarios"""
        # Inject scenario-specific data
        if scenario == "high_traffic":
            # Modify transaction data to show traffic spike
            data = mock_nrdb.mock_data['Transaction'].copy()
            spike_start = len(data) - 100
            data.loc[spike_start:, 'throughput'] *= 5
            
        elif scenario == "error_spike":
            # Increase error rate
            data = mock_nrdb.mock_data['Transaction'].copy()
            spike_start = len(data) - 200
            data.loc[spike_start:, 'error'] = np.random.random(200) < 0.3
            
        elif scenario == "performance_degradation":
            # Increase response times
            data = mock_nrdb.mock_data['Transaction'].copy()
            degradation_start = len(data) - 300
            data.loc[degradation_start:, 'duration'] *= 3
            
        else:  # resource_exhaustion
            # Max out CPU/memory
            data = mock_nrdb.mock_data['Metric'].copy()
            exhaustion_start = len(data) - 150
            data.loc[exhaustion_start:, 'cpu.usage'] = 95 + np.random.random(150) * 5
            data.loc[exhaustion_start:, 'memory.usage'] = 90 + np.random.random(150) * 10
        
        # Detect patterns
        patterns = pattern_engine.analyze(data)
        
        # Should detect anomalies or concerning patterns
        concerning_patterns = [
            p for p in patterns['patterns'] 
            if p['confidence'] > 0.7 and any(
                keyword in p['type'] 
                for keyword in ['anomaly', 'spike', 'trend', 'change']
            )
        ]
        
        assert len(concerning_patterns) > 0, f"No concerning patterns detected for {scenario}"
        
        # Generate investigation queries
        for pattern in concerning_patterns[:2]:
            if pattern['columns']:
                nl_query = f"Investigate {pattern['type']} in {pattern['columns'][0]}"
                result = query_generator.generate(nl_query)
                assert result.nrql != ""
                assert result.confidence > 0.5
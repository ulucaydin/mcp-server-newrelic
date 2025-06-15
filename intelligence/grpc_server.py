"""gRPC server for Python intelligence engine with New Relic APM"""

import grpc
import json
import logging
import concurrent.futures
from typing import Dict, Any, Optional
import pandas as pd
import sys
import os
import time

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import configuration
from intelligence.config.settings import get_config

# Import New Relic
try:
    import newrelic.agent
    HAS_NEWRELIC = True
except ImportError:
    HAS_NEWRELIC = False
    logging.warning("New Relic agent not available, APM instrumentation disabled")

# Import generated protobuf modules
from pkg.intelligence.proto import intelligence_pb2
from pkg.intelligence.proto import intelligence_pb2_grpc

# Import intelligence modules
from intelligence.patterns.engine import PatternEngine
from intelligence.query.query_generator import QueryGenerator
from intelligence.visualization.data_shape_analyzer import DataShapeAnalyzer
from intelligence.visualization.chart_recommender import ChartRecommender, RecommendationContext
from intelligence.visualization.layout_optimizer import LayoutOptimizer, Widget, LayoutConstraints, LayoutStrategy

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntelligenceServicer(intelligence_pb2_grpc.IntelligenceServiceServicer):
    """Implementation of the intelligence gRPC service with APM instrumentation"""
    
    def __init__(self):
        # Initialize components
        self.pattern_engine = PatternEngine()
        self.query_generator = QueryGenerator()
        self.shape_analyzer = DataShapeAnalyzer()
        self.chart_recommender = ChartRecommender()
        self.layout_optimizer = LayoutOptimizer()
        
        # Load configuration
        self.config = get_config()
        
        logger.info("Intelligence service initialized")
    
    @newrelic.agent.function_trace() if HAS_NEWRELIC else lambda f: f
    def HealthCheck(self, request, context):
        """Health check endpoint"""
        return intelligence_pb2.HealthResponse(
            healthy=True,
            version="1.0.0",
            components={
                "pattern_engine": "ready",
                "query_generator": "ready",
                "visualization": "ready"
            }
        )
    
    @newrelic.agent.function_trace() if HAS_NEWRELIC else lambda f: f
    def AnalyzePatterns(self, request, context):
        """Analyze patterns in data"""
        try:
            start_time = time.time()
            
            # Record custom event if APM is enabled
            if HAS_NEWRELIC and newrelic.agent.current_transaction():
                newrelic.agent.record_custom_event('PatternAnalysis', {
                    'data_size': len(request.data),
                    'has_columns': bool(request.columns),
                    'has_context': bool(request.context)
                })
            
            # Parse request data
            data_dict = json.loads(request.data)
            
            # Convert to DataFrame
            if isinstance(data_dict, list):
                df = pd.DataFrame(data_dict)
            elif isinstance(data_dict, dict):
                # Assume it's a dict of columns
                df = pd.DataFrame(data_dict)
            else:
                raise ValueError("Data must be a list or dict")
            
            # Parse columns if specified
            columns = None
            if request.columns:
                columns = json.loads(request.columns)
            
            # Parse context if provided
            context = None
            if request.context:
                context = json.loads(request.context)
            
            # Run pattern analysis
            results = self.pattern_engine.analyze(df, columns=columns, context=context)
            
            # Record metrics
            duration = time.time() - start_time
            if HAS_NEWRELIC and newrelic.agent.current_transaction():
                newrelic.agent.record_custom_metric('Intelligence/PatternAnalysis/Duration', duration)
                newrelic.agent.record_custom_metric('Intelligence/PatternAnalysis/PatternsFound', 
                                                   results['summary'].get('total_patterns', 0))
            
            # Convert results to JSON
            result_json = json.dumps(results)
            
            return intelligence_pb2.AnalyzePatternsResponse(
                result=result_json
            )
            
        except Exception as e:
            logger.error(f"Pattern analysis failed: {e}")
            
            if HAS_NEWRELIC and newrelic.agent.current_transaction():
                newrelic.agent.notice_error()
            
            return intelligence_pb2.AnalyzePatternsResponse(
                error=str(e)
            )
    
    @newrelic.agent.function_trace() if HAS_NEWRELIC else lambda f: f
    def GenerateQuery(self, request, context):
        """Generate NRQL query from natural language"""
        try:
            start_time = time.time()
            
            # Record custom event
            if HAS_NEWRELIC and newrelic.agent.current_transaction():
                newrelic.agent.record_custom_event('QueryGeneration', {
                    'query_length': len(request.natural_query),
                    'has_context': bool(request.context)
                })
            
            # Parse context if provided
            query_context = None
            if request.context:
                query_context = json.loads(request.context)
            
            # Generate query
            result = self.query_generator.generate(
                request.natural_query,
                context=query_context
            )
            
            # Record metrics
            duration = time.time() - start_time
            if HAS_NEWRELIC and newrelic.agent.current_transaction():
                newrelic.agent.record_custom_metric('Intelligence/QueryGeneration/Duration', duration)
                newrelic.agent.record_custom_metric('Intelligence/QueryGeneration/Confidence', result.confidence)
            
            # Convert result to response
            return intelligence_pb2.GenerateQueryResponse(
                query=result.nrql,
                confidence=result.confidence,
                explanation=result.explanation
            )
            
        except Exception as e:
            logger.error(f"Query generation failed: {e}")
            
            if HAS_NEWRELIC and newrelic.agent.current_transaction():
                newrelic.agent.notice_error()
            
            return intelligence_pb2.GenerateQueryResponse(
                error=str(e)
            )
    
    @newrelic.agent.function_trace() if HAS_NEWRELIC else lambda f: f
    def RecommendVisualizations(self, request, context):
        """Recommend visualizations for data"""
        try:
            start_time = time.time()
            
            # Parse request
            data_shape_dict = json.loads(request.data_shape)
            
            # Create DataShape object
            # This is a simplified version - in real implementation, 
            # we'd properly deserialize the DataShape
            from intelligence.visualization.data_shape_analyzer import DataShape
            data_shape = DataShape(
                num_rows=data_shape_dict.get('num_rows', 0),
                num_columns=data_shape_dict.get('num_columns', 0),
                numeric_columns=data_shape_dict.get('numeric_columns', []),
                categorical_columns=data_shape_dict.get('categorical_columns', []),
                temporal_columns=data_shape_dict.get('temporal_columns', []),
                primary_metrics=data_shape_dict.get('primary_metrics', []),
                primary_dimensions=data_shape_dict.get('primary_dimensions', []),
                has_time_series=data_shape_dict.get('has_time_series', False),
                time_granularity=data_shape_dict.get('time_granularity'),
                cardinality_info=data_shape_dict.get('cardinality_info', {}),
                correlation_info=data_shape_dict.get('correlation_info', {}),
                distribution_info=data_shape_dict.get('distribution_info', {}),
                data_quality_score=data_shape_dict.get('data_quality_score', 1.0)
            )
            
            # Get recommendations
            recommendations = self.chart_recommender.recommend(data_shape)
            
            # Record metrics
            duration = time.time() - start_time
            if HAS_NEWRELIC and newrelic.agent.current_transaction():
                newrelic.agent.record_custom_metric('Intelligence/Visualization/Duration', duration)
                newrelic.agent.record_custom_metric('Intelligence/Visualization/RecommendationCount', 
                                                   len(recommendations))
            
            # Convert to response format
            viz_recommendations = []
            for rec in recommendations:
                viz_recommendations.append({
                    'chart_type': rec.chart_type.value,
                    'confidence': rec.confidence,
                    'reasoning': rec.reasoning,
                    'configuration': rec.configuration or {}
                })
            
            result_json = json.dumps({
                'recommendations': viz_recommendations
            })
            
            return intelligence_pb2.RecommendVisualizationsResponse(
                result=result_json
            )
            
        except Exception as e:
            logger.error(f"Visualization recommendation failed: {e}")
            
            if HAS_NEWRELIC and newrelic.agent.current_transaction():
                newrelic.agent.notice_error()
            
            return intelligence_pb2.RecommendVisualizationsResponse(
                error=str(e)
            )


def serve():
    """Start the gRPC server with New Relic instrumentation"""
    # Load configuration
    config = get_config()
    
    # Initialize New Relic if enabled
    if HAS_NEWRELIC and config.apm.enabled and config.apm.license_key:
        # Initialize New Relic agent
        settings = newrelic.agent.global_settings()
        settings.app_name = config.apm.app_name
        settings.license_key = config.apm.license_key
        settings.distributed_tracing.enabled = config.apm.distributed_tracing
        settings.log_level = config.apm.log_level
        
        # Initialize the agent
        newrelic.agent.initialize()
        
        logger.info(f"New Relic APM initialized for app: {config.apm.app_name}")
    
    # Create gRPC server
    server = grpc.server(
        concurrent.futures.ThreadPoolExecutor(max_workers=config.server.max_workers)
    )
    
    # Add service
    intelligence_pb2_grpc.add_IntelligenceServiceServicer_to_server(
        IntelligenceServicer(), server
    )
    
    # Listen on port
    server.add_insecure_port(f'{config.server.host}:{config.server.port}')
    
    logger.info(f"Intelligence gRPC server starting on {config.server.host}:{config.server.port}")
    server.start()
    
    # Start metrics server if enabled
    if config.server.enable_metrics:
        from intelligence.metrics.performance_monitor import start_metrics_server
        start_metrics_server(config.server.metrics_port)
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        server.stop(0)
        
        # Shutdown New Relic
        if HAS_NEWRELIC:
            newrelic.agent.shutdown_agent(timeout=10)


if __name__ == '__main__':
    serve()
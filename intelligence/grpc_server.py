"""gRPC server for Python intelligence engine"""

import grpc
import json
import logging
import concurrent.futures
from typing import Dict, Any
import pandas as pd
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    """Implementation of the intelligence gRPC service"""
    
    def __init__(self):
        # Initialize components
        self.pattern_engine = PatternEngine()
        self.query_generator = QueryGenerator()
        self.shape_analyzer = DataShapeAnalyzer()
        self.chart_recommender = ChartRecommender()
        self.layout_optimizer = LayoutOptimizer()
        
        logger.info("Intelligence service initialized")
    
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
    
    def AnalyzePatterns(self, request, context):
        """Analyze patterns in data"""
        try:
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
            
            # Convert results to JSON
            result_json = json.dumps(results)
            
            return intelligence_pb2.AnalyzePatternsResponse(
                result=result_json
            )
            
        except Exception as e:
            logger.error(f"Pattern analysis failed: {e}")
            return intelligence_pb2.AnalyzePatternsResponse(
                error=str(e)
            )
    
    def GenerateQuery(self, request, context):
        """Generate NRQL query from natural language"""
        try:
            # Parse context if provided
            query_context = None
            if request.context:
                context_dict = json.loads(request.context)
                # Convert to QueryContext object
                from intelligence.query.base import QueryContext
                query_context = QueryContext(**context_dict)
            
            # Generate query
            result = self.query_generator.generate(
                request.natural_query,
                context=query_context
            )
            
            # Convert result to dict
            result_dict = {
                'nrql': result.nrql,
                'confidence': result.confidence,
                'estimated_cost': result.estimated_cost,
                'warnings': result.warnings,
                'suggestions': result.suggestions,
                'alternatives': result.alternatives,
                'metadata': result.metadata
            }
            
            result_json = json.dumps(result_dict)
            
            return intelligence_pb2.GenerateQueryResponse(
                result=result_json
            )
            
        except Exception as e:
            logger.error(f"Query generation failed: {e}")
            return intelligence_pb2.GenerateQueryResponse(
                error=str(e)
            )
    
    def RecommendCharts(self, request, context):
        """Recommend charts based on data shape"""
        try:
            # Parse data shape
            data_shape_dict = json.loads(request.data_shape)
            
            # Reconstruct DataShape object
            from intelligence.visualization.data_shape_analyzer import DataShape, DataCharacteristics
            
            # Convert column characteristics
            column_chars = []
            for col_dict in data_shape_dict.get('columns', []):
                # Create DataCharacteristics from dict
                char = DataCharacteristics(
                    name=col_dict['name'],
                    data_type=col_dict['data_type'],
                    cardinality=col_dict['cardinality'],
                    null_percentage=col_dict['null_percentage'],
                    unique_percentage=col_dict['unique_percentage']
                )
                column_chars.append(char)
            
            # Create DataShape
            data_shape = DataShape(
                row_count=data_shape_dict['row_count'],
                column_count=data_shape_dict['column_count'],
                column_characteristics=column_chars,
                has_time_series=data_shape_dict['has_time_series'],
                time_column=data_shape_dict.get('time_column'),
                primary_metrics=data_shape_dict.get('primary_metrics', []),
                primary_dimensions=data_shape_dict.get('primary_dimensions', []),
                data_quality_score=data_shape_dict.get('data_quality_score', 1.0)
            )
            
            # Parse context if provided
            rec_context = None
            if request.context:
                context_dict = json.loads(request.context)
                rec_context = RecommendationContext(**context_dict)
            
            # Get recommendations
            recommendations = self.chart_recommender.recommend(
                data_shape,
                context=rec_context
            )
            
            # Convert to dict
            result_dict = {
                'recommendations': [rec.to_dict() for rec in recommendations]
            }
            
            result_json = json.dumps(result_dict)
            
            return intelligence_pb2.RecommendChartsResponse(
                result=result_json
            )
            
        except Exception as e:
            logger.error(f"Chart recommendation failed: {e}")
            return intelligence_pb2.RecommendChartsResponse(
                error=str(e)
            )
    
    def OptimizeLayout(self, request, context):
        """Optimize dashboard layout"""
        try:
            # Parse widgets
            widgets_data = json.loads(request.widgets)
            widgets = []
            
            for w_dict in widgets_data:
                # Convert to Widget object
                from intelligence.visualization.layout_optimizer import WidgetSize, WidgetPriority
                from intelligence.visualization.chart_recommender import ChartType
                
                widget = Widget(
                    id=w_dict['id'],
                    title=w_dict['title'],
                    chart_type=ChartType(w_dict['chart_type']),
                    data_query=w_dict['data_query']
                )
                
                # Optional fields
                if 'size' in w_dict:
                    widget.size = WidgetSize[w_dict['size']]
                if 'priority' in w_dict:
                    widget.priority = WidgetPriority[w_dict['priority']]
                
                widgets.append(widget)
            
            # Parse constraints
            constraints = None
            if request.constraints:
                constraints_dict = json.loads(request.constraints)
                constraints = LayoutConstraints(**constraints_dict)
            
            # Parse strategy
            strategy = LayoutStrategy.GRID  # default
            if request.strategy:
                strategy = LayoutStrategy(request.strategy)
            
            # Optimize layout
            layout = self.layout_optimizer.optimize(
                widgets,
                constraints=constraints,
                strategy=strategy
            )
            
            # Convert to dict
            result_json = json.dumps(layout.to_dict())
            
            return intelligence_pb2.OptimizeLayoutResponse(
                result=result_json
            )
            
        except Exception as e:
            logger.error(f"Layout optimization failed: {e}")
            return intelligence_pb2.OptimizeLayoutResponse(
                error=str(e)
            )


def serve():
    """Start the gRPC server"""
    server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
    intelligence_pb2_grpc.add_IntelligenceServiceServicer_to_server(
        IntelligenceServicer(), server
    )
    
    # Listen on port 50051
    port = '50051'
    server.add_insecure_port(f'[::]:{port}')
    
    logger.info(f"Intelligence gRPC server starting on port {port}")
    server.start()
    
    # Keep server running
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down server")
        server.stop(0)


if __name__ == '__main__':
    serve()
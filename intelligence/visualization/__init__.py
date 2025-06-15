"""Visualization Intelligence - Smart chart selection and dashboard layout"""

from .data_shape_analyzer import DataShapeAnalyzer, DataShape, DataCharacteristics
from .chart_recommender import ChartRecommender, ChartRecommendation, ChartType
from .layout_optimizer import LayoutOptimizer, DashboardLayout, WidgetPlacement, Widget, LayoutStrategy

__all__ = [
    # Data Shape Analysis
    'DataShapeAnalyzer',
    'DataShape',
    'DataCharacteristics',
    
    # Chart Recommendation
    'ChartRecommender',
    'ChartRecommendation',
    'ChartType',
    
    # Layout Optimization
    'LayoutOptimizer',
    'DashboardLayout',
    'WidgetPlacement',
    'Widget',
    'LayoutStrategy'
]
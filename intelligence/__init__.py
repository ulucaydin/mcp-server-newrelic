"""
UDS Intelligence Engine

The brain of the Universal Data Synthesizer - providing ML-enhanced pattern detection,
intelligent query generation, and visualization recommendations.
"""

__version__ = "0.1.0"

from .patterns import (
    PatternDetector,
    StatisticalPatternDetector,
    TimeSeriesPatternDetector,
    AnomalyDetector,
    CorrelationDetector,
    Pattern,
    PatternType
)

from .query import (
    QueryGenerator,
    IntentParser,
    QueryOptimizer,
    NRQLBuilder
)

from .visualization import (
    DataShapeAnalyzer,
    VisualizationRecommender,
    LayoutOptimizer
)

__all__ = [
    # Pattern Detection
    'PatternDetector',
    'StatisticalPatternDetector', 
    'TimeSeriesPatternDetector',
    'AnomalyDetector',
    'CorrelationDetector',
    'Pattern',
    'PatternType',
    
    # Query Generation
    'QueryGenerator',
    'IntentParser',
    'QueryOptimizer',
    'NRQLBuilder',
    
    # Visualization Intelligence
    'DataShapeAnalyzer',
    'VisualizationRecommender',
    'LayoutOptimizer'
]
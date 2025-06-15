"""Chart Type Recommender - Recommends optimal chart types based on data characteristics"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from loguru import logger

from .data_shape_analyzer import DataShape, DataCharacteristics, DataType, DistributionType


class ChartType(Enum):
    """Available chart types in New Relic"""
    # Basic charts
    LINE = "line"
    AREA = "area"
    BAR = "bar"
    STACKED_BAR = "stacked_bar"
    PIE = "pie"
    TABLE = "table"
    BILLBOARD = "billboard"
    
    # Advanced charts
    HISTOGRAM = "histogram"
    HEATMAP = "heatmap"
    SCATTER = "scatter"
    FUNNEL = "funnel"
    
    # Time series specific
    TIMESERIES_LINE = "timeseries_line"
    TIMESERIES_AREA = "timeseries_area"
    TIMESERIES_STACKED = "timeseries_stacked"
    
    # Distribution charts
    BOX_PLOT = "box_plot"
    VIOLIN = "violin"
    
    # Specialized
    GAUGE = "gauge"
    BULLET = "bullet"
    SPARKLINE = "sparkline"
    MARKDOWN = "markdown"


class VisualizationGoal(Enum):
    """Common visualization goals"""
    COMPARISON = "comparison"
    TREND = "trend"
    DISTRIBUTION = "distribution"
    RELATIONSHIP = "relationship"
    COMPOSITION = "composition"
    RANKING = "ranking"
    DEVIATION = "deviation"
    CORRELATION = "correlation"
    GEOGRAPHIC = "geographic"


@dataclass
class ChartRecommendation:
    """A recommended chart configuration"""
    chart_type: ChartType
    confidence: float
    reasoning: str
    
    # Chart configuration
    x_axis: Optional[str] = None
    y_axis: Optional[List[str]] = None
    group_by: Optional[str] = None
    
    # Additional settings
    settings: Dict[str, Any] = field(default_factory=dict)
    
    # Pros and cons
    advantages: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    
    # When to use this chart
    use_cases: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'chart_type': self.chart_type.value,
            'confidence': self.confidence,
            'reasoning': self.reasoning,
            'configuration': {
                'x_axis': self.x_axis,
                'y_axis': self.y_axis,
                'group_by': self.group_by,
                'settings': self.settings
            },
            'advantages': self.advantages,
            'limitations': self.limitations,
            'use_cases': self.use_cases
        }


@dataclass
class RecommendationContext:
    """Context for chart recommendation"""
    visualization_goal: Optional[VisualizationGoal] = None
    preferred_charts: List[ChartType] = field(default_factory=list)
    excluded_charts: List[ChartType] = field(default_factory=list)
    max_data_points: int = 1000
    is_dashboard: bool = True
    dashboard_size: Optional[Tuple[int, int]] = None  # (width, height)
    user_expertise: str = "intermediate"  # beginner, intermediate, advanced


class ChartRecommender:
    """Recommends optimal chart types based on data shape and visualization goals"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.recommendation_rules = self._initialize_rules()
        
    def recommend(self,
                 data_shape: DataShape,
                 context: Optional[RecommendationContext] = None) -> List[ChartRecommendation]:
        """
        Recommend chart types based on data shape
        
        Args:
            data_shape: Analysis of the data characteristics
            context: Optional context for recommendations
            
        Returns:
            List of chart recommendations ordered by confidence
        """
        context = context or RecommendationContext()
        recommendations = []
        
        # Determine visualization goal if not provided
        if not context.visualization_goal:
            context.visualization_goal = self._infer_visualization_goal(data_shape)
        
        logger.info(f"Recommending charts for goal: {context.visualization_goal.value}")
        
        # Apply recommendation rules
        for rule in self.recommendation_rules:
            if self._rule_applies(rule, data_shape, context):
                recommendation = self._create_recommendation(rule, data_shape, context)
                if recommendation:
                    recommendations.append(recommendation)
        
        # Sort by confidence
        recommendations.sort(key=lambda r: r.confidence, reverse=True)
        
        # Filter out excluded charts
        if context.excluded_charts:
            recommendations = [
                r for r in recommendations 
                if r.chart_type not in context.excluded_charts
            ]
        
        # Limit to top recommendations
        max_recommendations = self.config.get('max_recommendations', 5)
        recommendations = recommendations[:max_recommendations]
        
        # If no recommendations, provide fallback
        if not recommendations:
            recommendations = self._get_fallback_recommendations(data_shape, context)
        
        return recommendations
    
    def _initialize_rules(self) -> List[Dict[str, Any]]:
        """Initialize recommendation rules"""
        return [
            # Time series rules
            {
                'name': 'timeseries_single_metric',
                'conditions': {
                    'has_time_series': True,
                    'metric_count': (1, 1),
                    'data_points': (10, float('inf'))
                },
                'chart_types': [ChartType.TIMESERIES_LINE, ChartType.TIMESERIES_AREA],
                'goal': VisualizationGoal.TREND,
                'confidence_base': 0.9
            },
            {
                'name': 'timeseries_multiple_metrics',
                'conditions': {
                    'has_time_series': True,
                    'metric_count': (2, 5),
                    'data_points': (10, float('inf'))
                },
                'chart_types': [ChartType.TIMESERIES_LINE, ChartType.TIMESERIES_STACKED],
                'goal': VisualizationGoal.COMPARISON,
                'confidence_base': 0.85
            },
            
            # Distribution rules
            {
                'name': 'distribution_continuous',
                'conditions': {
                    'has_continuous_numeric': True,
                    'distribution_focus': True
                },
                'chart_types': [ChartType.HISTOGRAM, ChartType.BOX_PLOT],
                'goal': VisualizationGoal.DISTRIBUTION,
                'confidence_base': 0.9
            },
            {
                'name': 'distribution_violin',
                'conditions': {
                    'has_continuous_numeric': True,
                    'has_grouping': True,
                    'group_count': (2, 10)
                },
                'chart_types': [ChartType.VIOLIN],
                'goal': VisualizationGoal.DISTRIBUTION,
                'confidence_base': 0.8
            },
            
            # Comparison rules
            {
                'name': 'comparison_categorical',
                'conditions': {
                    'has_categorical': True,
                    'category_count': (2, 20),
                    'metric_count': (1, 1)
                },
                'chart_types': [ChartType.BAR, ChartType.PIE],
                'goal': VisualizationGoal.COMPARISON,
                'confidence_base': 0.85
            },
            {
                'name': 'comparison_stacked',
                'conditions': {
                    'has_categorical': True,
                    'category_count': (2, 10),
                    'metric_count': (2, 5)
                },
                'chart_types': [ChartType.STACKED_BAR],
                'goal': VisualizationGoal.COMPOSITION,
                'confidence_base': 0.8
            },
            
            # Correlation rules
            {
                'name': 'correlation_scatter',
                'conditions': {
                    'has_correlation': True,
                    'metric_count': (2, 2)
                },
                'chart_types': [ChartType.SCATTER],
                'goal': VisualizationGoal.CORRELATION,
                'confidence_base': 0.9
            },
            {
                'name': 'correlation_heatmap',
                'conditions': {
                    'has_correlation': True,
                    'metric_count': (3, float('inf'))
                },
                'chart_types': [ChartType.HEATMAP],
                'goal': VisualizationGoal.CORRELATION,
                'confidence_base': 0.85
            },
            
            # Single value rules
            {
                'name': 'single_value_billboard',
                'conditions': {
                    'metric_count': (1, 1),
                    'data_points': (1, 1)
                },
                'chart_types': [ChartType.BILLBOARD],
                'goal': VisualizationGoal.COMPARISON,
                'confidence_base': 0.95
            },
            {
                'name': 'single_value_gauge',
                'conditions': {
                    'metric_count': (1, 1),
                    'data_points': (1, 1),
                    'has_threshold': True
                },
                'chart_types': [ChartType.GAUGE, ChartType.BULLET],
                'goal': VisualizationGoal.DEVIATION,
                'confidence_base': 0.9
            },
            
            # Table rules
            {
                'name': 'table_detailed',
                'conditions': {
                    'high_cardinality': True,
                    'multiple_attributes': True
                },
                'chart_types': [ChartType.TABLE],
                'goal': VisualizationGoal.RANKING,
                'confidence_base': 0.8
            },
            
            # Funnel rules
            {
                'name': 'funnel_process',
                'conditions': {
                    'is_process_data': True,
                    'ordered_categories': True
                },
                'chart_types': [ChartType.FUNNEL],
                'goal': VisualizationGoal.COMPOSITION,
                'confidence_base': 0.85
            }
        ]
    
    def _rule_applies(self,
                     rule: Dict[str, Any],
                     data_shape: DataShape,
                     context: RecommendationContext) -> bool:
        """Check if a rule applies to the current data"""
        
        conditions = rule['conditions']
        
        # Check visualization goal
        if 'goal' in rule and context.visualization_goal != rule['goal']:
            return False
        
        # Check time series
        if 'has_time_series' in conditions:
            if conditions['has_time_series'] != data_shape.has_time_series:
                return False
        
        # Check metric count
        if 'metric_count' in conditions:
            min_metrics, max_metrics = conditions['metric_count']
            metric_count = len(data_shape.primary_metrics)
            if not (min_metrics <= metric_count <= max_metrics):
                return False
        
        # Check data points
        if 'data_points' in conditions:
            min_points, max_points = conditions['data_points']
            if not (min_points <= data_shape.row_count <= max_points):
                return False
        
        # Check for continuous numeric data
        if conditions.get('has_continuous_numeric'):
            has_continuous = any(
                char.data_type == DataType.NUMERIC_CONTINUOUS
                for char in data_shape.column_characteristics
            )
            if not has_continuous:
                return False
        
        # Check for categorical data
        if conditions.get('has_categorical'):
            has_categorical = any(
                char.data_type in [DataType.CATEGORICAL_NOMINAL, DataType.CATEGORICAL_ORDINAL]
                for char in data_shape.column_characteristics
            )
            if not has_categorical:
                return False
        
        # Check category count
        if 'category_count' in conditions:
            min_cats, max_cats = conditions['category_count']
            categorical_chars = [
                char for char in data_shape.column_characteristics
                if char.data_type in [DataType.CATEGORICAL_NOMINAL, DataType.CATEGORICAL_ORDINAL]
            ]
            if categorical_chars:
                max_cardinality = max(char.cardinality for char in categorical_chars)
                if not (min_cats <= max_cardinality <= max_cats):
                    return False
        
        # Check for correlations
        if conditions.get('has_correlation'):
            has_correlation = any(
                char.correlations for char in data_shape.column_characteristics
            )
            if not has_correlation:
                return False
        
        # Check for distribution focus
        if conditions.get('distribution_focus'):
            # Infer from context or data characteristics
            if context.visualization_goal == VisualizationGoal.DISTRIBUTION:
                return True
            # Check if any numeric columns have interesting distributions
            for char in data_shape.column_characteristics:
                if char.data_type == DataType.NUMERIC_CONTINUOUS:
                    if char.distribution_type and char.distribution_type != DistributionType.UNKNOWN:
                        return True
            return False
        
        # Additional condition checks can be added here
        
        return True
    
    def _create_recommendation(self,
                             rule: Dict[str, Any],
                             data_shape: DataShape,
                             context: RecommendationContext) -> Optional[ChartRecommendation]:
        """Create a recommendation from a rule"""
        
        # Select best chart type from rule
        chart_types = rule['chart_types']
        if context.preferred_charts:
            # Prefer user's preferred charts if available in rule
            preferred = [ct for ct in chart_types if ct in context.preferred_charts]
            if preferred:
                chart_type = preferred[0]
            else:
                chart_type = chart_types[0]
        else:
            chart_type = chart_types[0]
        
        # Calculate confidence
        confidence = rule['confidence_base']
        confidence = self._adjust_confidence(confidence, data_shape, context, chart_type)
        
        # Create base recommendation
        recommendation = ChartRecommendation(
            chart_type=chart_type,
            confidence=confidence,
            reasoning=self._generate_reasoning(rule, data_shape, chart_type)
        )
        
        # Configure axes and settings
        self._configure_chart(recommendation, data_shape, chart_type)
        
        # Add advantages and limitations
        self._add_pros_cons(recommendation, data_shape, chart_type)
        
        # Add use cases
        self._add_use_cases(recommendation, chart_type)
        
        return recommendation
    
    def _adjust_confidence(self,
                         base_confidence: float,
                         data_shape: DataShape,
                         context: RecommendationContext,
                         chart_type: ChartType) -> float:
        """Adjust confidence based on data characteristics"""
        
        confidence = base_confidence
        
        # Boost for preferred charts
        if chart_type in context.preferred_charts:
            confidence *= 1.1
        
        # Reduce for high data volume with detailed charts
        if data_shape.row_count > context.max_data_points:
            if chart_type in [ChartType.SCATTER, ChartType.TABLE]:
                confidence *= 0.8
        
        # Boost for good data quality
        if data_shape.data_quality_score > 0.9:
            confidence *= 1.05
        
        # Reduce for poor data quality
        elif data_shape.data_quality_score < 0.5:
            confidence *= 0.9
        
        # Cap confidence
        return min(0.99, max(0.1, confidence))
    
    def _configure_chart(self,
                        recommendation: ChartRecommendation,
                        data_shape: DataShape,
                        chart_type: ChartType):
        """Configure chart axes and settings"""
        
        # Time series charts
        if chart_type in [ChartType.TIMESERIES_LINE, ChartType.TIMESERIES_AREA, ChartType.TIMESERIES_STACKED]:
            recommendation.x_axis = data_shape.time_column or 'timestamp'
            recommendation.y_axis = data_shape.primary_metrics[:3]  # Limit to 3 metrics
            
            # Add bucket size recommendation
            if data_shape.row_count > 1000:
                recommendation.settings['bucket_size'] = 'auto'
            
            # Stacked specific settings
            if chart_type == ChartType.TIMESERIES_STACKED:
                recommendation.settings['stack_type'] = 'normal'  # or 'percent'
        
        # Bar charts
        elif chart_type in [ChartType.BAR, ChartType.STACKED_BAR]:
            # Find best categorical dimension
            categorical_dims = data_shape.primary_dimensions
            if categorical_dims:
                recommendation.x_axis = categorical_dims[0]
            recommendation.y_axis = data_shape.primary_metrics[:1]
            
            # Orientation based on category count
            char = next((c for c in data_shape.column_characteristics if c.name == recommendation.x_axis), None)
            if char and char.cardinality > 10:
                recommendation.settings['orientation'] = 'horizontal'
        
        # Scatter plot
        elif chart_type == ChartType.SCATTER:
            metrics = data_shape.primary_metrics
            if len(metrics) >= 2:
                recommendation.x_axis = metrics[0]
                recommendation.y_axis = [metrics[1]]
                
                # Find correlations
                for char in data_shape.column_characteristics:
                    if char.name == metrics[0] and char.correlations:
                        # Use highest correlated metric
                        best_corr = max(char.correlations.items(), key=lambda x: abs(x[1]))
                        recommendation.y_axis = [best_corr[0]]
                        break
        
        # Pie chart
        elif chart_type == ChartType.PIE:
            if data_shape.primary_dimensions:
                recommendation.group_by = data_shape.primary_dimensions[0]
            if data_shape.primary_metrics:
                recommendation.y_axis = [data_shape.primary_metrics[0]]
            
            # Limit slices
            recommendation.settings['max_slices'] = 8
            recommendation.settings['other_bucket'] = True
        
        # Heatmap
        elif chart_type == ChartType.HEATMAP:
            dims = data_shape.primary_dimensions[:2]
            if len(dims) >= 2:
                recommendation.x_axis = dims[0]
                recommendation.group_by = dims[1]
            if data_shape.primary_metrics:
                recommendation.y_axis = [data_shape.primary_metrics[0]]
        
        # Billboard
        elif chart_type == ChartType.BILLBOARD:
            if data_shape.primary_metrics:
                recommendation.y_axis = [data_shape.primary_metrics[0]]
            
            # Add comparison if available
            recommendation.settings['show_comparison'] = True
            recommendation.settings['comparison_type'] = 'previous_period'
        
        # Table
        elif chart_type == ChartType.TABLE:
            # Include all relevant columns
            recommendation.settings['columns'] = (
                data_shape.primary_dimensions[:3] + 
                data_shape.primary_metrics[:5]
            )
            recommendation.settings['sortable'] = True
            recommendation.settings['pagination'] = data_shape.row_count > 100
    
    def _generate_reasoning(self,
                          rule: Dict[str, Any],
                          data_shape: DataShape,
                          chart_type: ChartType) -> str:
        """Generate human-readable reasoning for recommendation"""
        
        reasons = []
        
        # Time series reasoning
        if data_shape.has_time_series:
            reasons.append(f"Data contains time series with {data_shape.row_count} data points")
        
        # Metric/dimension reasoning
        metric_count = len(data_shape.primary_metrics)
        dim_count = len(data_shape.primary_dimensions)
        
        if metric_count == 1:
            reasons.append(f"Single metric '{data_shape.primary_metrics[0]}' to visualize")
        elif metric_count > 1:
            reasons.append(f"{metric_count} metrics available for comparison")
        
        if dim_count > 0:
            reasons.append(f"{dim_count} dimensions available for grouping")
        
        # Distribution reasoning
        for char in data_shape.column_characteristics:
            if char.distribution_type and char.distribution_type != DistributionType.UNKNOWN:
                reasons.append(f"'{char.name}' shows {char.distribution_type.value} distribution")
                break
        
        # Correlation reasoning
        correlations = []
        for char in data_shape.column_characteristics:
            if char.correlations:
                for other, corr in char.correlations.items():
                    if abs(corr) > 0.7:
                        correlations.append(f"'{char.name}' and '{other}' (r={corr:.2f})")
        
        if correlations:
            reasons.append(f"Strong correlations found: {', '.join(correlations[:2])}")
        
        # Chart-specific reasoning
        chart_reasons = {
            ChartType.LINE: "Best for showing trends over time",
            ChartType.BAR: "Ideal for comparing categories",
            ChartType.PIE: "Shows composition of the whole",
            ChartType.SCATTER: "Reveals relationships between variables",
            ChartType.HEATMAP: "Displays patterns across two dimensions",
            ChartType.HISTOGRAM: "Shows distribution of values",
            ChartType.BILLBOARD: "Highlights a single important metric",
            ChartType.TABLE: "Provides detailed view of all data"
        }
        
        if chart_type in chart_reasons:
            reasons.append(chart_reasons[chart_type])
        
        return ". ".join(reasons)
    
    def _add_pros_cons(self,
                      recommendation: ChartRecommendation,
                      data_shape: DataShape,
                      chart_type: ChartType):
        """Add advantages and limitations"""
        
        # General pros/cons by chart type
        pros_cons = {
            ChartType.LINE: {
                'pros': [
                    "Excellent for showing trends",
                    "Easy to read and understand",
                    "Supports multiple series"
                ],
                'cons': [
                    "Can become cluttered with many lines",
                    "Not suitable for categorical comparisons"
                ]
            },
            ChartType.BAR: {
                'pros': [
                    "Clear comparison between categories",
                    "Shows exact values well",
                    "Works with negative values"
                ],
                'cons': [
                    "Limited to reasonable number of categories",
                    "Not ideal for continuous data"
                ]
            },
            ChartType.PIE: {
                'pros': [
                    "Shows part-to-whole relationships",
                    "Visually appealing",
                    "Easy to understand percentages"
                ],
                'cons': [
                    "Limited to single data series",
                    "Hard to compare similar-sized slices",
                    "Not suitable for many categories"
                ]
            },
            ChartType.SCATTER: {
                'pros': [
                    "Shows relationships between variables",
                    "Identifies clusters and outliers",
                    "Can encode additional dimensions"
                ],
                'cons': [
                    "Can be hard to read with many points",
                    "Requires numeric data",
                    "May need trend lines for clarity"
                ]
            },
            ChartType.HEATMAP: {
                'pros': [
                    "Visualizes patterns in large datasets",
                    "Shows intensity through color",
                    "Compact representation"
                ],
                'cons': [
                    "Color interpretation can vary",
                    "Requires sufficient data density",
                    "Limited to 2-3 dimensions"
                ]
            },
            ChartType.TABLE: {
                'pros': [
                    "Shows exact values",
                    "Supports sorting and filtering",
                    "Can display many attributes"
                ],
                'cons': [
                    "Not visually engaging",
                    "Patterns hard to spot",
                    "Can be overwhelming with much data"
                ]
            }
        }
        
        if chart_type in pros_cons:
            recommendation.advantages = pros_cons[chart_type]['pros']
            recommendation.limitations = pros_cons[chart_type]['cons']
        
        # Add data-specific pros/cons
        if data_shape.data_quality_score < 0.7:
            recommendation.limitations.append("Data quality issues may affect accuracy")
        
        if data_shape.row_count > 10000 and chart_type in [ChartType.SCATTER, ChartType.LINE]:
            recommendation.limitations.append("Large dataset may require sampling or aggregation")
    
    def _add_use_cases(self,
                      recommendation: ChartRecommendation,
                      chart_type: ChartType):
        """Add typical use cases"""
        
        use_cases = {
            ChartType.LINE: [
                "Monitoring metrics over time",
                "Comparing trends between different series",
                "Identifying seasonal patterns"
            ],
            ChartType.BAR: [
                "Comparing performance across teams/services",
                "Ranking by a metric",
                "Showing survey results"
            ],
            ChartType.PIE: [
                "Showing market share",
                "Displaying resource allocation",
                "Visualizing survey responses"
            ],
            ChartType.SCATTER: [
                "Analyzing correlation between metrics",
                "Identifying outliers",
                "Segmentation analysis"
            ],
            ChartType.HEATMAP: [
                "Finding patterns in time-based data",
                "Correlation matrices",
                "Activity calendars"
            ],
            ChartType.HISTOGRAM: [
                "Understanding data distribution",
                "Identifying data quality issues",
                "Setting thresholds"
            ],
            ChartType.BILLBOARD: [
                "KPI dashboards",
                "Real-time monitoring",
                "Executive summaries"
            ],
            ChartType.TABLE: [
                "Detailed drill-downs",
                "Data export/reporting",
                "Multi-attribute analysis"
            ]
        }
        
        if chart_type in use_cases:
            recommendation.use_cases = use_cases[chart_type]
    
    def _infer_visualization_goal(self, data_shape: DataShape) -> VisualizationGoal:
        """Infer visualization goal from data shape"""
        
        # Time series data usually means trend analysis
        if data_shape.has_time_series:
            return VisualizationGoal.TREND
        
        # Multiple metrics suggest comparison
        if len(data_shape.primary_metrics) > 1:
            return VisualizationGoal.COMPARISON
        
        # Strong correlations suggest relationship analysis
        for char in data_shape.column_characteristics:
            if char.correlations and any(abs(c) > 0.7 for c in char.correlations.values()):
                return VisualizationGoal.CORRELATION
        
        # Categorical data with single metric suggests ranking
        if data_shape.primary_dimensions and len(data_shape.primary_metrics) == 1:
            return VisualizationGoal.RANKING
        
        # Default to comparison
        return VisualizationGoal.COMPARISON
    
    def _get_fallback_recommendations(self,
                                    data_shape: DataShape,
                                    context: RecommendationContext) -> List[ChartRecommendation]:
        """Provide fallback recommendations when no rules match"""
        
        recommendations = []
        
        # Always recommend table as fallback
        table_rec = ChartRecommendation(
            chart_type=ChartType.TABLE,
            confidence=0.5,
            reasoning="Table view provides detailed access to all data",
            advantages=["Shows all data", "Sortable", "Filterable"],
            limitations=["Not visually engaging", "Patterns hard to spot"],
            use_cases=["Data exploration", "Detailed analysis"]
        )
        recommendations.append(table_rec)
        
        # If numeric data exists, recommend billboard
        if data_shape.primary_metrics:
            billboard_rec = ChartRecommendation(
                chart_type=ChartType.BILLBOARD,
                confidence=0.4,
                reasoning="Billboard highlights key metrics",
                y_axis=[data_shape.primary_metrics[0]],
                advantages=["Clear metric display", "Good for dashboards"],
                limitations=["Single metric only"],
                use_cases=["KPI monitoring"]
            )
            recommendations.append(billboard_rec)
        
        return recommendations
    
    def explain_recommendation(self,
                             recommendation: ChartRecommendation,
                             data_shape: DataShape) -> str:
        """Generate detailed explanation for a recommendation"""
        
        explanation = f"""
Chart Type: {recommendation.chart_type.value.replace('_', ' ').title()}
Confidence: {recommendation.confidence:.0%}

Why this chart?
{recommendation.reasoning}

Configuration:
- X-axis: {recommendation.x_axis or 'N/A'}
- Y-axis: {', '.join(recommendation.y_axis) if recommendation.y_axis else 'N/A'}
- Group by: {recommendation.group_by or 'N/A'}

Advantages:
{chr(8226)} {f'{chr(8226)} '.join(recommendation.advantages)}

Limitations:
{chr(8226)} {f'{chr(8226)} '.join(recommendation.limitations)}

Best used for:
{chr(8226)} {f'{chr(8226)} '.join(recommendation.use_cases)}

Data characteristics:
- {data_shape.row_count:,} rows
- {data_shape.column_count} columns
- Quality score: {data_shape.data_quality_score:.0%}
"""
        
        return explanation.strip()
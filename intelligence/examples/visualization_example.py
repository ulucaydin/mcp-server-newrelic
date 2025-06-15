"""
Visualization Intelligence Example
=================================

This example demonstrates how to use the Intelligence Engine's visualization
capabilities to analyze data shape, recommend charts, and optimize dashboard layouts.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from intelligence.visualization.data_shape_analyzer import DataShapeAnalyzer
from intelligence.visualization.chart_recommender import (
    ChartRecommender, RecommendationContext, VisualizationGoal
)
from intelligence.visualization.layout_optimizer import (
    LayoutOptimizer, Widget, LayoutConstraints, LayoutStrategy,
    WidgetSize, WidgetPriority
)
from intelligence.visualization.chart_recommender import ChartType


def generate_sample_datasets():
    """Generate various types of datasets for visualization"""
    
    datasets = {}
    
    # 1. Time series data
    dates = pd.date_range(start='2024-01-01', periods=168, freq='H')  # 1 week
    datasets['timeseries'] = pd.DataFrame({
        'timestamp': dates,
        'requests_per_second': 1000 + 500 * np.sin(2 * np.pi * np.arange(168) / 24) + np.random.normal(0, 100, 168),
        'response_time_ms': 50 + 20 * np.sin(2 * np.pi * np.arange(168) / 24 + np.pi/4) + np.random.normal(0, 10, 168),
        'error_rate': np.random.beta(1, 100, 168),
        'service': np.random.choice(['web', 'api', 'db'], 168, p=[0.5, 0.3, 0.2])
    })
    
    # 2. Categorical comparison data
    datasets['categorical'] = pd.DataFrame({
        'service': ['web', 'api', 'db', 'cache', 'queue'],
        'avg_response_time': [45, 120, 85, 5, 250],
        'error_count': [120, 45, 30, 5, 15],
        'throughput': [50000, 30000, 15000, 100000, 20000]
    })
    
    # 3. Distribution data
    datasets['distribution'] = pd.DataFrame({
        'response_time': np.concatenate([
            np.random.lognormal(3, 0.5, 800),  # Most requests
            np.random.lognormal(5, 0.3, 200)   # Slow requests
        ]),
        'memory_usage': np.random.beta(2, 5, 1000) * 100,
        'request_size_kb': np.random.gamma(2, 50, 1000)
    })
    
    # 4. Correlation data
    n = 500
    x = np.random.normal(0, 1, n)
    datasets['correlation'] = pd.DataFrame({
        'cpu_usage': 50 + 10 * x + np.random.normal(0, 5, n),
        'memory_usage': 40 + 15 * x + np.random.normal(0, 7, n),
        'disk_io': 20 + 5 * x**2 + np.random.normal(0, 10, n),  # Non-linear
        'network_io': np.random.uniform(0, 100, n),  # No correlation
        'response_time': 100 - 20 * x + np.random.normal(0, 15, n)  # Negative correlation
    })
    
    # 5. Large detailed data (for tables)
    datasets['detailed'] = pd.DataFrame({
        'transaction_id': [f'txn_{i:06d}' for i in range(100)],
        'timestamp': pd.date_range(start='2024-01-01 12:00', periods=100, freq='1min'),
        'user_id': [f'user_{np.random.randint(1, 20):03d}' for _ in range(100)],
        'endpoint': np.random.choice(['/api/users', '/api/products', '/api/orders', '/api/search'], 100),
        'method': np.random.choice(['GET', 'POST', 'PUT', 'DELETE'], 100, p=[0.6, 0.2, 0.15, 0.05]),
        'status_code': np.random.choice([200, 201, 400, 404, 500], 100, p=[0.8, 0.1, 0.05, 0.03, 0.02]),
        'response_time_ms': np.random.gamma(2, 50, 100),
        'response_size_bytes': np.random.gamma(3, 1000, 100)
    })
    
    return datasets


def analyze_data_shape_example():
    """Demonstrate data shape analysis"""
    
    print("Data Shape Analysis Example")
    print("=" * 50)
    print()
    
    # Initialize analyzer
    analyzer = DataShapeAnalyzer(config={
        'sample_size': 10000,
        'correlation_threshold': 0.5
    })
    
    # Generate datasets
    datasets = generate_sample_datasets()
    
    # Analyze each dataset
    for name, data in datasets.items():
        print(f"\nAnalyzing '{name}' dataset...")
        print("-" * 40)
        
        # Analyze shape
        shape = analyzer.analyze(data)
        
        # Display results
        print(f"Shape Summary:")
        print(f"  - Rows: {shape.row_count:,}")
        print(f"  - Columns: {shape.column_count}")
        print(f"  - Has time series: {shape.has_time_series}")
        if shape.time_column:
            print(f"  - Time column: {shape.time_column}")
        print(f"  - Primary metrics: {', '.join(shape.primary_metrics[:3])}")
        print(f"  - Primary dimensions: {', '.join(shape.primary_dimensions[:3])}")
        print(f"  - Data quality score: {shape.data_quality_score:.2%}")
        
        # Show column details for first 3 columns
        print(f"\nColumn Characteristics:")
        for char in shape.column_characteristics[:3]:
            print(f"  {char.name}:")
            print(f"    - Type: {char.data_type.value}")
            print(f"    - Cardinality: {char.cardinality}")
            print(f"    - Null %: {char.null_percentage:.1%}")
            
            if char.distribution_type:
                print(f"    - Distribution: {char.distribution_type.value}")
            
            if char.correlations:
                corr_str = ', '.join([f"{k}({v:.2f})" for k, v in list(char.correlations.items())[:2]])
                print(f"    - Correlations: {corr_str}")
    
    return datasets


def chart_recommendation_example(datasets):
    """Demonstrate chart recommendation"""
    
    print("\n\nChart Recommendation Example")
    print("=" * 50)
    print()
    
    # Initialize components
    analyzer = DataShapeAnalyzer()
    recommender = ChartRecommender()
    
    # Test different visualization goals
    contexts = [
        RecommendationContext(visualization_goal=VisualizationGoal.TREND),
        RecommendationContext(visualization_goal=VisualizationGoal.COMPARISON),
        RecommendationContext(visualization_goal=VisualizationGoal.DISTRIBUTION),
        RecommendationContext(visualization_goal=VisualizationGoal.CORRELATION)
    ]
    
    for context in contexts:
        print(f"\nGoal: {context.visualization_goal.value}")
        print("-" * 40)
        
        # Find best dataset for this goal
        if context.visualization_goal == VisualizationGoal.TREND:
            data = datasets['timeseries']
            data_name = 'timeseries'
        elif context.visualization_goal == VisualizationGoal.COMPARISON:
            data = datasets['categorical']
            data_name = 'categorical'
        elif context.visualization_goal == VisualizationGoal.DISTRIBUTION:
            data = datasets['distribution']
            data_name = 'distribution'
        else:  # CORRELATION
            data = datasets['correlation']
            data_name = 'correlation'
        
        print(f"Using '{data_name}' dataset")
        
        # Analyze and recommend
        shape = analyzer.analyze(data)
        recommendations = recommender.recommend(shape, context)
        
        # Display recommendations
        print(f"\nTop Recommendations:")
        for i, rec in enumerate(recommendations[:3], 1):
            print(f"\n  {i}. {rec.chart_type.value.replace('_', ' ').title()}")
            print(f"     Confidence: {rec.confidence:.0%}")
            print(f"     Reasoning: {rec.reasoning}")
            
            if rec.x_axis or rec.y_axis:
                print(f"     Configuration:")
                if rec.x_axis:
                    print(f"       - X-axis: {rec.x_axis}")
                if rec.y_axis:
                    print(f"       - Y-axis: {', '.join(rec.y_axis)}")
                if rec.group_by:
                    print(f"       - Group by: {rec.group_by}")
            
            print(f"     Advantages:")
            for adv in rec.advantages[:2]:
                print(f"       + {adv}")
    
    # Demonstrate chart explanation
    print("\n\nChart Type Explanation")
    print("-" * 40)
    
    # Get recommendation for time series
    shape = analyzer.analyze(datasets['timeseries'])
    recommendations = recommender.recommend(shape)
    
    if recommendations:
        rec = recommendations[0]
        explanation = recommender.explain_recommendation(rec, shape)
        print(explanation)


def layout_optimization_example():
    """Demonstrate dashboard layout optimization"""
    
    print("\n\nDashboard Layout Optimization Example")
    print("=" * 50)
    print()
    
    # Create sample widgets
    widgets = [
        Widget(
            id="w1",
            title="Service Performance Overview",
            chart_type=ChartType.TIMESERIES_LINE,
            data_query="SELECT average(duration) FROM Transaction TIMESERIES",
            priority=WidgetPriority.CRITICAL,
            size=WidgetSize.LARGE
        ),
        Widget(
            id="w2",
            title="Error Rate",
            chart_type=ChartType.BILLBOARD,
            data_query="SELECT percentage(count(*), WHERE error=true) FROM Transaction",
            priority=WidgetPriority.CRITICAL,
            size=WidgetSize.SMALL
        ),
        Widget(
            id="w3",
            title="Top Errors",
            chart_type=ChartType.TABLE,
            data_query="SELECT count(*) FROM Transaction WHERE error=true FACET errorMessage",
            priority=WidgetPriority.HIGH,
            size=WidgetSize.WIDE
        ),
        Widget(
            id="w4",
            title="Response Time Distribution",
            chart_type=ChartType.HISTOGRAM,
            data_query="SELECT histogram(duration) FROM Transaction",
            priority=WidgetPriority.MEDIUM,
            size=WidgetSize.MEDIUM
        ),
        Widget(
            id="w5",
            title="Service Comparison",
            chart_type=ChartType.BAR,
            data_query="SELECT average(duration) FROM Transaction FACET service",
            priority=WidgetPriority.HIGH,
            size=WidgetSize.MEDIUM
        ),
        Widget(
            id="w6",
            title="Throughput",
            chart_type=ChartType.BILLBOARD,
            data_query="SELECT rate(count(*), 1 minute) FROM Transaction",
            priority=WidgetPriority.HIGH,
            size=WidgetSize.SMALL
        ),
        Widget(
            id="w7",
            title="Host Performance",
            chart_type=ChartType.HEATMAP,
            data_query="SELECT average(duration) FROM Transaction FACET host, hour",
            priority=WidgetPriority.MEDIUM,
            size=WidgetSize.LARGE
        )
    ]
    
    # Set relationships
    widgets[0].related_widgets = ["w2", "w6"]  # Performance overview related to error rate and throughput
    widgets[1].related_widgets = ["w3"]  # Error rate related to top errors
    widgets[4].related_widgets = ["w5"]  # Service comparison related to throughput
    
    # Initialize optimizer
    optimizer = LayoutOptimizer()
    
    # Test different layout strategies
    strategies = [
        LayoutStrategy.GRID,
        LayoutStrategy.MASONRY,
        LayoutStrategy.FLOW
    ]
    
    constraints = LayoutConstraints(
        max_columns=4,
        max_rows=20,
        maintain_aspect_ratio=True,
        group_related_widgets=True
    )
    
    for strategy in strategies:
        print(f"\n{strategy.value.upper()} Layout")
        print("-" * 40)
        
        # Optimize layout
        layout = optimizer.optimize(widgets, constraints, strategy)
        
        # Display results
        print(f"Layout Metrics:")
        print(f"  - Grid: {layout.grid_columns} x {layout.grid_rows}")
        print(f"  - Space utilization: {layout.space_utilization:.1%}")
        print(f"  - Visual balance: {layout.visual_balance:.1%}")
        print(f"  - Relationship score: {layout.relationship_score:.1%}")
        print(f"  - Overall score: {layout.overall_score:.1%}")
        print(f"  - Optimization time: {layout.optimization_time:.3f}s")
        
        # Show placement
        print(f"\nWidget Placements:")
        for placement in layout.placements:
            widget = next(w for w in widgets if w.id == placement.widget_id)
            print(f"  - {widget.title}:")
            print(f"    Position: ({placement.position[0]}, {placement.position[1]})")
            print(f"    Size: {placement.size.value[0]}x{placement.size.value[1]}")
        
        # Get improvement suggestions
        suggestions = optimizer.suggest_improvements(layout)
        if suggestions:
            print(f"\nImprovement Suggestions:")
            for suggestion in suggestions:
                print(f"  - {suggestion}")
    
    # Test responsive layout
    print("\n\nResponsive Layout Testing")
    print("-" * 40)
    
    # Mobile constraints
    mobile_constraints = LayoutConstraints(
        max_columns=1,
        mobile_friendly=True,
        max_widgets_per_row=1
    )
    
    mobile_layout = optimizer.optimize(widgets[:4], mobile_constraints, LayoutStrategy.RESPONSIVE)
    print(f"Mobile Layout: {mobile_layout.grid_columns} columns")
    
    # Tablet constraints
    tablet_constraints = LayoutConstraints(
        max_columns=2,
        tablet_friendly=True
    )
    
    tablet_layout = optimizer.optimize(widgets, tablet_constraints, LayoutStrategy.RESPONSIVE)
    print(f"Tablet Layout: {tablet_layout.grid_columns} columns")


def integrated_visualization_pipeline():
    """Demonstrate complete visualization pipeline"""
    
    print("\n\nIntegrated Visualization Pipeline")
    print("=" * 50)
    print()
    
    # Initialize all components
    analyzer = DataShapeAnalyzer()
    recommender = ChartRecommender()
    optimizer = LayoutOptimizer()
    
    # Generate complex dataset
    print("1. Generating complex monitoring dataset...")
    dates = pd.date_range(start='2024-01-01', periods=24*7, freq='H')
    data = pd.DataFrame({
        'timestamp': dates,
        'service': np.random.choice(['web', 'api', 'db', 'cache'], len(dates)),
        'host': np.random.choice([f'host-{i}' for i in range(1, 6)], len(dates)),
        'response_time': np.random.gamma(2, 50, len(dates)),
        'error_count': np.random.poisson(1, len(dates)),
        'cpu_usage': np.random.beta(2, 5, len(dates)) * 100,
        'memory_usage': np.random.beta(3, 4, len(dates)) * 100,
        'requests': np.random.poisson(100, len(dates))
    })
    print(f"   Generated {len(data)} records")
    
    # Step 1: Analyze data
    print("\n2. Analyzing data shape...")
    shape = analyzer.analyze(data)
    print(f"   Identified {len(shape.primary_metrics)} metrics and {len(shape.primary_dimensions)} dimensions")
    
    # Step 2: Get recommendations for different aspects
    print("\n3. Getting visualization recommendations...")
    
    # Overall dashboard context
    context = RecommendationContext(
        visualization_goal=VisualizationGoal.COMPARISON,
        is_dashboard=True,
        dashboard_size=(1920, 1080),
        user_expertise="intermediate"
    )
    
    recommendations = recommender.recommend(shape, context)
    print(f"   Received {len(recommendations)} recommendations")
    
    # Step 3: Create widgets from recommendations
    print("\n4. Creating dashboard widgets...")
    widgets = []
    
    # Add key metrics as billboards
    for metric in shape.primary_metrics[:3]:
        widgets.append(Widget(
            id=f"billboard_{metric}",
            title=f"Current {metric.replace('_', ' ').title()}",
            chart_type=ChartType.BILLBOARD,
            data_query=f"SELECT latest({metric}) FROM data",
            priority=WidgetPriority.HIGH,
            size=WidgetSize.SMALL
        ))
    
    # Add main visualizations from recommendations
    for i, rec in enumerate(recommendations[:4]):
        widgets.append(Widget(
            id=f"chart_{i}",
            title=f"{rec.chart_type.value.replace('_', ' ').title()} - {shape.primary_metrics[0]}",
            chart_type=rec.chart_type,
            data_query="SELECT * FROM data",  # Simplified
            priority=WidgetPriority.MEDIUM if i > 1 else WidgetPriority.HIGH,
            size=WidgetSize.LARGE if rec.chart_type in [ChartType.TIMESERIES_LINE, ChartType.HEATMAP] else WidgetSize.MEDIUM
        ))
    
    # Add detail table
    widgets.append(Widget(
        id="detail_table",
        title="Detailed Metrics",
        chart_type=ChartType.TABLE,
        data_query="SELECT * FROM data LIMIT 100",
        priority=WidgetPriority.LOW,
        size=WidgetSize.WIDE
    ))
    
    print(f"   Created {len(widgets)} widgets")
    
    # Step 4: Optimize layout
    print("\n5. Optimizing dashboard layout...")
    
    constraints = LayoutConstraints(
        max_columns=4,
        max_rows=15,
        maintain_aspect_ratio=True,
        group_related_widgets=True
    )
    
    layout = optimizer.optimize(widgets, constraints, LayoutStrategy.GRID)
    
    print(f"   Layout optimized:")
    print(f"   - Grid size: {layout.grid_columns}x{layout.grid_rows}")
    print(f"   - Space utilization: {layout.space_utilization:.0%}")
    print(f"   - Overall quality: {layout.overall_score:.0%}")
    
    # Step 5: Generate dashboard configuration
    print("\n6. Generating dashboard configuration...")
    
    dashboard_config = {
        'title': 'System Performance Dashboard',
        'description': 'Comprehensive monitoring dashboard with intelligent layout',
        'grid': {
            'columns': layout.grid_columns,
            'rows': layout.grid_rows
        },
        'widgets': []
    }
    
    for placement in layout.placements:
        widget = next(w for w in widgets if w.id == placement.widget_id)
        dashboard_config['widgets'].append({
            'id': widget.id,
            'title': widget.title,
            'type': widget.chart_type.value,
            'query': widget.data_query,
            'position': {
                'x': placement.position[0],
                'y': placement.position[1],
                'width': placement.size.value[0],
                'height': placement.size.value[1]
            }
        })
    
    # Save configuration
    import json
    with open('dashboard_config.json', 'w') as f:
        json.dump(dashboard_config, f, indent=2)
    
    print("   Dashboard configuration saved to dashboard_config.json")
    
    print("\nPipeline completed successfully!")


if __name__ == "__main__":
    # Run examples
    print("Running Visualization Intelligence Examples")
    print("==========================================\n")
    
    # Example 1: Data shape analysis
    datasets = analyze_data_shape_example()
    
    # Example 2: Chart recommendations
    chart_recommendation_example(datasets)
    
    # Example 3: Layout optimization
    layout_optimization_example()
    
    # Example 4: Integrated pipeline
    integrated_visualization_pipeline()
    
    print("\nAll visualization examples completed!")
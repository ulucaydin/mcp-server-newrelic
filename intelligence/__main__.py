"""Entry point for running intelligence module as a script"""

import sys
import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Intelligence Engine')
    parser.add_argument('--mode', choices=['grpc', 'demo'], default='grpc',
                        help='Run mode: grpc server or demo')
    
    args = parser.parse_args()
    
    if args.mode == 'grpc':
        # Run gRPC server
        from .grpc_server import serve
        serve()
    elif args.mode == 'demo':
        # Run demo
        run_demo()
    else:
        parser.print_help()
        sys.exit(1)

def run_demo():
    """Run a demonstration of intelligence capabilities"""
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta
    
    from .patterns.engine import PatternEngine
    from .query.query_generator import QueryGenerator
    from .visualization.data_shape_analyzer import DataShapeAnalyzer
    from .visualization.chart_recommender import ChartRecommender
    
    print("=== Intelligence Engine Demo ===\n")
    
    # Create sample data
    print("1. Creating sample data...")
    dates = pd.date_range(start='2024-01-01', periods=100, freq='H')
    data = pd.DataFrame({
        'timestamp': dates,
        'response_time': np.random.gamma(2, 2, 100) * 100,  # Response times in ms
        'error_count': np.random.poisson(2, 100),
        'throughput': np.random.normal(1000, 200, 100),
        'cpu_usage': np.random.beta(2, 5, 100) * 100,  # CPU percentage
        'service': np.random.choice(['web', 'api', 'db'], 100),
        'region': np.random.choice(['us-east', 'us-west', 'eu-central'], 100)
    })
    
    print(f"Created dataset with {len(data)} rows and {len(data.columns)} columns\n")
    
    # Pattern Detection
    print("2. Detecting patterns...")
    pattern_engine = PatternEngine()
    patterns = pattern_engine.analyze(data)
    
    print(f"Found {patterns['summary']['total_patterns']} patterns:")
    for pattern in patterns['patterns'][:5]:  # Show first 5
        print(f"  - {pattern['type']}: {pattern['description']} (confidence: {pattern['confidence']:.2f})")
    print()
    
    # Query Generation
    print("3. Generating NRQL queries...")
    query_gen = QueryGenerator()
    
    queries = [
        "Show me average response time by service",
        "Find anomalies in error count over the last day",
        "What's the CPU usage trend?"
    ]
    
    for natural_query in queries:
        result = query_gen.generate(natural_query)
        print(f"  Query: {natural_query}")
        print(f"  NRQL: {result.nrql}")
        print(f"  Confidence: {result.confidence:.2f}")
        print()
    
    # Data Shape Analysis
    print("4. Analyzing data shape...")
    shape_analyzer = DataShapeAnalyzer()
    data_shape = shape_analyzer.analyze(data)
    
    print(f"Data shape analysis:")
    print(f"  - Primary metrics: {', '.join(data_shape.primary_metrics)}")
    print(f"  - Primary dimensions: {', '.join(data_shape.primary_dimensions)}")
    print(f"  - Has time series: {data_shape.has_time_series}")
    print(f"  - Data quality score: {data_shape.data_quality_score:.2f}")
    print()
    
    # Chart Recommendations
    print("5. Recommending visualizations...")
    chart_rec = ChartRecommender()
    recommendations = chart_rec.recommend(data_shape)
    
    print("Top chart recommendations:")
    for rec in recommendations[:3]:
        print(f"  - {rec.chart_type.value}: {rec.reasoning}")
        print(f"    Confidence: {rec.confidence:.2f}")
    
    print("\n=== Demo Complete ===")

if __name__ == '__main__':
    main()
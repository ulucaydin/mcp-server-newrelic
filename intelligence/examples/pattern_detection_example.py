"""
Pattern Detection Example
========================

This example demonstrates how to use the Intelligence Engine's pattern detection
capabilities to analyze New Relic data and discover insights.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Import intelligence components
from intelligence.patterns.engine import PatternEngine
from intelligence.patterns.base import PatternContext


def generate_sample_data():
    """Generate sample monitoring data with various patterns"""
    # Create 7 days of hourly data
    dates = pd.date_range(start='2024-01-01', periods=24*7, freq='H')
    
    # Base metrics with patterns
    data = pd.DataFrame({
        'timestamp': dates,
        
        # CPU with daily pattern and trend
        'cpu_usage': [
            50 + 10 * np.sin(2 * np.pi * i / 24) +  # Daily pattern
            0.1 * i +  # Slight upward trend
            np.random.normal(0, 5)  # Noise
            for i in range(len(dates))
        ],
        
        # Memory correlated with CPU
        'memory_usage': [
            40 + 0.8 * (50 + 10 * np.sin(2 * np.pi * i / 24)) +
            np.random.normal(0, 3)
            for i in range(len(dates))
        ],
        
        # Response time with spikes
        'response_time_ms': [
            100 + np.random.gamma(2, 10) if i % 50 != 0 
            else 500 + np.random.gamma(2, 50)  # Periodic spikes
            for i in range(len(dates))
        ],
        
        # Error count with anomalies
        'error_count': [
            np.random.poisson(2) if i < 100 or i > 110
            else np.random.poisson(20)  # Anomaly period
            for i in range(len(dates))
        ],
        
        # Categorical dimension
        'service': [
            np.random.choice(['web', 'api', 'db'], p=[0.5, 0.3, 0.2])
            for _ in range(len(dates))
        ]
    })
    
    return data


def main():
    """Run pattern detection example"""
    
    print("Pattern Detection Example")
    print("=" * 50)
    print()
    
    # Generate sample data
    print("1. Generating sample monitoring data...")
    data = generate_sample_data()
    print(f"   Created {len(data)} data points with {len(data.columns)} metrics")
    print()
    
    # Initialize pattern engine
    print("2. Initializing Pattern Engine...")
    engine = PatternEngine(config={
        'min_confidence': 0.7,  # Only show high-confidence patterns
        'enable_caching': True
    })
    print("   Engine configured and ready")
    print()
    
    # Run pattern analysis
    print("3. Analyzing patterns in the data...")
    print("   This may take a few moments...")
    
    # Create context with metadata
    context = PatternContext(
        data_source="monitoring_metrics",
        time_range="last_7_days",
        metadata={
            'environment': 'production',
            'analyze_correlations': True
        }
    )
    
    results = engine.analyze(data, context=context)
    print(f"   Analysis complete!")
    print()
    
    # Display summary
    print("4. Pattern Detection Summary")
    print("-" * 40)
    summary = results['summary']
    print(f"   Total patterns found: {summary['total_patterns']}")
    print(f"   Pattern types: {', '.join(summary['pattern_types'])}")
    print(f"   Average confidence: {summary['average_confidence']:.2%}")
    print()
    
    # Display top patterns
    print("5. Top Patterns Detected")
    print("-" * 40)
    
    for i, pattern in enumerate(results['patterns'][:10], 1):
        print(f"\n   Pattern #{i}:")
        print(f"   Type: {pattern['type']}")
        print(f"   Confidence: {pattern['confidence']:.2%}")
        print(f"   Columns: {', '.join(pattern['columns'])}")
        print(f"   Description: {pattern['description']}")
        
        # Show key evidence
        if 'evidence' in pattern and pattern['evidence']:
            print("   Evidence:")
            for key, value in list(pattern['evidence'].items())[:3]:
                if isinstance(value, (int, float)):
                    print(f"     - {key}: {value:.3f}")
                else:
                    print(f"     - {key}: {value}")
    
    print()
    
    # Display insights
    print("6. Generated Insights")
    print("-" * 40)
    
    for i, insight in enumerate(results['insights'][:5], 1):
        print(f"   {i}. {insight}")
    
    print()
    
    # Demonstrate pattern filtering
    print("7. Filtering Patterns by Type")
    print("-" * 40)
    
    # Find anomaly patterns
    anomaly_patterns = [
        p for p in results['patterns'] 
        if 'anomaly' in p['type']
    ]
    print(f"   Found {len(anomaly_patterns)} anomaly patterns:")
    for pattern in anomaly_patterns[:3]:
        print(f"   - {pattern['description']}")
    
    print()
    
    # Find correlation patterns
    correlation_patterns = [
        p for p in results['patterns'] 
        if 'correlation' in p['type']
    ]
    print(f"   Found {len(correlation_patterns)} correlation patterns:")
    for pattern in correlation_patterns[:3]:
        print(f"   - {pattern['description']}")
    
    print()
    
    # Demonstrate focused analysis
    print("8. Focused Analysis Example")
    print("-" * 40)
    print("   Analyzing only performance metrics...")
    
    perf_results = engine.analyze(
        data[['timestamp', 'cpu_usage', 'memory_usage', 'response_time_ms']],
        columns=['cpu_usage', 'memory_usage', 'response_time_ms']
    )
    
    print(f"   Found {perf_results['summary']['total_patterns']} patterns in performance metrics")
    
    # Show performance-specific insights
    for insight in perf_results['insights'][:3]:
        print(f"   - {insight}")
    
    print()
    print("Example completed successfully!")
    
    # Return results for further processing
    return results


def demonstrate_custom_pattern_detection():
    """Demonstrate custom pattern detection configuration"""
    
    print("\nCustom Pattern Detection Example")
    print("=" * 50)
    print()
    
    # Create engine with custom configuration
    custom_engine = PatternEngine(config={
        'min_confidence': 0.9,  # Very high confidence only
        'enable_statistical': True,
        'enable_timeseries': True,
        'enable_anomaly': True,
        'enable_correlation': False,  # Disable correlation detection
        'anomaly_config': {
            'ensemble_methods': ['iforest', 'lof'],  # Specific methods
            'contamination': 0.05  # Expect 5% anomalies
        },
        'timeseries_config': {
            'stationarity_alpha': 0.01,  # Strict stationarity test
            'min_seasonality_strength': 0.7  # Strong seasonality only
        }
    })
    
    # Generate data with known patterns
    data = generate_sample_data()
    
    # Add more pronounced patterns
    data['strong_seasonal'] = [
        100 * (1 + 0.5 * np.sin(2 * np.pi * i / 24))  # 50% amplitude
        for i in range(len(data))
    ]
    
    # Run analysis
    results = custom_engine.analyze(data)
    
    print(f"With custom configuration, found {results['summary']['total_patterns']} patterns")
    print(f"All patterns have confidence >= 90%")
    
    # Verify high confidence
    min_confidence = min(p['confidence'] for p in results['patterns'])
    print(f"Minimum confidence: {min_confidence:.2%}")
    
    return results


if __name__ == "__main__":
    # Run main example
    results = main()
    
    # Run custom configuration example
    custom_results = demonstrate_custom_pattern_detection()
    
    # Show how to export results
    print("\nExporting Results")
    print("-" * 40)
    
    # Save patterns to JSON
    import json
    with open('pattern_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print("Results saved to pattern_results.json")
    
    # Create pattern summary DataFrame
    patterns_df = pd.DataFrame(results['patterns'])
    patterns_df.to_csv('patterns_summary.csv', index=False)
    print("Pattern summary saved to patterns_summary.csv")
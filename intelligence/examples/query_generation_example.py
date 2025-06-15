"""
Query Generation Example
=======================

This example demonstrates how to convert natural language queries to NRQL
using the Intelligence Engine's query generation capabilities.
"""

from intelligence.query.query_generator import QueryGenerator
from intelligence.query.base import QueryContext


def main():
    """Run query generation examples"""
    
    print("Query Generation Example")
    print("=" * 50)
    print()
    
    # Initialize query generator
    print("1. Initializing Query Generator...")
    generator = QueryGenerator(config={
        'cache_size': 100,
        'optimizer_config': {
            'performance_mode': 'balanced',
            'aggressive': False
        }
    })
    print("   Generator ready")
    print()
    
    # Create context with available schemas
    context = QueryContext(
        available_schemas=[
            {
                'name': 'Transaction',
                'records_per_hour': 1_000_000,
                'common_facets': ['appName', 'name', 'host', 'error']
            },
            {
                'name': 'PageView', 
                'records_per_hour': 500_000,
                'common_facets': ['browserName', 'pageUrl', 'countryCode']
            },
            {
                'name': 'Metric',
                'records_per_hour': 2_000_000,
                'common_facets': ['host', 'metricName']
            }
        ],
        cost_constraints={'max_cost': 100.0},
        user_preferences={'prefer_timeseries': True}
    )
    
    # Example queries
    example_queries = [
        # Basic queries
        "Show me average response time",
        "Count of errors in the last hour",
        "What's the current error rate?",
        
        # Filtered queries
        "Show errors for the api service",
        "Response time for production environment",
        "Transactions where duration > 1000ms",
        
        # Aggregation queries
        "95th percentile response time by service",
        "Top 10 slowest transactions",
        "Error count grouped by host",
        
        # Time-based queries
        "Response time trend over the last day",
        "Compare this week's errors to last week",
        "Show CPU usage for the past 6 hours",
        
        # Complex queries
        "What's causing high latency in the payment service?",
        "Find anomalies in error rate",
        "Which endpoints have degraded performance?"
    ]
    
    print("2. Converting Natural Language to NRQL")
    print("-" * 40)
    
    for i, nl_query in enumerate(example_queries, 1):
        print(f"\n   Example #{i}:")
        print(f"   Natural Language: {nl_query}")
        
        # Generate NRQL
        result = generator.generate(nl_query, context)
        
        print(f"   Generated NRQL: {result.nrql}")
        print(f"   Confidence: {result.confidence:.2%}")
        
        if result.estimated_cost:
            print(f"   Estimated Cost: ${result.estimated_cost:.2f}")
        
        # Show warnings if any
        if result.warnings:
            print("   Warnings:")
            for warning in result.warnings:
                print(f"     ⚠️  {warning}")
        
        # Show suggestions if any
        if result.suggestions:
            print("   Suggestions:")
            for suggestion in result.suggestions[:2]:
                print(f"     💡 {suggestion}")
        
        # Show alternatives if any
        if result.alternatives:
            print("   Alternative queries:")
            for j, alt in enumerate(result.alternatives[:2], 1):
                print(f"     {j}. {alt}")
    
    print()
    
    # Demonstrate query explanation
    print("3. Query Explanation Example")
    print("-" * 40)
    
    complex_nrql = """
    SELECT average(duration), percentile(duration, 95) 
    FROM Transaction 
    WHERE appName = 'production' AND error = true 
    SINCE 1 day ago 
    FACET service 
    LIMIT 10
    """
    
    print(f"   NRQL: {complex_nrql.strip()}")
    print()
    
    explanation = generator.explain_query(complex_nrql)
    print(f"   Explanation: {explanation['summary']}")
    print()
    print("   Components:")
    print(f"   - Data Source: {explanation['data_source']}")
    print(f"   - Time Range: {explanation['time_range']}")
    print(f"   - Aggregations: {', '.join(explanation['aggregations'])}")
    print(f"   - Filters: {', '.join(explanation['filters'])}")
    print(f"   - Grouping: {', '.join(explanation['grouping'])}")
    
    print()
    
    # Demonstrate query suggestions
    print("4. Query Suggestions")
    print("-" * 40)
    
    partial_queries = [
        "Show me",
        "What is the average",
        "Find anomalies in",
        "Top 10"
    ]
    
    for partial in partial_queries:
        print(f"\n   Partial query: '{partial}'")
        suggestions = generator.suggest_queries(partial, context)
        print("   Suggestions:")
        for j, suggestion in enumerate(suggestions[:3], 1):
            print(f"     {j}. {suggestion}")
    
    print()
    
    # Demonstrate batch processing
    print("5. Batch Query Generation")
    print("-" * 40)
    
    batch_queries = [
        "Average CPU usage by host",
        "Memory usage trend",
        "Disk I/O spikes",
        "Network latency percentiles"
    ]
    
    print("   Processing batch of queries...")
    batch_results = generator.generate_batch(batch_queries, context)
    
    print(f"   Generated {len(batch_results)} queries:")
    for i, (query, result) in enumerate(zip(batch_queries, batch_results), 1):
        print(f"   {i}. {query}")
        print(f"      → {result.nrql}")
    
    print()
    
    # Show metrics
    print("6. Generator Metrics")
    print("-" * 40)
    
    metrics = generator.get_metrics()
    print(f"   Total queries processed: {metrics['total_queries']}")
    print(f"   Cache hit rate: {metrics['cache_hit_rate']:.2%}")
    print(f"   Average confidence: {metrics['average_confidence']:.2%}")
    
    print()
    print("Example completed successfully!")


def demonstrate_advanced_features():
    """Demonstrate advanced query generation features"""
    
    print("\nAdvanced Query Generation Features")
    print("=" * 50)
    print()
    
    # Initialize with custom configuration
    generator = QueryGenerator(config={
        'parser_config': {
            'enable_spell_correction': True,
            'confidence_threshold': 0.6
        },
        'builder_config': {
            'default_limit': 100,
            'max_time_range_days': 30
        },
        'optimizer_config': {
            'performance_mode': 'cost',  # Optimize for cost
            'cost_threshold': 50.0,
            'aggressive': True
        }
    })
    
    # Create detailed context
    context = QueryContext(
        available_schemas=[
            {
                'name': 'Transaction',
                'records_per_hour': 10_000_000,  # High volume
                'attributes': [
                    'duration', 'error', 'errorMessage', 'name', 
                    'appName', 'host', 'request.uri', 'response.status'
                ],
                'common_facets': ['appName', 'name', 'host']
            }
        ],
        cost_constraints={
            'max_cost': 50.0,
            'optimization_level': 'aggressive'
        },
        user_preferences={
            'default_time_range': 'last_hour',
            'prefer_sampling': True,
            'max_results': 1000
        }
    )
    
    # Test with typos and variations
    print("1. Handling Query Variations")
    print("-" * 40)
    
    query_variations = [
        "Show me averge respnse time",  # Typos
        "display the mean duration",     # Synonyms
        "What's the avg latency?",      # Abbreviations
        "response time 95%ile"          # Alternative formats
    ]
    
    for query in query_variations:
        result = generator.generate(query, context)
        print(f"   Input: '{query}'")
        print(f"   Output: {result.nrql}")
        print(f"   Confidence: {result.confidence:.2%}")
        print()
    
    # Test cost optimization
    print("2. Cost Optimization Example")
    print("-" * 40)
    
    expensive_query = "Show me all transaction data for the last month with all attributes"
    result = generator.generate(expensive_query, context)
    
    print(f"   Original request: {expensive_query}")
    print(f"   Optimized NRQL: {result.nrql}")
    print(f"   Estimated cost: ${result.estimated_cost:.2f}")
    
    if 'optimization' in result.metadata:
        opt_meta = result.metadata['optimization']
        print(f"   Cost reduction: {opt_meta.get('cost_reduction', 0):.1%}")
        print(f"   Optimizations applied:")
        for opt in opt_meta.get('optimizations_applied', []):
            print(f"     - {opt}")
    
    print()
    
    # Test intent detection
    print("3. Intent Detection Examples")
    print("-" * 40)
    
    intent_examples = {
        "Why are there so many errors?": "troubleshoot",
        "Monitor CPU usage": "monitor",
        "Analyze user behavior patterns": "analyze",
        "Create a dashboard for service health": "report",
        "Alert me when response time > 1s": "alert",
        "Predict next hour's traffic": "forecast"
    }
    
    for query, expected_intent in intent_examples.items():
        result = generator.generate(query, context)
        detected_intent = result.intent.intent_type.value
        print(f"   Query: '{query}'")
        print(f"   Detected intent: {detected_intent}")
        print(f"   Match: {'✓' if detected_intent == expected_intent else '✗'}")
        print()


def demonstrate_real_world_scenarios():
    """Demonstrate real-world monitoring scenarios"""
    
    print("\nReal-World Monitoring Scenarios")
    print("=" * 50)
    print()
    
    generator = QueryGenerator()
    
    # Scenario 1: Incident Investigation
    print("Scenario 1: Investigating a Production Incident")
    print("-" * 40)
    
    incident_queries = [
        "Show me error rate spike in the last 2 hours",
        "Which services are affected?",
        "What are the most common error messages?",
        "Compare current error rate with yesterday at the same time",
        "Show me the slowest transactions during the incident"
    ]
    
    for query in incident_queries:
        result = generator.generate(query)
        print(f"   Q: {query}")
        print(f"   A: {result.nrql}")
        print()
    
    # Scenario 2: Performance Optimization
    print("Scenario 2: Performance Optimization")
    print("-" * 40)
    
    perf_queries = [
        "Find the slowest database queries",
        "Show me 99th percentile latency by endpoint",
        "Which hosts have the highest CPU usage?",
        "Identify transactions with high variance in response time",
        "Show me cache hit rate over time"
    ]
    
    for query in perf_queries[:3]:
        result = generator.generate(query)
        print(f"   Q: {query}")
        print(f"   A: {result.nrql}")
        print()
    
    # Scenario 3: Capacity Planning
    print("Scenario 3: Capacity Planning")
    print("-" * 40)
    
    capacity_queries = [
        "Show me weekly traffic growth trend",
        "Peak concurrent users by day of week",
        "Resource utilization during peak hours",
        "Project next month's storage requirements"
    ]
    
    for query in capacity_queries[:2]:
        result = generator.generate(query)
        print(f"   Q: {query}")
        print(f"   A: {result.nrql}")
        print()


if __name__ == "__main__":
    # Run main example
    main()
    
    # Run advanced features demo
    demonstrate_advanced_features()
    
    # Run real-world scenarios
    demonstrate_real_world_scenarios()
    
    print("\nAll examples completed!")
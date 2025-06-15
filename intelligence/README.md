# Intelligence Engine

The Intelligence Engine provides advanced ML/AI capabilities for the Universal Data Synthesizer (UDS), including pattern detection, natural language query generation, and intelligent visualization recommendations.

## Overview

The Intelligence Engine consists of three main components:

1. **Pattern Detection**: Automatically discovers statistical, temporal, and anomalous patterns in data
2. **Query Generation**: Converts natural language to optimized NRQL queries
3. **Visualization Intelligence**: Recommends optimal chart types and dashboard layouts

## Architecture

```
intelligence/
├── patterns/           # Pattern detection framework
│   ├── base.py        # Core pattern types and interfaces
│   ├── statistical.py  # Statistical pattern detection
│   ├── timeseries.py  # Time series analysis
│   ├── anomaly.py     # Anomaly detection algorithms
│   ├── correlation.py # Correlation analysis
│   └── engine.py      # Pattern orchestration engine
├── query/             # Query generation system
│   ├── base.py        # Query models and types
│   ├── intent_parser.py    # NLP intent parsing
│   ├── nrql_builder.py     # NRQL construction
│   ├── query_optimizer.py  # Cost/performance optimization
│   └── query_generator.py  # Main query interface
├── visualization/     # Visualization intelligence
│   ├── data_shape_analyzer.py  # Data characteristic analysis
│   ├── chart_recommender.py    # Chart type recommendations
│   └── layout_optimizer.py     # Dashboard layout optimization
└── grpc_server.py    # gRPC service interface
```

## Quick Start

### Installation

```bash
# Install Python dependencies
pip install -r intelligence/requirements.txt

# Download spaCy language model
python -m spacy download en_core_web_sm
```

### Basic Usage

#### Pattern Detection

```python
from intelligence.patterns.engine import PatternEngine
import pandas as pd

# Initialize engine
engine = PatternEngine()

# Analyze data
data = pd.read_csv('metrics.csv')
results = engine.analyze(data)

# View patterns
for pattern in results['patterns']:
    print(f"{pattern['type']}: {pattern['description']} (confidence: {pattern['confidence']:.2%})")

# Get insights
for insight in results['insights']:
    print(f"- {insight}")
```

#### Query Generation

```python
from intelligence.query.query_generator import QueryGenerator

# Initialize generator
generator = QueryGenerator()

# Convert natural language to NRQL
result = generator.generate("Show me average response time by service")
print(f"NRQL: {result.nrql}")
print(f"Confidence: {result.confidence:.2%}")

# Get query suggestions
suggestions = generator.suggest_queries("Show me")
for suggestion in suggestions:
    print(f"- {suggestion}")
```

#### Visualization Recommendations

```python
from intelligence.visualization.data_shape_analyzer import DataShapeAnalyzer
from intelligence.visualization.chart_recommender import ChartRecommender

# Analyze data shape
analyzer = DataShapeAnalyzer()
shape = analyzer.analyze(data)

# Get chart recommendations
recommender = ChartRecommender()
recommendations = recommender.recommend(shape)

for rec in recommendations:
    print(f"{rec.chart_type.value}: {rec.reasoning} (confidence: {rec.confidence:.2%})")
```

## Features

### Pattern Detection

The pattern detection framework identifies various patterns in data:

- **Statistical Patterns**
  - Distribution types (normal, skewed, bimodal, etc.)
  - Outliers and anomalies
  - Missing data patterns
  - Data quality issues

- **Time Series Patterns**
  - Trends (linear, exponential, polynomial)
  - Seasonality and cyclical patterns
  - Stationarity and volatility changes
  - Change points

- **Anomaly Detection**
  - Point anomalies (individual outliers)
  - Contextual anomalies (unusual in context)
  - Collective anomalies (unusual groups)
  - Uses ensemble methods (Isolation Forest, LOF, KNN)

- **Correlation Analysis**
  - Linear correlations
  - Non-linear relationships
  - Lagged correlations
  - Multivariate analysis

### Query Generation

The query generation system provides:

- **Natural Language Understanding**
  - Intent detection (explore, monitor, troubleshoot, etc.)
  - Entity extraction (metrics, dimensions, filters)
  - Time range parsing
  - Aggregation detection

- **NRQL Construction**
  - Automatic query building
  - Multiple aggregation support
  - Complex filtering
  - Time series and faceting

- **Query Optimization**
  - Cost-aware optimization
  - Performance tuning
  - Sampling strategies
  - Time range adjustments

### Visualization Intelligence

The visualization system offers:

- **Data Shape Analysis**
  - Data type detection
  - Distribution analysis
  - Cardinality assessment
  - Correlation detection
  - Time series identification

- **Chart Recommendations**
  - Goal-based recommendations
  - Data-driven selection
  - Confidence scoring
  - Configuration suggestions

- **Layout Optimization**
  - Multiple layout strategies (grid, masonry, flow)
  - Space utilization optimization
  - Visual balance calculation
  - Related widget grouping
  - Responsive design support

## Configuration

### Pattern Engine Configuration

```python
engine = PatternEngine(config={
    'min_confidence': 0.7,           # Minimum pattern confidence
    'enable_statistical': True,      # Enable statistical detection
    'enable_timeseries': True,       # Enable time series analysis
    'enable_anomaly': True,          # Enable anomaly detection
    'enable_correlation': True,      # Enable correlation analysis
    'anomaly_config': {
        'ensemble_methods': ['iforest', 'lof', 'knn'],
        'contamination': 0.1         # Expected anomaly rate
    },
    'correlation_config': {
        'min_correlation': 0.5,      # Minimum correlation threshold
        'check_nonlinear': True      # Check non-linear relationships
    }
})
```

### Query Generator Configuration

```python
generator = QueryGenerator(config={
    'cache_size': 100,               # Query cache size
    'parser_config': {
        'confidence_threshold': 0.6,  # Minimum parse confidence
        'enable_spell_correction': True
    },
    'optimizer_config': {
        'performance_mode': 'balanced',  # cost, speed, or balanced
        'aggressive': False,             # Aggressive optimization
        'cost_threshold': 100.0          # Maximum query cost
    }
})
```

### Visualization Configuration

```python
recommender = ChartRecommender(config={
    'max_recommendations': 5         # Maximum recommendations
})

optimizer = LayoutOptimizer(config={
    'default_grid_columns': 4,       # Default grid width
    'optimization_iterations': 100    # Optimization iterations
})
```

## Integration

### With Go Services

The Intelligence Engine integrates with Go services via gRPC:

```go
import "github.com/anthropics/mcp-server-newrelic/pkg/intelligence"

// Create service
service := intelligence.NewService(logger, "python3")

// Start service
err := service.Start(ctx)

// Use pattern detection
patterns, err := service.AnalyzePatterns(ctx, data)

// Generate queries
query, err := service.GenerateQuery(ctx, "Show errors", context)
```

### With MCP Protocol

The engine implements MCP tool interfaces:

```python
# Start gRPC server
python -m intelligence.grpc_server

# Or run as MCP tool
python -m intelligence --mode grpc
```

## Performance Considerations

### Pattern Detection

- **Sampling**: Large datasets are automatically sampled
- **Caching**: Results are cached to avoid recomputation
- **Parallel Processing**: Multiple detectors run concurrently
- **Memory Management**: Streaming analysis for large datasets

### Query Generation

- **Query Caching**: Common queries are cached
- **Cost Estimation**: Queries estimated before execution
- **Optimization Levels**: Configurable optimization aggressiveness
- **Batch Processing**: Multiple queries processed efficiently

### Visualization

- **Incremental Analysis**: Progressive data shape analysis
- **Layout Caching**: Optimized layouts are reusable
- **Responsive Optimization**: Device-specific optimizations

## Testing

Run the test suite:

```bash
# All tests
pytest intelligence/tests/

# Specific test modules
pytest intelligence/tests/test_pattern_detectors.py
pytest intelligence/tests/test_query_generation.py
pytest intelligence/tests/test_integration.py

# With coverage
pytest --cov=intelligence intelligence/tests/
```

## Examples

See the `examples/` directory for comprehensive examples:

- `pattern_detection_example.py`: Complete pattern detection workflow
- `query_generation_example.py`: Natural language query examples
- `visualization_example.py`: Visualization recommendation pipeline

Run examples:

```bash
python -m intelligence.examples.pattern_detection_example
python -m intelligence.examples.query_generation_example
python -m intelligence.examples.visualization_example
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
   ```bash
   pip install -r intelligence/requirements.txt
   ```

2. **spaCy Model Missing**: Download the language model
   ```bash
   python -m spacy download en_core_web_sm
   ```

3. **gRPC Connection Failed**: Check Python service is running
   ```bash
   python -m intelligence.grpc_server
   ```

4. **High Memory Usage**: Adjust sampling configuration
   ```python
   analyzer = DataShapeAnalyzer(config={'sample_size': 1000})
   ```

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

When adding new capabilities:

1. Follow the existing pattern structure
2. Add comprehensive tests
3. Update documentation
4. Include examples
5. Ensure gRPC compatibility

## License

See the main project LICENSE file.
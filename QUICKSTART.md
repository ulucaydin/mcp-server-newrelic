# UDS Quick Start Guide

Get the Universal Data Synthesizer up and running in minutes!

## Prerequisites

- Go 1.21+
- Python 3.9+
- Docker & Docker Compose
- New Relic API Key and Account ID

## Quick Setup

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/anthropics/mcp-server-newrelic.git
cd mcp-server-newrelic

# Set up environment
cp .env.example .env
# Edit .env with your New Relic credentials
```

### 2. Start Intelligence Engine

```bash
# Navigate to intelligence directory
cd intelligence

# Install Python dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Start with Docker (recommended)
./docker-build.sh build
./docker-build.sh run

# Or start directly
python -m intelligence.grpc_server
```

### 3. Build and Run Go Services

```bash
# From root directory
cd ..

# Build Go services
make build

# Run discovery server
./bin/uds-discovery

# In another terminal, run MCP server
./bin/uds-mcp
```

### 4. Test the System

```bash
# Test Intelligence Engine
cd intelligence
python -m intelligence --mode demo

# Test MCP connection
mcp-client connect localhost:3333

# Or use the test script
./scripts/test-integration.sh
```

## Docker Compose (All-in-One)

The easiest way to run everything:

```bash
# From root directory
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Access services:
# - MCP Server: localhost:3333
# - Intelligence gRPC: localhost:50051
# - Prometheus: localhost:9090
# - Grafana: localhost:3000 (admin/admin)
```

## First Steps

### 1. Discover Your Data

```python
# Using MCP tools
from mcp_client import Client

client = Client("localhost:3333")

# Discover all schemas
schemas = client.call_tool("discover_schemas", {})
print(f"Found {len(schemas)} event types")

# Analyze a specific schema
analysis = client.call_tool("analyze_schema", {
    "eventType": "Transaction"
})
print(analysis["insights"])
```

### 2. Natural Language Queries

```python
# Generate NRQL from natural language
result = client.call_tool("nl_to_nrql", {
    "query": "Show me the average response time by service for the last hour"
})

print(f"NRQL: {result['nrql']}")
print(f"Confidence: {result['confidence']}")

# Execute the query
data = client.call_tool("execute_query", {
    "nrql": result['nrql']
})
```

### 3. Pattern Detection

```python
# Detect patterns in your data
patterns = client.call_tool("detect_patterns", {
    "eventType": "Transaction",
    "sampleSize": 1000
})

for pattern in patterns["patterns"]:
    print(f"Found {pattern['type']}: {pattern['description']}")
```

### 4. Create Smart Dashboard

```python
# Generate dashboard from description
dashboard = client.call_tool("create_dashboard", {
    "description": "Application performance monitoring",
    "focus": ["response time", "error rate", "throughput"]
})

print(f"Created dashboard with {len(dashboard['widgets'])} widgets")
```

## Configuration

### Basic Configuration

Create `config/uds.yaml`:

```yaml
# Minimal configuration
discovery:
  sampling:
    default_size: 1000

intelligence:
  grpc:
    port: 50051
  pattern_detection:
    min_confidence: 0.7

nrdb:
  api_key: ${NEW_RELIC_API_KEY}
  account_id: ${NEW_RELIC_ACCOUNT_ID}
```

### Environment Variables

```bash
# Required
export NEW_RELIC_API_KEY="your-api-key"
export NEW_RELIC_ACCOUNT_ID="your-account-id"

# Optional
export INTELLIGENCE_LOG_LEVEL="INFO"
export UDS_CACHE_DIR="/tmp/uds-cache"
export MCP_PORT="3333"
```

## Common Use Cases

### 1. Explore Unknown Data

```bash
# Use the discovery tool
./bin/uds-discovery explore --interactive

# Or via MCP
mcp-client call discover_all_schemas
```

### 2. Monitor Service Performance

```python
# Create performance monitoring queries
queries = [
    "Average response time by service",
    "Error rate trends over time",
    "Top 10 slowest endpoints",
    "Service availability percentage"
]

for query in queries:
    result = client.call_tool("nl_to_nrql", {"query": query})
    print(f"{query}: {result['nrql']}")
```

### 3. Anomaly Detection

```python
# Run anomaly detection
anomalies = client.call_tool("detect_anomalies", {
    "eventType": "Transaction",
    "metrics": ["duration", "errorRate"],
    "lookback": "1 week"
})

for anomaly in anomalies["anomalies"]:
    print(f"Anomaly in {anomaly['metric']} at {anomaly['timestamp']}")
```

## Troubleshooting

### Intelligence Engine Won't Start

```bash
# Check Python version
python --version  # Should be 3.9+

# Install missing dependencies
pip install -r intelligence/requirements.txt

# Check if port is in use
lsof -i :50051
```

### MCP Connection Failed

```bash
# Check if services are running
ps aux | grep uds-mcp

# Test gRPC connection
grpcurl -plaintext localhost:50051 list

# Check logs
tail -f logs/uds-mcp.log
```

### No Data Returned

```bash
# Verify New Relic credentials
curl -X POST https://api.newrelic.com/graphql \
  -H "API-Key: $NEW_RELIC_API_KEY" \
  -d '{"query": "{ actor { account(id: '$NEW_RELIC_ACCOUNT_ID') { name } } }"}'

# Check rate limits
# Look for X-RateLimit headers in response
```

## Examples

### Complete Python Example

```python
#!/usr/bin/env python3
"""UDS Quick Start Example"""

from mcp_client import Client
import json

def main():
    # Connect to UDS
    client = Client("localhost:3333")
    
    # 1. Discover available data
    print("Discovering schemas...")
    schemas = client.call_tool("discover_schemas", {})
    print(f"Found {len(schemas)} event types")
    
    # 2. Pick an interesting schema
    event_type = schemas[0]["name"]
    print(f"\nAnalyzing {event_type}...")
    
    # 3. Detect patterns
    patterns = client.call_tool("detect_patterns", {
        "eventType": event_type,
        "sampleSize": 1000
    })
    
    print(f"Found {len(patterns['patterns'])} patterns:")
    for p in patterns["patterns"][:5]:
        print(f"  - {p['type']}: {p['description']}")
    
    # 4. Generate intelligent queries
    insights = patterns.get("insights", [])
    if insights:
        print(f"\nGenerating query from insight: {insights[0]}")
        result = client.call_tool("nl_to_nrql", {
            "query": insights[0]
        })
        print(f"NRQL: {result['nrql']}")
    
    # 5. Create visualization
    print("\nRecommending visualizations...")
    viz = client.call_tool("recommend_visualizations", {
        "eventType": event_type,
        "goal": "monitoring"
    })
    
    print("Recommended charts:")
    for rec in viz["recommendations"][:3]:
        print(f"  - {rec['chartType']}: {rec['reasoning']}")

if __name__ == "__main__":
    main()
```

### Complete Go Example

```go
package main

import (
    "context"
    "fmt"
    "log"
    
    "github.com/anthropics/mcp-server-newrelic/pkg/discovery"
    "github.com/anthropics/mcp-server-newrelic/pkg/intelligence"
)

func main() {
    ctx := context.Background()
    
    // Initialize services
    disc := discovery.NewSchemaDiscoveryService()
    intel := intelligence.NewClient()
    
    // Discover schemas
    schemas, err := disc.DiscoverAll(ctx)
    if err != nil {
        log.Fatal(err)
    }
    
    fmt.Printf("Found %d schemas\n", len(schemas))
    
    // Analyze first schema
    if len(schemas) > 0 {
        schema := schemas[0]
        
        // Get sample data
        sample, err := disc.GetSample(ctx, schema.EventType, 1000)
        if err != nil {
            log.Fatal(err)
        }
        
        // Detect patterns
        patterns, err := intel.AnalyzePatterns(ctx, sample)
        if err != nil {
            log.Fatal(err)
        }
        
        fmt.Printf("Found %d patterns in %s\n", 
            len(patterns.Patterns), schema.EventType)
    }
}
```

## Next Steps

1. **Explore the Examples**: Check out `intelligence/examples/` for detailed examples
2. **Read the Docs**: See `docs/` for architecture and integration guides
3. **Customize Configuration**: Tune settings in `config/uds.yaml`
4. **Build Dashboards**: Use the visualization recommendations to create dashboards
5. **Set Up Monitoring**: Configure Prometheus/Grafana for production monitoring

## Getting Help

- **Documentation**: See [README.md](README.md) for detailed documentation
- **Examples**: Check `intelligence/examples/` directory
- **Issues**: Report issues on GitHub
- **Logs**: Check `logs/` directory for debugging

## Quick Commands Reference

```bash
# Start everything
docker-compose up -d

# Stop everything
docker-compose down

# View logs
docker-compose logs -f

# Run tests
make test

# Build only
make build

# Clean up
make clean
docker system prune -a
```

Happy exploring with UDS! 🚀
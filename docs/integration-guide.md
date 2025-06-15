# UDS Integration Guide

This guide explains how to integrate all tracks of the Universal Data Synthesizer (UDS) into a cohesive system.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        AI Assistants                             │
│                   (GitHub Copilot, Claude)                       │
└─────────────────────┬───────────────────────────────────────────┘
                      │ MCP Protocol
┌─────────────────────▼───────────────────────────────────────────┐
│                    Track 2: Interface Layer (Go)                 │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │ MCP Server  │  │ A2A Protocol │  │ Tool Orchestration    │ │
│  └─────────────┘  └──────────────┘  └───────────────────────┘ │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                    Track 1: Discovery Core (Go)                  │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │   Schema    │  │  Intelligent │  │    Relationship       │ │
│  │ Discovery   │  │   Sampling   │  │      Mining          │ │
│  └──────┬──────┘  └──────┬───────┘  └───────────┬───────────┘ │
└─────────┼─────────────────┼──────────────────────┼─────────────┘
          │                 │                      │
          └─────────────────┼──────────────────────┘
                           │ gRPC
┌──────────────────────────▼──────────────────────────────────────┐
│                Track 3: Intelligence Engine (Python)             │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │   Pattern   │  │    Query     │  │   Visualization       │ │
│  │ Detection   │  │ Generation   │  │   Intelligence        │ │
│  └─────────────┘  └──────────────┘  └───────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │     NRDB     │
                    └──────────────┘
```

## Integration Points

### 1. Go-Python Communication (Track 1/2 ↔ Track 3)

The Go services communicate with Python Intelligence Engine via gRPC:

```go
// pkg/intelligence/client.go
package intelligence

import (
    "context"
    pb "github.com/anthropics/mcp-server-newrelic/pkg/intelligence/proto"
)

type Client struct {
    grpcClient pb.IntelligenceServiceClient
}

func (c *Client) AnalyzePatterns(ctx context.Context, data []byte) (*PatternResult, error) {
    req := &pb.AnalyzePatternsRequest{
        Data: string(data),
    }
    
    resp, err := c.grpcClient.AnalyzePatterns(ctx, req)
    if err != nil {
        return nil, err
    }
    
    // Parse response
    return parsePatternResult(resp.Result)
}
```

### 2. Discovery to Intelligence Pipeline

```go
// pkg/discovery/intelligence_integration.go
package discovery

import (
    "github.com/anthropics/mcp-server-newrelic/pkg/intelligence"
)

func (s *SchemaDiscoveryService) AnalyzeWithIntelligence(ctx context.Context, schema *Schema) error {
    // Get sample data
    sampleData, err := s.sampler.GetSample(ctx, schema.EventType, 1000)
    if err != nil {
        return err
    }
    
    // Convert to DataFrame format
    dataJSON, err := convertToDataFrame(sampleData)
    if err != nil {
        return err
    }
    
    // Call Intelligence Engine
    client := intelligence.NewClient()
    patterns, err := client.AnalyzePatterns(ctx, dataJSON)
    if err != nil {
        return err
    }
    
    // Enrich schema with patterns
    schema.Patterns = patterns.Patterns
    schema.Insights = patterns.Insights
    
    return nil
}
```

### 3. MCP Tool Integration

```go
// pkg/interface/tools/intelligent_tools.go
package tools

type IntelligentQueryTool struct {
    intelligence *intelligence.Client
}

func (t *IntelligentQueryTool) Execute(ctx context.Context, params map[string]interface{}) (interface{}, error) {
    // Extract natural language query
    nlQuery := params["query"].(string)
    
    // Get query context
    context := buildQueryContext(ctx)
    
    // Generate NRQL
    result, err := t.intelligence.GenerateQuery(ctx, nlQuery, context)
    if err != nil {
        return nil, err
    }
    
    // Execute NRQL
    queryResult, err := executeNRQL(ctx, result.NRQL)
    if err != nil {
        return nil, err
    }
    
    return map[string]interface{}{
        "nrql": result.NRQL,
        "data": queryResult,
        "confidence": result.Confidence,
        "suggestions": result.Suggestions,
    }, nil
}
```

## Complete Workflow Examples

### Example 1: Intelligent Data Discovery

```go
// cmd/examples/intelligent_discovery.go
package main

import (
    "context"
    "fmt"
    
    "github.com/anthropics/mcp-server-newrelic/pkg/discovery"
    "github.com/anthropics/mcp-server-newrelic/pkg/intelligence"
)

func main() {
    ctx := context.Background()
    
    // 1. Initialize services
    discoveryService := discovery.NewSchemaDiscoveryService()
    intelligenceClient := intelligence.NewClient()
    
    // 2. Discover schemas
    schemas, err := discoveryService.DiscoverAll(ctx)
    if err != nil {
        panic(err)
    }
    
    // 3. Analyze each schema with intelligence
    for _, schema := range schemas {
        // Get sample data
        sample, err := discoveryService.GetSample(ctx, schema.EventType, 1000)
        if err != nil {
            continue
        }
        
        // Analyze patterns
        patterns, err := intelligenceClient.AnalyzePatterns(ctx, sample)
        if err != nil {
            continue
        }
        
        // Generate insights
        fmt.Printf("Schema: %s\n", schema.EventType)
        fmt.Printf("Patterns found: %d\n", len(patterns.Patterns))
        for _, insight := range patterns.Insights {
            fmt.Printf("  - %s\n", insight)
        }
        
        // Generate optimized queries
        for _, pattern := range patterns.Patterns {
            if pattern.Type == "anomaly" {
                // Generate anomaly detection query
                query := fmt.Sprintf("Find anomalies in %s for %s", 
                    pattern.Columns[0], schema.EventType)
                
                result, err := intelligenceClient.GenerateQuery(ctx, query, nil)
                if err == nil {
                    fmt.Printf("  Anomaly Query: %s\n", result.NRQL)
                }
            }
        }
    }
}
```

### Example 2: Natural Language Dashboard Creation

```go
// cmd/examples/nl_dashboard.go
package main

func createDashboardFromNL(ctx context.Context, description string) (*Dashboard, error) {
    // 1. Parse dashboard intent
    intent := "Create a dashboard for " + description
    
    // 2. Generate queries
    queries := []string{
        "Show key metrics for " + description,
        "Error rate trends for " + description,
        "Performance metrics for " + description,
        "Top issues in " + description,
    }
    
    widgets := []*Widget{}
    
    for _, query := range queries {
        // Generate NRQL
        result, err := intelligenceClient.GenerateQuery(ctx, query, nil)
        if err != nil {
            continue
        }
        
        // Get data shape
        data, err := executeNRQL(ctx, result.NRQL)
        if err != nil {
            continue
        }
        
        // Analyze data shape
        shape, err := intelligenceClient.AnalyzeDataShape(ctx, data)
        if err != nil {
            continue
        }
        
        // Get chart recommendations
        recommendations, err := intelligenceClient.RecommendCharts(ctx, shape)
        if err != nil {
            continue
        }
        
        // Create widget
        if len(recommendations) > 0 {
            widget := &Widget{
                Title:     query,
                ChartType: recommendations[0].ChartType,
                Query:     result.NRQL,
            }
            widgets = append(widgets, widget)
        }
    }
    
    // 3. Optimize layout
    layout, err := intelligenceClient.OptimizeLayout(ctx, widgets, nil)
    if err != nil {
        return nil, err
    }
    
    // 4. Create dashboard
    dashboard := &Dashboard{
        Title:   description + " Dashboard",
        Widgets: widgets,
        Layout:  layout,
    }
    
    return dashboard, nil
}
```

## Configuration

### Unified Configuration

Create a unified configuration file for all components:

```yaml
# config/uds.yaml

# Discovery Core Configuration
discovery:
  sampling:
    default_size: 1000
    max_size: 10000
    strategies:
      - adaptive
      - stratified
  caching:
    enabled: true
    ttl: 3600

# Interface Layer Configuration  
interface:
  mcp:
    port: 3333
    max_connections: 100
  a2a:
    enabled: true
    auth_required: true

# Intelligence Engine Configuration
intelligence:
  grpc:
    host: localhost
    port: 50051
  pattern_detection:
    min_confidence: 0.7
    enable_all: true
  query_generation:
    optimizer_mode: balanced
    cache_size: 100

# NRDB Configuration
nrdb:
  api_key: ${NEW_RELIC_API_KEY}
  account_id: ${NEW_RELIC_ACCOUNT_ID}
  region: US
  rate_limit: 100
```

### Environment Setup

```bash
# .env file
NEW_RELIC_API_KEY=your-api-key
NEW_RELIC_ACCOUNT_ID=your-account-id

# Intelligence Engine
INTELLIGENCE_GRPC_PORT=50051
INTELLIGENCE_LOG_LEVEL=INFO

# Discovery Core
DISCOVERY_CACHE_DIR=/var/cache/uds
DISCOVERY_LOG_LEVEL=INFO

# Interface Layer
MCP_PORT=3333
MCP_LOG_LEVEL=INFO
```

## Deployment

### Docker Compose Full Stack

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Intelligence Engine (Python)
  intelligence:
    build: ./intelligence
    ports:
      - "50051:50051"
      - "8080:8080"
    volumes:
      - ./config:/app/config:ro
      - intelligence-models:/app/models
    environment:
      - INTELLIGENCE_LOG_LEVEL=INFO

  # Discovery Core & Interface (Go)
  uds-core:
    build: .
    ports:
      - "3333:3333"  # MCP
      - "8081:8081"  # Metrics
    volumes:
      - ./config:/app/config:ro
    environment:
      - NEW_RELIC_API_KEY=${NEW_RELIC_API_KEY}
      - NEW_RELIC_ACCOUNT_ID=${NEW_RELIC_ACCOUNT_ID}
      - INTELLIGENCE_GRPC_ENDPOINT=intelligence:50051
    depends_on:
      - intelligence

  # Prometheus
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    depends_on:
      - intelligence
      - uds-core

  # Grafana
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    depends_on:
      - prometheus

volumes:
  intelligence-models:
```

### Production Deployment

For production deployments, we recommend:

1. **Container Orchestration**: Use Docker Swarm or a managed container service
2. **Load Balancing**: Deploy multiple instances behind a load balancer
3. **Service Mesh**: Consider using a service mesh for internal communication
4. **Resource Limits**: Set appropriate CPU and memory limits:
   - Intelligence Engine: 1-2GB RAM, 500m-1 CPU
   - UDS Core: 512MB-1GB RAM, 250m-500m CPU
5. **Monitoring**: Enable Prometheus metrics and integrate with your monitoring stack

## Testing Integration

### End-to-End Test Suite

```go
// tests/integration/e2e_test.go
package integration

import (
    "testing"
    "context"
)

func TestCompleteDiscoveryPipeline(t *testing.T) {
    ctx := context.Background()
    
    // Start services
    startIntelligenceEngine(t)
    startDiscoveryCore(t)
    startMCPServer(t)
    
    // Test discovery
    t.Run("DiscoverSchemas", func(t *testing.T) {
        schemas, err := discoverAllSchemas(ctx)
        assert.NoError(t, err)
        assert.NotEmpty(t, schemas)
    })
    
    // Test pattern detection
    t.Run("DetectPatterns", func(t *testing.T) {
        patterns, err := analyzePatterns(ctx, sampleData)
        assert.NoError(t, err)
        assert.NotEmpty(t, patterns)
    })
    
    // Test query generation
    t.Run("GenerateQueries", func(t *testing.T) {
        query := "Show me error trends"
        result, err := generateQuery(ctx, query)
        assert.NoError(t, err)
        assert.NotEmpty(t, result.NRQL)
    })
    
    // Test visualization
    t.Run("RecommendCharts", func(t *testing.T) {
        recommendations, err := recommendCharts(ctx, sampleData)
        assert.NoError(t, err)
        assert.NotEmpty(t, recommendations)
    })
}
```

## Monitoring & Observability

### Unified Metrics

All components expose Prometheus metrics:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'intelligence-engine'
    static_configs:
      - targets: ['intelligence:8080']
      
  - job_name: 'uds-core'
    static_configs:
      - targets: ['uds-core:8081']
```

### Key Metrics to Monitor

1. **Discovery Core**
   - `uds_schemas_discovered_total`
   - `uds_discovery_duration_seconds`
   - `uds_nrdb_queries_total`

2. **Intelligence Engine**
   - `intelligence_patterns_detected_total`
   - `intelligence_queries_generated_total`
   - `intelligence_operation_duration_seconds`

3. **Interface Layer**
   - `mcp_requests_total`
   - `mcp_request_duration_seconds`
   - `a2a_messages_total`

## Troubleshooting

### Common Integration Issues

1. **gRPC Connection Failed**
   ```bash
   # Check if Intelligence Engine is running
   grpcurl -plaintext localhost:50051 list
   
   # Check logs
   docker logs intelligence
   ```

2. **Pattern Detection Timeout**
   ```yaml
   # Increase timeout in Go client
   ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
   ```

3. **Memory Issues**
   ```yaml
   # Increase container limits
   resources:
     limits:
       memory: "4Gi"
   ```

## Best Practices

1. **Use Circuit Breakers**
   ```go
   breaker := circuit.NewBreaker(circuit.Config{
       Timeout: 30 * time.Second,
       MaxConcurrent: 10,
   })
   ```

2. **Implement Retries**
   ```go
   retry.Do(func() error {
       return intelligenceClient.AnalyzePatterns(ctx, data)
   }, retry.Attempts(3), retry.Delay(time.Second))
   ```

3. **Cache Intelligence Results**
   ```go
   cache := ttlcache.New(ttlcache.WithTTL(time.Hour))
   ```

4. **Monitor Resource Usage**
   ```go
   metrics.RecordMemoryUsage()
   metrics.RecordGoroutineCount()
   ```

## Next Steps

1. Complete remaining Track 1 & 2 features
2. Build comprehensive integration tests
3. Performance optimization
4. Security hardening
5. Production deployment preparation
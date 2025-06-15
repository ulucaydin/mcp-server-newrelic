# Architecture Integration: Go Discovery Engine + Python MCP Server

## Overview

This document describes the architecture and integration strategy between the Go-based Discovery Engine (Track 1) and the Python-based MCP Server (Track 2). The hybrid architecture leverages the strengths of both languages while maintaining a clean separation of concerns.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AI Assistant (Claude, etc)                    │
└────────────────────────────┬────────────────────────────────────────┘
                             │ MCP Protocol
┌────────────────────────────▼────────────────────────────────────────┐
│                     Python MCP Server                                │
│  ┌────────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │  MCP Handler   │  │ Tool Registry │  │  Discovery Client      │  │
│  │  (FastMCP)     │  │  (Plugins)    │  │  (gRPC Client)         │  │
│  └────────────────┘  └──────────────┘  └───────────┬──────────┘  │
└─────────────────────────────────────────────────────┼──────────────┘
                                                      │ gRPC
┌─────────────────────────────────────────────────────▼──────────────┐
│                      Go Discovery Engine                            │
│  ┌────────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │ gRPC Server    │  │  Discovery   │  │  NRDB Client           │  │
│  │                │  │  Engine      │  │  (Resilient)           │  │
│  └────────────────┘  └──────────────┘  └───────────┬──────────┘  │
│  ┌────────────────┐  ┌──────────────┐              │              │
│  │ Pattern        │  │  Quality     │              │              │
│  │ Detection      │  │  Assessment  │              │              │
│  └────────────────┘  └──────────────┘              │              │
└─────────────────────────────────────────────────────┼──────────────┘
                                                      │ HTTPS
                                                      ▼
                                            ┌─────────────────┐
                                            │  New Relic API  │
                                            └─────────────────┘
```

## Component Responsibilities

### Python MCP Server (Track 2)
- **Primary Role**: AI-facing interface and tool orchestration
- **Responsibilities**:
  - MCP protocol implementation and handshake
  - Tool registration and metadata management
  - Request routing and response formatting
  - Simple, direct New Relic API calls
  - Integration with Discovery Engine for advanced features

### Go Discovery Engine (Track 1)
- **Primary Role**: High-performance data analysis and discovery
- **Responsibilities**:
  - Schema discovery and profiling
  - Pattern detection and mining
  - Relationship analysis
  - Data quality assessment
  - Caching and performance optimization
  - Resilient API communication (circuit breakers, retries)

## Integration Points

### 1. gRPC Interface
The primary integration mechanism between Python and Go components:

```protobuf
service DiscoveryService {
  rpc DiscoverSchemas(DiscoverSchemasRequest) returns (DiscoverSchemasResponse);
  rpc ProfileSchema(ProfileSchemaRequest) returns (ProfileSchemaResponse);
  rpc IntelligentDiscovery(IntelligentDiscoveryRequest) returns (IntelligentDiscoveryResponse);
  rpc FindRelationships(FindRelationshipsRequest) returns (FindRelationshipsResponse);
  rpc AssessQuality(AssessQualityRequest) returns (AssessQualityResponse);
  rpc GetHealth(GetHealthRequest) returns (GetHealthResponse);
}
```

### 2. Discovery Client (Python)
Python client library that wraps gRPC calls:

```python
from discovery_client import DiscoveryClient

client = DiscoveryClient(host="localhost", port=8081)
schemas = client.discover_schemas(account_id="123456")
```

### 3. Tool Registration
MCP tools that leverage the Discovery Engine:

```python
@mcp_server.tool()
async def discover_schemas(account_id: str, pattern: str = "") -> list:
    """Discover available schemas using intelligent analysis"""
    return discovery_integration.discover_schemas_for_mcp(account_id, pattern=pattern)

@mcp_server.tool()
async def analyze_data_quality(event_type: str) -> dict:
    """Analyze data quality for a specific event type"""
    return discovery_integration.analyze_schema_for_mcp(event_type)
```

## Deployment Options

### Option 1: Sidecar Pattern (Recommended)
- Deploy Go Discovery Engine as a sidecar container
- Python MCP Server communicates via localhost gRPC
- Benefits: Low latency, shared lifecycle, easy scaling

```yaml
version: '3.8'
services:
  mcp-server:
    image: mcp-server-newrelic:latest
    environment:
      DISCOVERY_ENGINE_HOST: localhost
      DISCOVERY_ENGINE_PORT: 8081
    ports:
      - "8080:8080"
  
  discovery-engine:
    image: discovery-engine:latest
    environment:
      NEW_RELIC_API_KEY: ${NEW_RELIC_API_KEY}
      OTEL_ENABLED: true
    ports:
      - "8081:8081"
```

### Option 2: Separate Services
- Deploy as independent services
- Communicate over network gRPC
- Benefits: Independent scaling, language-specific optimization

### Option 3: Embedded Library (Future)
- Compile Go code as C-compatible library
- Use Python ctypes or cgo bindings
- Benefits: Single process, minimal latency

## Configuration Management

### Environment Variables
Shared configuration through environment:

```bash
# New Relic Configuration
NEW_RELIC_API_KEY=xxx
NEW_RELIC_ACCOUNT_ID=123456
NEW_RELIC_REGION=US

# Discovery Engine
DISCOVERY_ENGINE_HOST=localhost
DISCOVERY_ENGINE_PORT=8081
DISCOVERY_WORKER_COUNT=10
DISCOVERY_CACHE_TTL=5m

# MCP Server
MCP_SERVER_PORT=8080
MCP_MAX_REQUEST_SIZE=10MB

# Observability
OTEL_ENABLED=true
OTEL_SERVICE_NAME=mcp-server-newrelic
```

### Feature Flags
Control which tools use the Discovery Engine:

```python
FEATURE_FLAGS = {
    "use_discovery_engine": True,
    "enable_pattern_detection": True,
    "enable_quality_assessment": True,
    "enable_intelligent_discovery": False,  # Still in beta
}
```

## Error Handling and Fallbacks

### Graceful Degradation
When Discovery Engine is unavailable:

```python
async def discover_schemas_with_fallback(account_id: str) -> list:
    try:
        # Try Discovery Engine first
        return discovery_integration.discover_schemas_for_mcp(account_id)
    except DiscoveryEngineError:
        # Fall back to direct NRQL query
        return await query_schemas_directly(account_id)
```

### Circuit Breaker Pattern
Both components implement circuit breakers:
- Go: Built into NRDB client
- Python: At gRPC client level

## Observability

### Distributed Tracing
OpenTelemetry traces span both components:

```
[Python MCP Tool Call]
  └─[gRPC Call to Discovery Engine]
      └─[Schema Discovery]
          └─[NRDB Query 1]
          └─[NRDB Query 2]
          └─[Pattern Detection]
```

### Metrics Collection
- Python: Request counts, latencies, error rates
- Go: Query performance, cache hits, pattern detection times
- Both export to New Relic APM

### Health Checks
Consolidated health endpoint:

```python
@app.get("/health")
async def health():
    mcp_health = check_mcp_server_health()
    discovery_health = discovery_client.get_health()
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "components": {
            "mcp_server": mcp_health,
            "discovery_engine": discovery_health,
        }
    }
```

## Development Workflow

### Local Development
1. Start Discovery Engine:
   ```bash
   cd /path/to/discovery
   go run cmd/uds-discovery/main.go
   ```

2. Start MCP Server:
   ```bash
   cd /path/to/mcp-server
   python main.py
   ```

### Testing Integration
- Unit tests mock gRPC calls
- Integration tests use real Discovery Engine
- End-to-end tests verify full flow

## Migration Strategy

### Phase 1: Parallel Operation
- Both Python and Go components active
- New tools use Discovery Engine
- Existing tools unchanged

### Phase 2: Gradual Migration
- Migrate high-value tools to use Discovery Engine
- Monitor performance and reliability
- Gather user feedback

### Phase 3: Full Integration
- All applicable tools use Discovery Engine
- Python handles only MCP protocol and simple tools
- Go handles all complex analysis

## Performance Considerations

### Latency Budget
- MCP request timeout: 30s
- gRPC call timeout: 25s
- NRDB query timeout: 20s
- Pattern detection timeout: 15s

### Resource Allocation
- Python: 2 CPU, 4GB RAM (handles many concurrent connections)
- Go: 4 CPU, 8GB RAM (CPU-intensive analysis)
- Adjust based on workload

### Caching Strategy
- Go: In-memory cache for schema metadata
- Python: Simple cache for gRPC responses
- Shared Redis for distributed deployment

## Security Considerations

### API Key Management
- Stored securely in environment
- Never passed between components
- Each component manages its own credentials

### gRPC Security
- TLS for production deployments
- mTLS for zero-trust environments
- API key or JWT for authentication

### Data Privacy
- No sensitive data logged
- PII scrubbing in error messages
- Audit logs for compliance

## Future Enhancements

### Short Term
- [ ] Implement streaming gRPC for real-time updates
- [ ] Add request batching for efficiency
- [ ] Enhance error messages with remediation steps

### Medium Term
- [ ] A2A protocol support
- [ ] Multi-tenant architecture
- [ ] Advanced caching with ML-based prefetch

### Long Term
- [ ] Unified codebase (evaluate Go for entire stack)
- [ ] Plugin architecture for custom analyzers
- [ ] Self-learning pattern detection

## Conclusion

The hybrid Python-Go architecture provides the best of both worlds:
- Python's excellent AI integration capabilities
- Go's performance for data-intensive operations
- Clean separation allowing independent evolution
- Graceful degradation ensuring reliability

This architecture positions the MCP server for future growth while maintaining compatibility with the existing ecosystem.
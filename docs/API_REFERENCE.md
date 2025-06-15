# API Reference

## Table of Contents
1. [MCP Protocol](#mcp-protocol)
2. [Discovery Engine API](#discovery-engine-api)
3. [REST API Endpoints](#rest-api-endpoints)
4. [gRPC Services](#grpc-services)
5. [Client Libraries](#client-libraries)
6. [Error Handling](#error-handling)
7. [Rate Limiting](#rate-limiting)

## MCP Protocol

The MCP (Model Context Protocol) server exposes tools that can be invoked by AI assistants. All tools follow a consistent request/response pattern.

### Tool Invocation

```json
{
  "tool": "tool_name",
  "arguments": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

### Available Tools

#### Schema Discovery Tools

##### `discover_schemas`
Discover available schemas in a New Relic account.

**Arguments:**
- `account_id` (string, required): New Relic account ID
- `pattern` (string, optional): Filter pattern for schema names
- `max_schemas` (int, optional): Maximum schemas to return (default: 100)
- `event_types` (array, optional): Specific event types to include

**Response:**
```json
{
  "schemas": [
    {
      "name": "Transaction",
      "event_type": "Transaction",
      "attributes": [
        {
          "name": "duration",
          "data_type": "float",
          "semantic_type": "duration"
        }
      ],
      "sample_count": 1000000,
      "quality_score": 0.85
    }
  ],
  "total_count": 42,
  "discovery_duration_ms": 1234
}
```

##### `profile_schema`
Get detailed profile of a specific schema.

**Arguments:**
- `event_type` (string, required): Event type to profile
- `profile_depth` (string, optional): "basic", "standard", or "deep" (default: "standard")
- `include_patterns` (bool, optional): Include pattern detection (default: true)
- `include_quality` (bool, optional): Include quality assessment (default: true)

**Response:**
```json
{
  "schema": {
    "name": "Transaction",
    "event_type": "Transaction",
    "attributes": [...],
    "patterns": [
      {
        "type": "time_series",
        "subtype": "seasonal",
        "confidence": 0.85,
        "description": "Daily seasonality detected"
      }
    ],
    "quality": {
      "overall_score": 0.82,
      "dimensions": {
        "completeness": 0.88,
        "consistency": 0.79,
        "timeliness": 0.91,
        "uniqueness": 0.85,
        "validity": 0.67
      }
    }
  }
}
```

#### Query Tools

##### `run_nrql_query`
Execute a NRQL query.

**Arguments:**
- `query` (string, required): NRQL query to execute
- `account_id` (string, optional): Override default account
- `timeout` (int, optional): Query timeout in seconds (default: 30)

**Response:**
```json
{
  "results": [...],
  "metadata": {
    "facets": [...],
    "totalResult": {...}
  },
  "performanceStats": {
    "inspectedCount": 1000000,
    "omittedCount": 0,
    "matchCount": 500000,
    "wallClockTime": 234
  }
}
```

##### `search_entities`
Search for entities across New Relic.

**Arguments:**
- `query` (string, optional): Search query
- `entity_types` (array, optional): Filter by entity types
- `tags` (object, optional): Filter by tags
- `limit` (int, optional): Maximum results (default: 100)

**Response:**
```json
{
  "entities": [
    {
      "guid": "abc123",
      "name": "production-api",
      "type": "APPLICATION",
      "tags": {
        "environment": "production",
        "team": "platform"
      }
    }
  ],
  "total_count": 42
}
```

#### APM Tools

##### `list_apm_applications`
List APM applications.

**Arguments:**
- `account_id` (string, optional): Filter by account
- `name_filter` (string, optional): Filter by name pattern
- `language` (string, optional): Filter by language

**Response:**
```json
{
  "applications": [
    {
      "id": "123456",
      "name": "production-api",
      "language": "java",
      "health_status": "green",
      "reporting": true,
      "throughput": 1000.5,
      "response_time": 45.2,
      "error_rate": 0.01
    }
  ]
}
```

##### `get_apm_metrics`
Get metrics for an APM application.

**Arguments:**
- `app_id` (string, required): Application ID
- `metric_names` (array, required): Metrics to retrieve
- `time_range` (object, optional): Time range specification
- `summarize` (bool, optional): Return summarized data

**Response:**
```json
{
  "metrics": {
    "HttpDispatcher": {
      "call_count": 1000000,
      "total_call_time": 45000,
      "average_response_time": 45,
      "min_response_time": 10,
      "max_response_time": 500
    }
  }
}
```

#### Infrastructure Tools

##### `list_hosts`
List infrastructure hosts.

**Arguments:**
- `account_id` (string, optional): Filter by account
- `hostname_filter` (string, optional): Filter by hostname
- `tags` (object, optional): Filter by tags

**Response:**
```json
{
  "hosts": [
    {
      "hostname": "web-server-01",
      "system_info": {
        "cpu_cores": 8,
        "ram_gb": 32,
        "os": "Ubuntu 20.04"
      },
      "metrics": {
        "cpu_percent": 45.2,
        "memory_percent": 67.8,
        "disk_percent": 23.4
      }
    }
  ]
}
```

## Discovery Engine API

The Discovery Engine provides advanced data analysis capabilities through a gRPC interface.

### Service Definition

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

### Intelligent Discovery

##### `IntelligentDiscovery`
AI-guided schema discovery with insights.

**Request:**
```json
{
  "focus_areas": ["errors", "performance"],
  "event_types": ["Transaction", "TransactionError"],
  "anomaly_detection": true,
  "pattern_mining": true,
  "quality_assessment": true,
  "confidence_threshold": 0.7,
  "context": {
    "user_intent": "troubleshoot slow response times"
  }
}
```

**Response:**
```json
{
  "schemas": [...],
  "insights": [
    {
      "type": "anomaly",
      "severity": "high",
      "title": "Unusual spike in error rates",
      "description": "Error rate increased by 300% in the last hour",
      "affected_schemas": ["Transaction"],
      "confidence": 0.92
    }
  ],
  "recommendations": [
    "Investigate errors in checkout service",
    "Check database connection pool settings"
  ]
}
```

## REST API Endpoints

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "components": {
    "mcp_server": {
      "status": "healthy",
      "uptime": 3600
    },
    "discovery_engine": {
      "status": "healthy",
      "queries_processed": 10000,
      "cache_hit_rate": 0.75
    }
  },
  "timestamp": "2024-12-20T10:00:00Z"
}
```

### Metrics

```http
GET /metrics
```

Returns Prometheus-formatted metrics:
```
# HELP mcp_requests_total Total number of MCP requests
# TYPE mcp_requests_total counter
mcp_requests_total{tool="discover_schemas",status="success"} 1234

# HELP discovery_query_duration_seconds Query duration in seconds
# TYPE discovery_query_duration_seconds histogram
discovery_query_duration_seconds_bucket{le="0.1"} 100
discovery_query_duration_seconds_bucket{le="0.5"} 950
discovery_query_duration_seconds_bucket{le="1.0"} 990
```

## gRPC Services

### Connection

```go
// Go client example
conn, err := grpc.Dial("localhost:8081", grpc.WithInsecure())
client := pb.NewDiscoveryServiceClient(conn)

// Python client example
channel = grpc.insecure_channel('localhost:8081')
stub = discovery_pb2_grpc.DiscoveryServiceStub(channel)
```

### Authentication

Include API key in metadata:
```go
// Go
md := metadata.Pairs("authorization", "Bearer " + apiKey)
ctx := metadata.NewOutgoingContext(context.Background(), md)

// Python
metadata = [('authorization', f'Bearer {api_key}')]
response = stub.DiscoverSchemas(request, metadata=metadata)
```

## Client Libraries

### Python Client

```python
from discovery_client import DiscoveryClient

# Initialize client
client = DiscoveryClient(host="localhost", port=8081)

# Discover schemas
schemas = client.discover_schemas(
    account_id="123456",
    pattern="Transaction",
    max_schemas=50
)

# Profile schema
profile = client.profile_schema(
    event_type="Transaction",
    profile_depth="deep",
    include_patterns=True
)

# Find relationships
relationships = client.find_relationships(
    schema_names=["Transaction", "TransactionError"],
    min_confidence=0.7
)
```

### Go Client

```go
import "github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery"

// Create client
client, err := discovery.NewClient(discovery.Config{
    Endpoint: "localhost:8081",
    APIKey:   "your-api-key",
})

// Discover schemas
schemas, err := client.DiscoverSchemas(ctx, discovery.DiscoveryFilter{
    AccountID:  "123456",
    Pattern:    "Transaction",
    MaxSchemas: 50,
})
```

### JavaScript/TypeScript Client (Planned)

```typescript
import { DiscoveryClient } from '@newrelic/discovery-client';

const client = new DiscoveryClient({
  host: 'localhost',
  port: 8081,
  apiKey: 'your-api-key'
});

// Async/await syntax
const schemas = await client.discoverSchemas({
  accountId: '123456',
  pattern: 'Transaction'
});
```

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Rate limit exceeded",
    "details": {
      "limit": 100,
      "window": "1m",
      "retry_after": 45
    }
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_REQUEST` | 400 | Invalid request parameters |
| `UNAUTHORIZED` | 401 | Missing or invalid authentication |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMITED` | 429 | Rate limit exceeded |
| `INTERNAL_ERROR` | 500 | Internal server error |
| `UNAVAILABLE` | 503 | Service temporarily unavailable |

### Retry Strategy

```python
# Example retry with exponential backoff
import time
from typing import Any, Callable

def retry_with_backoff(
    func: Callable,
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0
) -> Any:
    delay = initial_delay
    
    for attempt in range(max_attempts):
        try:
            return func()
        except RateLimitError as e:
            if attempt == max_attempts - 1:
                raise
            
            wait_time = min(delay, max_delay)
            time.sleep(wait_time)
            delay *= exponential_base
```

## Rate Limiting

### Default Limits

| Resource | Limit | Window |
|----------|-------|--------|
| MCP Tool Calls | 100 | 1 minute |
| Discovery API | 50 | 1 minute |
| NRQL Queries | 30 | 1 minute |
| Bulk Operations | 10 | 1 minute |

### Rate Limit Headers

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1703080800
X-RateLimit-Window: 60
```

### Handling Rate Limits

```python
async def call_with_rate_limit_handling(tool_name: str, args: dict):
    try:
        return await mcp_client.call_tool(tool_name, args)
    except RateLimitError as e:
        retry_after = e.retry_after
        logger.warning(f"Rate limited. Retrying after {retry_after}s")
        await asyncio.sleep(retry_after)
        return await mcp_client.call_tool(tool_name, args)
```

## Webhooks (Planned)

### Webhook Configuration

```json
{
  "url": "https://your-app.com/webhooks/discovery",
  "events": ["schema.discovered", "quality.degraded"],
  "secret": "webhook-secret-key"
}
```

### Webhook Payload

```json
{
  "event": "schema.discovered",
  "timestamp": "2024-12-20T10:00:00Z",
  "data": {
    "schema_name": "NewEventType",
    "account_id": "123456",
    "attributes_count": 25
  }
}
```

## API Versioning

The API uses URL versioning:
- Current version: `/v1/`
- Legacy support: Maintained for 6 months
- Deprecation notices: Sent via headers

```http
Sunset: Sat, 01 Jun 2025 00:00:00 GMT
Deprecation: true
Link: <https://api.example.com/v2/docs>; rel="successor-version"
```
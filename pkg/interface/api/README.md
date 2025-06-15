# REST API Implementation

This package implements the REST API for the New Relic UDS Interface Layer. The API provides HTTP endpoints for discovery, pattern analysis, query generation, and dashboard creation.

## Architecture

### Core Components

1. **Server** (`server.go`) - HTTP server with routing and middleware
2. **Handlers** (`handlers.go`) - Request handlers for all endpoints
3. **Middleware** (`middleware.go`) - Cross-cutting concerns:
   - Request logging
   - Request ID generation
   - Panic recovery
   - CORS support
   - Rate limiting
   - Request size limiting
4. **OpenAPI Spec** (`openapi.yaml`) - Complete API specification

### Build Tags

Similar to the MCP implementation, we use build tags to isolate from Track 1:

- `nodiscovery` - Builds without discovery dependencies (for testing)
- Default build includes full discovery integration

## Running the API Server

### Development Mode

```bash
# Run with default settings
go run cmd/api-server/main.go

# Run with custom configuration
go run cmd/api-server/main.go \
  --host 0.0.0.0 \
  --port 8080 \
  --cors \
  --swagger \
  --rate-limit 100
```

### Testing

Run tests in isolation from Track 1:
```bash
go test -tags="nodiscovery" -v ./pkg/interface/api/...
```

## API Endpoints

### Health
- `GET /api/v1/health` - Check service health

### Discovery
- `GET /api/v1/discovery/schemas` - List available schemas
- `GET /api/v1/discovery/schemas/{eventType}` - Get detailed schema profile
- `POST /api/v1/discovery/relationships` - Find relationships between schemas
- `GET /api/v1/discovery/quality/{eventType}` - Assess data quality

### Patterns (Track 3)
- `POST /api/v1/patterns/analyze` - Analyze patterns in data

### Query (Track 3)
- `POST /api/v1/query/generate` - Generate NRQL from natural language

### Dashboard (Track 4)
- `POST /api/v1/dashboard/create` - Create dashboard from specification

## Example Requests

### List Schemas
```bash
curl http://localhost:8080/api/v1/discovery/schemas?includeMetadata=true
```

### Get Schema Profile
```bash
curl http://localhost:8080/api/v1/discovery/schemas/Transaction?depth=full
```

### Find Relationships
```bash
curl -X POST http://localhost:8080/api/v1/discovery/relationships \
  -H "Content-Type: application/json" \
  -d '{
    "schemas": ["Transaction", "PageView"],
    "options": {
      "maxRelationships": 10,
      "minConfidence": 0.7
    }
  }'
```

### Assess Quality
```bash
curl http://localhost:8080/api/v1/discovery/quality/Transaction?timeRange=24h
```

## Configuration

### Server Options

| Flag | Default | Description |
|------|---------|-------------|
| `--host` | localhost | Server host |
| `--port` | 8080 | Server port |
| `--cors` | true | Enable CORS |
| `--swagger` | true | Enable Swagger UI |
| `--rate-limit` | 100 | Requests per minute (0 to disable) |
| `--max-request-size` | 1MB | Maximum request body size |
| `--read-timeout` | 30s | HTTP read timeout |
| `--write-timeout` | 30s | HTTP write timeout |

## Middleware

### Request Logging
All requests are logged with:
- Method and path
- Client IP
- Response status
- Request duration
- Request ID

### Rate Limiting
- Per-IP rate limiting
- Configurable requests per minute
- Burst capacity of 10 requests
- Returns 429 Too Many Requests when exceeded

### CORS
When enabled, allows:
- All origins (configurable in production)
- Common HTTP methods
- All headers
- Credentials

### Request ID
- Generates unique ID for each request
- Propagated via `X-Request-ID` header
- Available in request context

## Integration with Track 1

When Track 1 is ready, integrate by:

```go
// In main.go
discoveryEngine := discovery.NewEngine(config)
handler.SetDiscoveryEngine(discoveryEngine)
```

## OpenAPI/Swagger

The API is fully documented using OpenAPI 3.0:

1. View spec: `http://localhost:8080/openapi.yaml`
2. Interactive UI: `http://localhost:8080/swagger/`

## Error Handling

All errors follow a consistent format:

```json
{
  "error": "error_type",
  "message": "Human readable message",
  "details": {
    // Additional context
  }
}
```

Standard HTTP status codes:
- 200 OK - Success
- 201 Created - Resource created
- 400 Bad Request - Invalid input
- 404 Not Found - Resource not found
- 429 Too Many Requests - Rate limited
- 500 Internal Server Error - Server error
- 503 Service Unavailable - Service not ready

## Security Considerations

1. **Rate Limiting** - Prevents abuse
2. **Request Size Limits** - Prevents DoS
3. **CORS Configuration** - Control client access
4. **Input Validation** - All inputs validated
5. **Error Sanitization** - No sensitive data in errors

## Performance

- Concurrent request handling
- Connection pooling (when integrated with Track 1)
- Response caching (future enhancement)
- Efficient JSON serialization

## Testing

The package includes comprehensive tests:
- Server lifecycle
- All endpoint handlers
- Middleware functionality
- Error handling
- Rate limiting

Current test coverage: ~70%

## Future Enhancements

1. **Authentication/Authorization** - JWT or API keys
2. **Response Caching** - Redis-based caching
3. **Metrics Collection** - Prometheus metrics
4. **Request Tracing** - OpenTelemetry support
5. **WebSocket Support** - Real-time updates
6. **GraphQL Alternative** - For complex queries
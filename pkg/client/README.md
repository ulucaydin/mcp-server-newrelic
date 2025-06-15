# UDS Go Client Library

A Go client library for the New Relic Unified Data Service (UDS) API with built-in retry logic, comprehensive error handling, and full type safety.

## Installation

```bash
go get github.com/deepaucksharma/mcp-server-newrelic/pkg/client
```

## Quick Start

```go
package main

import (
    "context"
    "log"
    "time"
    
    "github.com/deepaucksharma/mcp-server-newrelic/pkg/client"
)

func main() {
    // Create client
    c, err := client.NewClient(client.Config{
        BaseURL:   "http://localhost:8080/api/v1",
        APIKey:    "your-api-key", // Optional for now
        Timeout:   30 * time.Second,
        RetryMax:  3,
        RetryWait: 1 * time.Second,
    })
    if err != nil {
        log.Fatal(err)
    }
    
    ctx := context.Background()
    
    // List schemas
    schemas, err := c.Discovery.ListSchemas(ctx, nil)
    if err != nil {
        log.Fatal(err)
    }
    
    for _, schema := range schemas.Schemas {
        log.Printf("Schema: %s, Records: %d", schema.Name, schema.RecordCount)
    }
}
```

## Features

### 🔄 Automatic Retry Logic
- Exponential backoff with jitter
- Configurable max retries and wait time
- Retries on network errors and specific HTTP status codes
- Respects context cancellation

### 🛡️ Error Handling
- Typed errors for API responses
- Detailed error messages with status codes
- Request/response logging (when enabled)

### 🚀 Performance
- Connection pooling
- Concurrent requests support
- Efficient JSON marshaling/unmarshaling
- Minimal allocations

### 📦 Type Safety
- Full Go structs for all API requests/responses
- No interface{} in public API
- Compile-time type checking

## Configuration

### Client Options

```go
config := client.Config{
    // API endpoint (default: http://localhost:8080/api/v1)
    BaseURL: "https://uds.newrelic.com/api/v1",
    
    // API key for authentication (optional for now)
    APIKey: "your-api-key",
    
    // Custom HTTP client (optional)
    HTTPClient: &http.Client{
        Transport: &http.Transport{
            MaxIdleConns:    100,
            IdleConnTimeout: 90 * time.Second,
        },
    },
    
    // User agent string
    UserAgent: "my-app/1.0",
    
    // Request timeout
    Timeout: 30 * time.Second,
    
    // Retry configuration
    RetryMax:  3,                // Max retry attempts
    RetryWait: 1 * time.Second,  // Initial retry wait
}
```

### Retry Policy

The client automatically retries on:
- Network errors
- HTTP 408 (Request Timeout)
- HTTP 429 (Too Many Requests)
- HTTP 502 (Bad Gateway)
- HTTP 503 (Service Unavailable)
- HTTP 504 (Gateway Timeout)

## API Services

### Discovery Service

```go
// List schemas with filtering
schemas, err := c.Discovery.ListSchemas(ctx, &client.ListSchemasOptions{
    EventType:       "Transaction",
    MinRecordCount:  1000,
    MaxSchemas:      50,
    IncludeMetadata: true,
})

// Get detailed schema profile
profile, err := c.Discovery.GetSchemaProfile(ctx, "Transaction", 
    &client.ProfileSchemaOptions{
        Depth: "full", // basic, standard, full
    })

// Find relationships between schemas
relationships, err := c.Discovery.FindRelationships(ctx,
    []string{"Transaction", "PageView"},
    &client.FindRelationshipsOptions{
        MaxRelationships: 10,
        MinConfidence:    0.7,
    })

// Assess data quality
quality, err := c.Discovery.AssessQuality(ctx, "Transaction",
    &client.AssessQualityOptions{
        TimeRange: "24h",
    })
```

### Patterns Service

```go
// Analyze patterns in data
patterns, err := c.Patterns.AnalyzePatterns(ctx, &client.PatternAnalysisRequest{
    EventType:  "Transaction",
    Attributes: []string{"duration", "error"},
    TimeRange:  "24h",
})
```

### Query Service

```go
// Generate NRQL from natural language
query, err := c.Query.GenerateQuery(ctx,
    "show me the average transaction duration by application",
    &client.QueryContext{
        Schemas:   []string{"Transaction"},
        TimeRange: "1h",
        Examples:  []string{"SELECT average(duration) FROM Transaction"},
    })
```

### Dashboard Service

```go
// Create dashboard from specification
dashboard, err := c.Dashboard.CreateDashboard(ctx, &client.DashboardSpec{
    Name:        "My Dashboard",
    Description: "Transaction monitoring",
    Widgets: []client.WidgetSpec{
        {
            Type:  "line",
            Title: "Transaction Duration",
            Query: "SELECT average(duration) FROM Transaction TIMESERIES",
        },
    },
})
```

## Error Handling

### API Errors

```go
schemas, err := c.Discovery.ListSchemas(ctx, nil)
if err != nil {
    if apiErr, ok := err.(*client.APIError); ok {
        // Handle API error
        log.Printf("API Error %d: %s", apiErr.StatusCode, apiErr.Message)
        
        // Access error details
        if details, ok := apiErr.Details["resource"]; ok {
            log.Printf("Resource: %v", details)
        }
    } else {
        // Handle other errors (network, etc.)
        log.Printf("Error: %v", err)
    }
}
```

### Context Cancellation

```go
ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel()

schemas, err := c.Discovery.ListSchemas(ctx, nil)
if err != nil {
    if err == context.DeadlineExceeded {
        log.Println("Request timed out")
    }
}
```

## Advanced Usage

### Custom HTTP Client

```go
// Create custom transport with proxy
transport := &http.Transport{
    Proxy: http.ProxyURL(proxyURL),
    DialContext: (&net.Dialer{
        Timeout:   30 * time.Second,
        KeepAlive: 30 * time.Second,
    }).DialContext,
}

config := client.Config{
    HTTPClient: &http.Client{
        Transport: transport,
        Timeout:   60 * time.Second,
    },
}
```

### Request Middleware

```go
// Add custom headers or logging
type loggingTransport struct {
    transport http.RoundTripper
}

func (t *loggingTransport) RoundTrip(req *http.Request) (*http.Response, error) {
    log.Printf("Request: %s %s", req.Method, req.URL)
    resp, err := t.transport.RoundTrip(req)
    if resp != nil {
        log.Printf("Response: %d", resp.StatusCode)
    }
    return resp, err
}

config := client.Config{
    HTTPClient: &http.Client{
        Transport: &loggingTransport{
            transport: http.DefaultTransport,
        },
    },
}
```

### Concurrent Operations

```go
var wg sync.WaitGroup
schemas := []string{"Transaction", "PageView", "SystemSample"}

for _, schema := range schemas {
    wg.Add(1)
    go func(s string) {
        defer wg.Done()
        
        profile, err := c.Discovery.GetSchemaProfile(ctx, s, nil)
        if err != nil {
            log.Printf("Error getting %s: %v", s, err)
            return
        }
        
        log.Printf("%s has %d attributes", s, len(profile.Attributes))
    }(schema)
}

wg.Wait()
```

## Testing

### Mock Client

```go
// Use httptest for testing
server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
    // Mock response
    json.NewEncoder(w).Encode(client.ListSchemasResponse{
        Schemas: []client.Schema{
            {Name: "Test", EventType: "Test"},
        },
    })
}))
defer server.Close()

c, _ := client.NewClient(client.Config{
    BaseURL: server.URL + "/api/v1",
})

// Test your code with mock client
schemas, err := c.Discovery.ListSchemas(ctx, nil)
```

## Best Practices

1. **Always use contexts** - Pass context for cancellation and timeouts
2. **Handle errors properly** - Check for specific error types
3. **Configure retries** - Adjust based on your use case
4. **Pool clients** - Reuse client instances, they're safe for concurrent use
5. **Set timeouts** - Always set reasonable timeouts

## Examples

See the [examples directory](../../examples/go-client) for complete examples:
- Basic usage
- Error handling
- Concurrent requests
- Custom configuration

## Performance Considerations

- The client uses connection pooling by default
- Retry logic adds overhead; adjust `RetryMax` if needed
- For high-throughput applications, increase `MaxIdleConns`
- Consider using contexts with deadlines for all operations

## Contributing

When adding new endpoints:
1. Add types to appropriate service file
2. Implement method with proper error handling
3. Add tests with httptest
4. Update documentation

## License

Same as the parent project.
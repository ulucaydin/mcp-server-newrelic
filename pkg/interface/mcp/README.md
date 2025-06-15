# MCP Server Implementation

This package implements the Model Context Protocol (MCP) server for the New Relic UDS Interface Layer. The implementation follows the MCP specification and provides multiple transport options for AI agents to interact with the UDS discovery capabilities.

## Architecture

### Core Components

1. **Server** (`server.go`) - Main MCP server that coordinates all components
2. **Protocol Handler** (`protocol.go`) - Implements JSON-RPC 2.0 protocol
3. **Tool Registry** (`registry.go`) - Manages available tools and their handlers
4. **Session Manager** (`sessions.go`) - Handles stateful interactions
5. **Transports** - Multiple transport implementations:
   - Stdio (`transport_stdio.go`) - For CLI integration
   - HTTP (`transport_http.go`) - For web-based tools
   - SSE (`transport_sse.go`) - For real-time streaming

### Build Tags

To isolate Track 2 (Interface Layer) from Track 1 (Discovery Core) during development, we use build tags:

- `nodiscovery` - Builds without discovery dependencies (for testing)
- Default build includes full discovery integration

## Usage

### Running Tests

Run tests in isolation from Track 1:
```bash
go test -tags="nodiscovery" -v
```

Run with coverage:
```bash
go test -tags="nodiscovery" -v -cover
```

### Starting the Server

```go
// Create server configuration
config := mcp.ServerConfig{
    TransportType:    mcp.TransportStdio,
    RequestTimeout:   30 * time.Second,
    StreamingEnabled: true,
}

// Create and start server
server := mcp.NewServer(config)
ctx := context.Background()
if err := server.Start(ctx); err != nil {
    log.Fatal(err)
}
```

### Available Tools

The MCP server provides the following built-in tools:

1. **discovery.list_schemas** - List available data schemas
2. **discovery.profile_attribute** - Get detailed attribute profiles
3. **discovery.find_relationships** - Discover relationships between schemas
4. **discovery.assess_quality** - Assess data quality
5. **session.create** - Create a new session
6. **session.end** - End a session

### Transport Options

#### Stdio Transport
Best for CLI tools and local development:
```bash
./mcp-server --transport stdio
```

#### HTTP Transport
For web-based integrations:
```bash
./mcp-server --transport http --host localhost --port 9090
```

#### SSE Transport
For real-time streaming applications:
```bash
./mcp-server --transport sse --host localhost --port 9091
```

## Integration with Track 1

When Track 1 (Discovery Core) is ready, the integration points are:

1. Set the discovery engine in the server:
```go
server.SetDiscoveryEngine(discoveryEngine)
```

2. The discovery tools will automatically use the engine for:
   - Schema discovery
   - Attribute profiling
   - Relationship detection
   - Quality assessment

## Protocol Details

The server implements JSON-RPC 2.0 with the following methods:

- `initialize` - Initialize the connection
- `tools/list` - List available tools
- `tools/call` - Execute a tool
- `completion/complete` - Get completions (placeholder)
- `sessions/create` - Create a session
- `sessions/get` - Get session details

## Development

### Adding New Tools

1. Define the tool in `tools.go`:
```go
server.tools.Register(Tool{
    Name:        "my.tool",
    Description: "My custom tool",
    Parameters: ToolParameters{
        Type: "object",
        Properties: map[string]Property{
            "param1": {
                Type:        "string",
                Description: "Parameter description",
            },
        },
        Required: []string{"param1"},
    },
    Handler: myToolHandler,
})
```

2. Implement the handler:
```go
func myToolHandler(ctx context.Context, params map[string]interface{}) (interface{}, error) {
    // Tool implementation
    return result, nil
}
```

### Streaming Tools

For tools that return large results or real-time data:

```go
server.tools.Register(Tool{
    Name:        "my.streaming.tool",
    Description: "Streaming tool",
    Streaming:   true,
    StreamHandler: func(ctx context.Context, params map[string]interface{}, stream chan<- StreamChunk) {
        // Send chunks
        stream <- StreamChunk{Type: "data", Data: chunk1}
        stream <- StreamChunk{Type: "data", Data: chunk2}
        close(stream)
    },
})
```

## Testing

The package includes comprehensive tests for:
- Server lifecycle
- Tool registry operations
- Protocol handling
- Session management
- All transport implementations
- Concurrent operations

Current test coverage: ~38%

## Next Steps

1. Complete REST API implementation (Week 2)
2. Build CLI tool with Cobra (Week 2)
3. Create client libraries (Week 2)
4. Add authentication and rate limiting (Week 3)
5. Implement caching and monitoring (Week 4)
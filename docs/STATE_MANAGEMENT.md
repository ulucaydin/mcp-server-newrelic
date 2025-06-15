# State Management Documentation

## Overview

The UDS state management system provides lightweight, efficient session and cache management for MCP interactions. It maintains context between discovery calls and caches expensive NRDB query results.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    State Management System                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Session Management                     │   │
│  │  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐ │   │
│  │  │ Memory Store │  │ Redis Store   │  │ Session      │ │   │
│  │  │ (Default)    │  │ (Distributed) │  │ Context      │ │   │
│  │  └──────────────┘  └───────────────┘  └──────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Result Caching                        │   │
│  │  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐ │   │
│  │  │ Memory Cache │  │ Redis Cache   │  │ TTL Manager  │ │   │
│  │  │ (L1)         │  │ (L2)          │  │              │ │   │
│  │  └──────────────┘  └───────────────┘  └──────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  MCP Integration                         │   │
│  │  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐ │   │
│  │  │ Enhanced     │  │ Discovery     │  │ APM          │ │   │
│  │  │ Server       │  │ Recording     │  │ Metrics      │ │   │
│  │  └──────────────┘  └───────────────┘  └──────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Configuration

### Environment Variables

```bash
# Core Configuration
STATE_STORE_TYPE=memory          # Options: memory, redis
SESSION_TTL=1h                   # Session expiration time
CACHE_TTL=5m                     # Default cache TTL

# Memory Store Configuration
MAX_SESSIONS=10000              # Maximum concurrent sessions
MAX_CACHE_ENTRIES=100000        # Maximum cache entries
MAX_CACHE_MEMORY=1073741824     # Maximum cache memory (1GB)

# Redis Configuration (optional)
REDIS_URL=redis://localhost:6379 # Redis connection URL
REDIS_MAX_RETRIES=3             # Connection retry attempts
REDIS_POOL_SIZE=10              # Connection pool size
REDIS_KEY_PREFIX=uds            # Key prefix for multi-tenant Redis
```

### Example .env Configuration

```bash
# In-memory configuration (default)
STATE_STORE_TYPE=memory
SESSION_TTL=1h
CACHE_TTL=5m

# Redis configuration (for production)
STATE_STORE_TYPE=redis
REDIS_URL=redis://redis.example.com:6379/0
REDIS_KEY_PREFIX=uds_prod
SESSION_TTL=2h
CACHE_TTL=10m
```

## Usage

### Basic Integration

```go
import (
    "github.com/deepaucksharma/mcp-server-newrelic/pkg/state"
)

// Create state manager from environment
stateManager, err := state.CreateStateManagerFromEnv()
if err != nil {
    log.Fatal(err)
}
defer stateManager.Close()

// Create a session
session, err := stateManager.CreateSession(ctx, "explore transaction performance")

// Store context
stateManager.SetContext(ctx, session.ID, "current_schema", "Transaction")

// Cache discovery results
stateManager.Set(ctx, "schema:Transaction", schemaData, 5*time.Minute)
```

### MCP Server Integration

```go
// Create enhanced MCP server with state management
server := mcp.NewEnhancedServer(mcpConfig, stateManager)

// Discovery results are automatically cached
// Session context is maintained between calls
```

### Discovery Recording

```go
mcpManager := state.NewMCPSessionManager(stateManager)

// Start a discovery session
session, err := mcpManager.StartDiscoverySession(ctx, "analyze error patterns")

// Record discoveries
mcpManager.RecordDiscovery(ctx, session.ID, "TransactionError", discoveryResult)

// Get full context
context, err := mcpManager.GetDiscoveryContext(ctx, session.ID)
```

## Features

### Session Management

- **Unique Sessions**: Each MCP connection gets a unique session ID
- **Context Storage**: Arbitrary key-value pairs stored per session
- **Goal Tracking**: User's discovery goal stored and used for optimization
- **TTL Management**: Automatic cleanup of expired sessions
- **Discovery History**: Track which schemas have been explored

### Result Caching

- **Multi-Level Cache**: In-memory L1 cache with optional Redis L2
- **TTL Support**: Configurable expiration for each cached item
- **LRU Eviction**: Automatic eviction when memory limits reached
- **Hit Rate Tracking**: Monitor cache effectiveness
- **Smart Invalidation**: Automatic cleanup of stale data

### Performance Optimizations

- **Cache Warming**: Pre-load commonly accessed data
- **Batch Operations**: Efficient bulk updates
- **Async Updates**: Non-blocking cache writes
- **Connection Pooling**: Efficient Redis connection management

### Observability

- **APM Integration**: Full New Relic APM instrumentation
- **Metrics Collection**: Cache hit/miss rates, session counts
- **Health Checks**: Monitor state store health
- **Performance Tracking**: Measure operation latencies

## Implementation Details

### Memory Store

The default in-memory store provides:
- Thread-safe operations using sync.RWMutex
- O(1) lookups for sessions and cache entries
- Automatic garbage collection of expired items
- Memory-efficient storage with configurable limits

### Redis Store

The Redis store provides:
- Distributed state across multiple instances
- Persistence across restarts
- Pub/Sub for real-time updates
- Atomic operations for consistency

### Cache Strategies

1. **Write-Through**: Updates written to both L1 and L2
2. **Read-Through**: L1 miss triggers L2 lookup
3. **TTL Cascade**: Shorter TTL in L1, longer in L2
4. **Predictive Loading**: Pre-load based on access patterns

## Best Practices

### Session Lifecycle

1. Create session at MCP connection start
2. Update context as discoveries progress
3. Cache results with appropriate TTLs
4. Clean up on disconnect

### Cache Key Naming

```
discovery:<session_id>:schema:<schema_name>
discovery:<session_id>:pattern:<pattern_type>
tool:<tool_name>:<params_hash>
```

### TTL Guidelines

- Session TTL: 1-2 hours (user interaction timeframe)
- Schema Cache: 5-10 minutes (data freshness)
- Pattern Cache: 10-30 minutes (computation cost)
- Tool Results: 1-5 minutes (quick refresh)

## Monitoring

### Key Metrics

```
# Session Metrics
state_sessions_total         # Total sessions created
state_sessions_active        # Currently active sessions
state_sessions_expired       # Expired sessions

# Cache Metrics
state_cache_hits_total       # Cache hit count
state_cache_misses_total     # Cache miss count
state_cache_evictions_total  # Evicted entries
state_cache_size_bytes       # Current cache size

# Performance Metrics
state_operation_duration_seconds{operation="get"}
state_operation_duration_seconds{operation="set"}
```

### Health Checks

```bash
# Check state manager health
curl http://localhost:8080/health

# Response includes state component status
{
  "state": {
    "status": "healthy",
    "store_type": "redis",
    "sessions_active": 42,
    "cache_hit_rate": 0.85
  }
}
```

## Troubleshooting

### Common Issues

1. **High Memory Usage**
   - Reduce MAX_CACHE_MEMORY
   - Decrease cache TTLs
   - Enable Redis for distributed caching

2. **Redis Connection Failures**
   - Check REDIS_URL configuration
   - Verify network connectivity
   - Falls back to memory store automatically

3. **Session Expiration**
   - Increase SESSION_TTL
   - Implement session refresh on activity
   - Monitor session cleanup frequency

### Debug Logging

```bash
# Enable debug logging
LOG_LEVEL=DEBUG

# State-specific debug logs
STATE_DEBUG=true
```

## Future Enhancements

1. **Distributed Locking**: For multi-instance coordination
2. **Event Streaming**: Real-time state change notifications
3. **Backup/Restore**: State snapshots for recovery
4. **Analytics**: Usage patterns and optimization suggestions
5. **Compression**: Reduce memory usage for large cached objects

## Example Workflows

### Discovery Session Flow

```
1. User connects via MCP
   → Create session with goal
   → Initialize empty context

2. User requests schema discovery
   → Check cache for results
   → Execute discovery if cache miss
   → Store results in cache
   → Update session context

3. User explores specific schema
   → Retrieve from cache if available
   → Record in session history
   → Suggest related schemas

4. Session ends
   → Mark session inactive
   → Retain cache for TTL period
   → Clean up after expiration
```

### Cache Warming Example

```go
// Warm cache for transaction analysis
if session.UserGoal == "analyze transactions" {
    schemas := []string{"Transaction", "TransactionError", "TransactionTrace"}
    for _, schema := range schemas {
        go warmSchemaCache(ctx, session.ID, schema)
    }
}
```

This state management system provides the foundation for maintaining context and improving performance in UDS MCP interactions.
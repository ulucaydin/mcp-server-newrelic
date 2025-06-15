# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The Universal Data Synthesizer (UDS) is an AI-powered system for New Relic that automatically discovers, analyzes, and visualizes data from NRDB. It implements MCP (Model Context Protocol) for seamless integration with AI assistants like Claude and GitHub Copilot.

**Current State**: The repository has an active implementation with Discovery Core (Track 1) mostly complete, MCP server operational, and Platform Foundation (Track 4) partially implemented. Intelligence Engine (Tracks 2-3) are planned but not yet implemented.

## High-Level Architecture

The system follows a multi-layer architecture:

```
AI Assistant (Claude/Copilot)
    ↓ MCP Protocol (JSON-RPC)
MCP Server (Go) - pkg/interface/mcp/
    ↓ Internal APIs
Discovery Engine (Go) - pkg/discovery/
    ↓ GraphQL
New Relic NRDB
```

### Key Components
- **Discovery Engine** (`pkg/discovery/`): Schema discovery, pattern detection, relationship mining
- **MCP Server** (`pkg/interface/mcp/`): AI assistant integration via Model Context Protocol
- **REST API** (`pkg/interface/api/`): Traditional HTTP API for non-AI clients
- **Platform Foundation** (`pkg/auth/`, `pkg/telemetry/`): Security, observability, resilience

### Implementation Status
- ✅ **Track 1**: Discovery Core with sampling, pattern detection, quality assessment
- ✅ **Track 4**: Authentication, APM integration, resilience patterns
- 🚧 **MCP Server**: Basic tool registration and execution
- ❌ **Tracks 2-3**: Intelligence Engine (Python) - not yet implemented

## Development Commands

### Build & Run
```bash
# Build the Go MCP server
make build                  # Builds bin/mcp-server

# Docker builds
make build-docker          # Build Docker image
docker-compose up          # Run full stack with Docker Compose

# Development mode
make dev                   # Run with auto-reload
make run                   # Run the built server
```

### Testing
```bash
# Go tests
make test                  # Run all tests with race detection
make test-unit            # Unit tests only
make test-integration     # Integration tests
make test-benchmarks      # Performance benchmarks
make test-coverage        # Generate coverage report

# MCP tests
make test-mcp            # Run MCP test suite
make test-mcp-interactive # Interactive MCP test runner

# End-to-end tests
./tests/run_tests.sh      # Full test suite with Docker
```

### Code Quality
```bash
make lint                 # Run golangci-lint
make format              # Format Go code
make tidy                # Tidy dependencies
make install-tools       # Install dev tools
```

## Key Architecture Patterns

### Interface-Based Design
All major components use Go interfaces for testability:
- `DiscoveryEngine`, `NRDBClient`, `Cache` interfaces enable easy mocking
- Clean separation between interface and implementation

### Resilience Patterns
- **Circuit Breaker** (`pkg/discovery/nrdb/circuit_breaker.go`): Prevents cascading failures
- **Rate Limiter** (`pkg/discovery/nrdb/rate_limiter.go`): Token bucket algorithm
- **Retry Logic** (`pkg/discovery/nrdb/retry.go`): Exponential backoff with jitter

### Worker Pool Pattern
Parallel processing for discovery tasks:
- Configurable pool size based on workload
- Graceful shutdown with context cancellation
- Type-safe task execution

### Multi-Layer Caching
- L1: In-memory cache (ristretto)
- L2: Redis distributed cache
- Cache-aside pattern with TTL management

## Required Environment Configuration

```bash
# New Relic API Access
NEW_RELIC_API_KEY=your-user-api-key        # Required: User API key for NRDB access
NEW_RELIC_ACCOUNT_ID=your-account-id       # Required: Your New Relic account ID
NEW_RELIC_REGION=US                        # US or EU

# New Relic APM (for monitoring this service)
NEW_RELIC_LICENSE_KEY=your-license-key     # Optional: For APM instrumentation
NEW_RELIC_APP_NAME=mcp-server-newrelic     # Optional: APM app name

# Service Configuration
MCP_TRANSPORT=stdio                        # stdio, http, or sse
SERVER_PORT=8080                          # REST API port
LOG_LEVEL=INFO                            # DEBUG, INFO, WARN, ERROR
```

Copy `.env.example` to `.env` and fill in your values.

## Component Communication Flow

### MCP Tool Execution
1. AI assistant sends JSON-RPC request to MCP server
2. MCP server validates request and extracts parameters
3. Tool handler calls Discovery Engine with context
4. Discovery Engine queries NRDB with circuit breaker protection
5. Results are cached and returned to AI assistant
6. APM tracks the entire transaction

### Discovery Process
1. **Event Type Discovery**: Find all available event types
2. **Schema Profiling**: Analyze attributes and data types
3. **Pattern Detection**: Identify common patterns and anomalies
4. **Quality Assessment**: Score data completeness and consistency
5. **Relationship Mining**: Find connections between schemas

## New Relic APM Integration

The codebase includes native New Relic APM instrumentation:
- Transaction tracking for all major operations
- Custom metrics for discovery operations
- Distributed tracing across services
- Error tracking and alerting

APM instrumentation points:
- `pkg/discovery/engine.go`: Discovery operations
- `pkg/interface/api/server.go`: HTTP endpoints
- `pkg/interface/mcp/server.go`: MCP tool execution

## Working with the Codebase

### Adding a New MCP Tool
1. Define tool schema in `pkg/interface/mcp/tools_*.go`
2. Implement handler method on `MCPServer`
3. Register tool in `RegisterTools()` method
4. Add tests in `pkg/interface/mcp/*_test.go`

### Extending Discovery Engine
1. Implement new interface in `pkg/discovery/types.go`
2. Add implementation in appropriate package
3. Wire into `Engine` in `pkg/discovery/engine.go`
4. Add configuration in `pkg/config/config.go`

### Running Single Tests
```bash
# Run specific Go test
go test -v -run TestDiscoverSchemas ./pkg/discovery

# Run specific test file
go test -v ./pkg/discovery/sampling/strategies_test.go

# Run with race detection
go test -race -v ./pkg/discovery/...
```
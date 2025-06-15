# UDS Project Structure

## Overview
This document describes the organization of the Universal Data Synthesizer (UDS) codebase.

## Directory Structure

```
.
├── cmd/                      # Command-line applications
│   ├── uds-discovery/       # Discovery engine CLI
│   │   └── main.go         # Entry point for discovery service
│   └── uds-mcp/            # MCP server CLI
│       └── main.go         # Entry point for MCP server
│
├── pkg/                      # Public packages (importable by other projects)
│   ├── discovery/           # Discovery engine implementation (Track 1)
│   │   ├── config.go       # Configuration structures
│   │   ├── engine.go       # Main discovery engine
│   │   ├── engine_helpers.go # Helper functions for engine
│   │   ├── factory.go      # Factory functions for creating components
│   │   ├── helpers.go      # General helper functions
│   │   ├── interfaces.go   # Interface definitions
│   │   ├── types.go        # Type definitions
│   │   ├── nrdb/          # NRDB client implementation
│   │   │   ├── client.go   # NRDB client
│   │   │   ├── mock.go     # Mock NRDB client for testing
│   │   │   ├── rate_limiter.go # Rate limiting implementation
│   │   │   └── types.go    # NRDB-specific types
│   │   └── sampling/       # Sampling strategies
│   │       └── strategies.go # Various sampling implementations
│   │
│   └── interface/           # Interface layer (Track 2)
│       └── mcp/            # MCP protocol implementation
│           ├── protocol.go  # Protocol handler
│           ├── registry.go  # Tool registry
│           ├── server_*.go  # Server implementations
│           ├── sessions.go  # Session management
│           ├── tools_*.go   # Tool definitions
│           ├── transport_*.go # Transport implementations
│           ├── types.go     # MCP types
│           └── mock_*.go    # Mock implementations for testing
│
├── internal/                 # Private packages (not importable)
│   └── (currently empty)
│
├── docs/                     # Documentation
│   ├── track1-discovery-core.md      # Track 1 implementation guide
│   ├── track2-interface-layer.md     # Track 2 implementation guide
│   ├── track3-intelligence-engine.md # Track 3 implementation guide
│   └── IMPLEMENTATION_LOG.md         # Implementation progress tracking
│
├── go.mod                    # Go module definition
├── go.sum                    # Go module checksums
├── Makefile                  # Build automation
├── ARCHITECTURE.md           # System architecture documentation
├── TECHNICAL_VISION.md       # Technical vision and roadmap
├── CLAUDE.md                 # AI assistant instructions
└── PROJECT_STRUCTURE.md      # This file
```

## Package Organization

### cmd/ Directory
Contains the main applications. Each subdirectory is a separate executable:
- `uds-discovery`: Standalone discovery engine service
- `uds-mcp`: MCP server that exposes UDS functionality to AI assistants

### pkg/ Directory
Contains all the importable packages:
- `discovery`: Core discovery engine functionality (Track 1)
- `interface/mcp`: MCP protocol implementation (Track 2)

### internal/ Directory
For code that should not be imported by external projects. Currently empty but will contain:
- Shared utilities specific to UDS
- Internal testing helpers

## Naming Conventions

1. **Packages**: Lowercase, single word when possible (e.g., `discovery`, `mcp`)
2. **Files**: Lowercase with underscores (e.g., `rate_limiter.go`)
3. **Types**: PascalCase (e.g., `DiscoveryEngine`, `NRDBClient`)
4. **Interfaces**: PascalCase, often ending in "er" (e.g., `Discoverer`, `Sampler`)
5. **Functions**: PascalCase for exported, camelCase for unexported

## Build Tags

The project uses build tags for conditional compilation:
- `nodiscovery`: Build MCP server without discovery engine dependency (for testing)
- `test`: Enable test-specific code

## Future Structure (Tracks 3-4)

When Track 3 (Intelligence Engine) and Track 4 (Visualizer) are implemented:

```
├── intelligence/             # Track 3: Python-based intelligence engine
│   ├── patterns/            # Pattern detection
│   ├── query/              # Query generation
│   └── visualization/      # Visualization recommendations
│
└── visualizer/              # Track 4: Dashboard creation
    ├── templates/          # Dashboard templates
    └── builder/           # Dashboard builder logic
```

## Import Paths

All imports use the full module path:
```go
import "github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery"
```

## Testing

Test files are colocated with the code they test:
- Unit tests: `*_test.go` in the same package
- Integration tests: In `internal/integration/` (to be created)
- E2E tests: In `internal/e2e/` (to be created)
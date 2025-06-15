# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The Universal Data Synthesizer (UDS) is an AI-powered system for New Relic that automatically discovers, analyzes, and visualizes data from NRDB. It implements MCP (Model Context Protocol) and A2A (Agent-to-Agent) standards for seamless integration with AI assistants like GitHub Copilot.

**Current State**: The repository is in a clean state with only documentation remaining. All implementation code has been removed, preparing for a fresh implementation following the architectural vision.

## Core Architecture

### Multi-Agent System
- **Orchestrator Agent**: Coordinates all specialist agents and manages workflows
- **Explorer Agent**: Discovers schemas and profiles data
- **Analyst Agent**: Detects patterns and generates insights
- **Cartographer Agent**: Maps relationships between data sources
- **Visualizer Agent**: Generates dashboards and visualizations

### Technology Stack
- **Track 1 (Discovery Core)**: Go-based implementation for high performance
- **Tracks 2-4 (Agents)**: Python implementation for flexibility
- **Protocol**: MCP server for tool integration, A2A for agent communication
- **Data Access**: NRDB via NerdGraph API

## Implementation Tracks

### Track 1: Discovery Core (Go)
- Location: `pkg/discovery/`
- Key components: Schema discovery, intelligent sampling, pattern detection, relationship mining
- Reference: `docs/track1-discovery-core.md`

### Track 2: LLM Orchestrator & Explorer Agent (Python)
- Orchestrator manages agent coordination and decision trees
- Explorer performs zero-knowledge schema discovery

### Track 3: Analyst & Cartographer Agents (Python)
- Analyst detects patterns and anomalies
- Cartographer maps data relationships

### Track 4: Visualizer Agent & MCP Server (Python)
- Visualizer generates NRQL queries and dashboards
- MCP server provides tool interface

## Development Commands

Since the codebase is being rebuilt, here are the expected commands once implementation begins:

### Go Development (Track 1)
```bash
# Run tests
go test ./pkg/discovery/...

# Run benchmarks
go test -bench=. ./pkg/discovery/...

# Build
go build ./cmd/uds-discovery

# Lint
golangci-lint run
```

### Python Development (Tracks 2-4)
```bash
# Run tests
pytest tests/

# Run specific test
pytest tests/test_orchestrator.py::TestOrchestrator::test_decision_tree

# Lint
ruff check .

# Type check
mypy src/

# Run MCP server
python -m src.mcp_server
```

## Key Design Patterns

### 1. Agent Communication
- Agents communicate via A2A protocol
- Each agent has well-defined interfaces and responsibilities
- Orchestrator manages agent lifecycle and coordination

### 2. Discovery Strategy
- Zero-knowledge approach: no assumptions about data schema
- Intelligent sampling to minimize NRDB query costs
- Progressive discovery: start simple, go deeper as needed

### 3. Error Handling
- All NRDB operations must handle rate limits and quotas
- Implement exponential backoff for retries
- Cache discovered schemas to reduce repeated queries

### 4. Security
- Multi-tenant isolation at all layers
- API key validation and secure storage
- Query result sanitization before caching

## Working with NRDB

### Query Patterns
```python
# Always use parameterized queries
query = f"SELECT * FROM {event_type} SINCE 1 hour ago LIMIT 100"

# Cost-aware sampling
query = f"SELECT * FROM {event_type} SINCE 1 hour ago LIMIT {calculate_sample_size(volume)}"

# Faceted discovery
query = f"SELECT keyset() FROM {event_type} SINCE 1 hour ago LIMIT 1"
```

### Rate Limiting
- Implement circuit breakers for NRDB queries
- Use adaptive sampling based on data volume
- Cache aggressively with appropriate TTLs

## Testing Strategy

### Unit Tests
- Mock NRDB responses for predictable testing
- Test each agent in isolation
- Verify protocol compliance (MCP/A2A)

### Integration Tests
- Use test accounts with known data
- Verify end-to-end workflows
- Test error scenarios and recovery

### Performance Tests
- Benchmark discovery time for various data volumes
- Measure memory usage during large discoveries
- Verify concurrent query handling

## Important Considerations

1. **Cost Management**: Every NRDB query has a cost. Always optimize for minimal queries.
2. **Data Privacy**: Never log or cache sensitive data values, only schemas and patterns.
3. **Scalability**: Design for millions of events and hundreds of attributes per schema.
4. **Idempotency**: All operations should be safely retryable.
5. **Observability**: Instrument everything - this is for New Relic after all!

## References

- Technical Vision: `TECHNICAL_VISION.md`
- Architecture Details: `ARCHITECTURE.md`
- Track 1 Implementation: `docs/track1-discovery-core.md`
- MCP Specification: https://modelcontextprotocol.io/
- NRDB Documentation: https://docs.newrelic.com/docs/query-your-data/nrdb-query-language/
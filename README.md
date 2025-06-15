# Universal Data Synthesizer (UDS)

## Overview

AI-powered New Relic dashboard generation system that leverages MCP (Model Context Protocol) and A2A (Agent-to-Agent) standards to provide intelligent data discovery, analysis, and visualization capabilities.

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/deepaucksharma/mcp-server-newrelic.git
cd mcp-server-newrelic

# Install Go dependencies
go mod download

# Install Python dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your New Relic credentials
```

### Basic Usage

```bash
# Start the Discovery Engine (Go)
make run-discovery

# Start the MCP Server (Python)
python main.py

# Or use Docker Compose
docker-compose up
```

### Example MCP Tool Usage

```python
# Discover schemas in your New Relic account
await mcp_client.call_tool("discover_schemas", {
    "account_id": "123456",
    "pattern": "Transaction"
})

# Analyze data quality
await mcp_client.call_tool("analyze_data_quality", {
    "event_type": "Transaction"
})
```

## 📊 Project Status

| Track | Component | Language | Status | Test Coverage | Notes |
|-------|-----------|----------|--------|---------------|-------|
| 1 | Discovery Core | Go | ✅ Complete | 70% | Schema discovery, pattern detection, quality assessment |
| 2 | Interface Layer | Go/Python | 🚧 In Progress (60%) | 50% | MCP server, gRPC interface, Python client |
| 3 | Intelligence Engine | Python | 📝 Planned | - | NLP, ML models, insight generation |
| 4 | Visualizer | Python/React | ⏳ Not Started | - | Dashboard generation, D3.js visualizations |

### Current Sprint Focus
- Completing Track 2 Python client integration
- Adding authentication and rate limiting
- Implementing integration tests
- Creating deployment automation

## 📚 Documentation

- **[Architecture Overview](./docs/ARCHITECTURE.md)** - System design and component interaction
- **[API Reference](./docs/API_REFERENCE.md)** - Complete API documentation
- **[Development Guide](./docs/DEVELOPMENT.md)** - Setup and contribution guidelines
- **[Deployment Guide](./docs/DEPLOYMENT.md)** - Production deployment instructions
- **[Implementation Status](./docs/IMPLEMENTATION_STATUS.md)** - Detailed progress tracking

## 🛠️ Key Features

### Track 1: Discovery Core (Go)
- ✅ Schema discovery with parallel processing
- ✅ Pattern detection (time series, distributions)
- ✅ Relationship mining between data types
- ✅ Data quality assessment (5 dimensions)
- ✅ Resilient NRDB client (circuit breaker, retries)
- ✅ OpenTelemetry tracing integration

### Track 2: Interface Layer
- ✅ MCP protocol implementation
- ✅ Multi-transport support (STDIO, HTTP, SSE)
- ✅ Plugin architecture for extensibility
- 🚧 Python client for Discovery Engine
- 🚧 Authentication and authorization
- 🚧 Rate limiting and quota management

### Track 3: Intelligence Engine (Planned)
- 📝 Natural language to NRQL translation
- 📝 Anomaly detection and prediction
- 📝 Automated insight generation
- 📝 Dashboard recommendation system

### Track 4: Visualizer (Planned)
- 📝 Dynamic dashboard generation
- 📝 Interactive visualizations
- 📝 Export to New Relic dashboards
- 📝 Custom widget library

## 🏗️ Architecture

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
└─────────────────────────────────────────────────────┼──────────────┘
                                                      │ HTTPS
                                                      ▼
                                            ┌─────────────────┐
                                            │  New Relic API  │
                                            └─────────────────┘
```

## 🔧 Configuration

### Required Environment Variables

```bash
# New Relic Credentials
NEW_RELIC_API_KEY=your_api_key
NEW_RELIC_ACCOUNT_ID=your_account_id
NEW_RELIC_REGION=US  # or EU

# Service Configuration
DISCOVERY_ENGINE_PORT=8081
MCP_SERVER_PORT=8080

# Observability
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp.nr-data.net:4317
OTEL_EXPORTER_OTLP_HEADERS=Api-Key=your_license_key
```

See [.env.example](./.env.example) for full configuration options.

## 🧪 Testing

```bash
# Run all tests
make test

# Run specific test suites
make test-unit         # Unit tests only
make test-integration  # Integration tests
make test-benchmarks   # Performance benchmarks

# Generate coverage report
make test-coverage
```

## 🚀 Deployment

### Docker

```bash
# Build images
docker build -t uds-discovery:latest -f Dockerfile.discovery .
docker build -t uds-mcp:latest -f Dockerfile.mcp .

# Run with Docker Compose
docker-compose up -d
```

See [Deployment Guide](./docs/DEPLOYMENT.md) for detailed deployment instructions.

## 🤝 Contributing

We welcome contributions! Please see our [Development Guide](./docs/DEVELOPMENT.md) for:
- Code style guidelines
- Testing requirements
- Pull request process
- Issue reporting

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [FastMCP](https://github.com/jlowin/fastmcp) for MCP protocol support
- Uses [OpenTelemetry](https://opentelemetry.io/) for observability
- Powered by [New Relic](https://newrelic.com/) APIs

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/deepaucksharma/mcp-server-newrelic/issues)
- **Discussions**: [GitHub Discussions](https://github.com/deepaucksharma/mcp-server-newrelic/discussions)
- **Documentation**: [docs/](./docs/)

---

**Current Version**: 0.3.0-alpha | **Last Updated**: December 2024
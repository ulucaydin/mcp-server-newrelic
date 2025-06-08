# New Relic MCP Server 🚀

**Enterprise-grade Model Context Protocol server** that seamlessly integrates New Relic's observability platform with AI assistants like **GitHub Copilot**, **Claude Code**, and **Claude Desktop**. Transform your development workflow with intelligent, context-aware observability insights.

[![Production Ready](https://img.shields.io/badge/Status-Production%20Ready-green.svg)](https://github.com/your-org/mcp-server-newrelic)
[![Security Hardened](https://img.shields.io/badge/Security-Hardened-blue.svg)](SECURITY.md)
[![Test Coverage](https://img.shields.io/badge/Coverage-80%25+-brightgreen.svg)](tests/)
[![AI Assistants](https://img.shields.io/badge/AI%20Assistants-3%20Supported-purple.svg)](#ai-assistant-integrations)

## ✨ What Makes This Special

🤖 **AI-Native Design**: Purpose-built for AI assistants with natural language interfaces  
🔒 **Enterprise Security**: Thread-safe, memory-bounded, with comprehensive error sanitization  
⚡ **High Performance**: Connection pooling, caching, and async operations throughout  
🔧 **Production Ready**: Comprehensive testing, monitoring, and deployment automation  
📊 **Complete Observability**: APM, Infrastructure, Logs, Alerts, Synthetics, and more  

## 🎯 AI Assistant Integrations

### GitHub Copilot + VS Code
```bash
# One-command setup
curl -sSL https://raw.githubusercontent.com/your-org/mcp-server-newrelic/main/scripts/setup-github-copilot.sh | bash

# Then in Copilot Chat:
@copilot /newrelic What's the error rate for my applications?
```

### Claude Desktop
```bash
# One-command setup  
curl -sSL https://raw.githubusercontent.com/your-org/mcp-server-newrelic/main/scripts/setup-claude-desktop.sh | bash

# Then chat naturally:
"Show me the health of my New Relic applications"
```

### Claude Code CLI
```bash
# One-command setup
curl -sSL https://raw.githubusercontent.com/your-org/mcp-server-newrelic/main/scripts/setup-claude-code.sh | bash

# Then use workflows:
claude-code workflow run performance-analysis
```

## 🚀 Core Features

### 🏗️ Enterprise Architecture
- **Thread-Safe Operations**: Production-grade concurrency with RLock protection
- **Memory Management**: Bounded LRU caching prevents OOM conditions  
- **Connection Pooling**: Efficient resource management with reference counting
- **Error Sanitization**: Security-focused error handling prevents information leakage
- **Request Signing**: HMAC-based authentication prevents replay attacks

### 📊 Complete New Relic Coverage
- **APM**: Application performance, transactions, traces, deployments
- **Infrastructure**: Hosts, containers, Kubernetes, processes, storage, network
- **Entities**: Search, relationships, golden signals, dependencies
- **Alerts & Incidents**: Policies, conditions, notifications, acknowledgments  
- **Logs**: Search, patterns, tail, error analysis, correlation
- **Synthetics**: Monitor management, results, alerting
- **Custom Metrics**: NRQL queries, dashboards, time series analysis

### 🎮 Multiple Access Patterns
- **Natural Language**: AI assistants understand your intent
- **CLI Tools**: Direct command execution for automation
- **Workflows**: Pre-built analysis templates  
- **Docker**: Containerized deployment with multi-stage builds

## 📋 Prerequisites

- Python 3.11+
- New Relic account with API key
- Claude Desktop or VS Code (for AI assistant integration)

## 🛠️ Installation

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/mcp-server-newrelic.git
   cd mcp-server-newrelic
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure credentials**
   ```bash
   cp .env.example .env
   # Edit .env with your New Relic API key and account ID
   ```

4. **Run the server**
   ```bash
   # Advanced server with all features
   python main.py
   
   # Or use the simple server
   python server_simple.py
   
   # Or with fastmcp CLI
   fastmcp run server_simple.py:mcp
   ```

### Docker Installation

```bash
# Build and run with Docker Compose
docker-compose up -d

# Or build manually
docker build -t newrelic-mcp .
docker run -e NEW_RELIC_API_KEY=your-key -e NEW_RELIC_ACCOUNT_ID=your-id newrelic-mcp
```

## 🔧 Configuration

### Environment Variables

```bash
# Required
NEW_RELIC_API_KEY=your-api-key
NEW_RELIC_ACCOUNT_ID=your-account-id

# Optional
NEW_RELIC_REGION=US              # US or EU
MCP_TRANSPORT=stdio              # stdio, http, or multi
LOG_LEVEL=INFO                   # DEBUG, INFO, WARNING, ERROR
SESSION_TTL_HOURS=24            # Session timeout
```

### Multi-Account Setup

Use the CLI to manage multiple accounts:

```bash
# Add accounts
python cli.py config add-account --name prod --api-key KEY --account-id ID
python cli.py config add-account --name staging --api-key KEY --account-id ID

# Switch accounts
python cli.py config use prod

# List accounts
python cli.py config list-accounts
```

### Claude Desktop Configuration

Add to your Claude Desktop config:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "newrelic": {
      "command": "python",
      "args": ["/path/to/mcp-server-newrelic/main.py"],
      "env": {
        "NEW_RELIC_API_KEY": "your-api-key",
        "NEW_RELIC_ACCOUNT_ID": "your-account-id"
      }
    }
  }
}
```

### VS Code / GitHub Copilot Configuration

Add to your VS Code settings:

```json
{
  "github.copilot.chat.mcpServers": {
    "newrelic": {
      "url": "http://localhost:3000",
      "token": "optional-auth-token"
    }
  }
}
```

## 💻 CLI Usage

The CLI provides direct access to all MCP tools:

### Query Examples

```bash
# Run NRQL queries
python cli.py query "SELECT count(*) FROM Transaction SINCE 1 hour ago"

# Search entities
python cli.py entities search --name "production" --type APPLICATION

# Get entity details
python cli.py entities details "ENTITY_GUID_HERE"

# List APM applications
python cli.py apm list

# Get application metrics
python cli.py apm metrics "My App" --time-range "SINCE 30 minutes ago"

# Check infrastructure
python cli.py infra hosts --tag environment=production
python cli.py infra disk-usage --threshold 80

# Search logs
python cli.py logs search "error" --since "1 hour ago"
python cli.py logs tail --query "level='ERROR'" --limit 50
```

### Advanced Usage

```bash
# Compare deployments
python cli.py apm deployments compare "My App" --before 30 --after 30

# Analyze error patterns
python cli.py logs analyze-errors --group-by application,error.class

# Get Kubernetes metrics
python cli.py infra k8s --cluster "prod-cluster" --namespace "default"

# Monitor processes
python cli.py infra processes "web-server-01" --name "nginx" --top 10
```

## 🤖 AI Assistant Examples

### With Claude

```
User: What's the current status of my production environment?

Claude: I'll check your production environment status across multiple dimensions.

[Uses search_entities, get_apm_metrics, list_open_incidents tools]

Here's the current status:
- 12 APM applications are running normally
- Average response time: 245ms (↓ 5% from yesterday)  
- Error rate: 0.3% (within normal range)
- 2 minor incidents open (disk space warnings)
- All synthetic monitors passing
```

### With GitHub Copilot

```
User: Help me debug why my API is slow

Copilot: I'll analyze your API performance. Let me check the metrics.

[Uses get_apm_transactions, search_logs, get_entity_golden_signals]

I found the issue:
- The /api/search endpoint has 3.2s average response time
- Database queries are taking 2.8s (90% of request time)
- Error logs show connection pool exhaustion
- Recommendation: Increase connection pool size
```

## 📁 Architecture

### Directory Structure

```
mcp-server-newrelic/
├── main.py                 # Application entry point
├── cli.py                  # CLI interface
├── core/                   # Core components
│   ├── account_manager.py  # Multi-account support
│   ├── nerdgraph_client.py # Async GraphQL client
│   ├── entity_definitions.py # Golden metrics cache
│   ├── session_manager.py  # Conversation state
│   ├── plugin_loader.py    # Plugin discovery
│   └── telemetry.py       # Observability
├── features/              # Feature plugins
│   ├── common.py          # NRQL & NerdGraph tools
│   ├── entities.py        # Entity search & details
│   ├── apm.py            # APM monitoring
│   ├── alerts.py         # Alerts & incidents
│   ├── infrastructure.py # Infrastructure monitoring
│   ├── logs.py           # Log analysis
│   ├── synthetics.py     # Synthetic monitoring
│   └── docs.py           # Documentation search
└── transports/           # Communication layers
    └── multi_transport.py # STDIO/HTTP support
```

### Plugin System

Create new plugins by extending `PluginBase`:

```python
from core.plugin_loader import PluginBase

class MyPlugin(PluginBase):
    @staticmethod
    def register(app: FastMCP, services: Dict[str, Any]):
        @app.tool()
        async def my_tool(param: str) -> Dict[str, Any]:
            # Tool implementation
            return {"result": "data"}
```

## 🔒 Security

- API keys are stored server-side only
- No credentials exposed to AI models
- Support for environment variables and secure config files
- Audit logging of all tool invocations
- Rate limiting and error handling

## 📊 Monitoring

The server includes built-in telemetry:

```bash
# View server metrics
python cli.py server metrics

# Example output:
{
  "uptime_seconds": 3600,
  "total_tool_calls": 150,
  "tools": {
    "run_nrql_query": {
      "calls": 45,
      "avg_duration_ms": 230,
      "error_rate": 0.02
    }
  }
}
```

## 🚧 Roadmap

- [ ] WebSocket transport for real-time updates
- [ ] Caching layer with Redis
- [ ] Dashboard generation tools
- [ ] Anomaly detection integration
- [ ] Multi-tenant support
- [ ] Prometheus metrics endpoint

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- Built with [FastMCP](https://github.com/anthropics/fastmcp)
- Uses [New Relic Entity Definitions](https://github.com/newrelic/entity-definitions)
- Inspired by the MCP ecosystem

---

*Built with ❤️ for the New Relic community*
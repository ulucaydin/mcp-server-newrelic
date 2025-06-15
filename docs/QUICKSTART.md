# Quick Start Guide

## 5-Minute Setup

### Prerequisites
- Docker installed
- New Relic account with API key

### Quick Install

1. **Clone and Configure**
   ```bash
   git clone https://github.com/deepaucksharma/mcp-server-newrelic.git
   cd mcp-server-newrelic
   
   # Set up credentials
   cp .env.example .env
   # Edit .env with your New Relic API key and account ID
   ```

2. **Start Services**
   ```bash
   docker-compose up -d
   ```

3. **Verify Installation**
   ```bash
   # Check health
   curl http://localhost:8080/health
   
   # Test with Claude Desktop
   # Add to claude_desktop_config.json:
   {
     "mcpServers": {
       "newrelic": {
         "command": "docker",
         "args": ["run", "-i", "--rm", "--env-file", ".env", "uds-mcp:latest"]
       }
     }
   }
   ```

## Basic Usage Examples

### 1. Discover Schemas
```python
# In Claude/AI Assistant
"What schemas are available in my New Relic account?"

# Direct API call
curl -X POST http://localhost:8080/tools/discover_schemas \
  -H "Content-Type: application/json" \
  -d '{"account_id": "123456"}'
```

### 2. Run NRQL Query
```python
# In Claude/AI Assistant
"Show me the average response time for the last hour"

# Direct API call
curl -X POST http://localhost:8080/tools/run_nrql_query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT average(duration) FROM Transaction SINCE 1 hour ago"}'
```

### 3. Analyze Data Quality
```python
# In Claude/AI Assistant
"Analyze the data quality of my Transaction events"

# Direct API call
curl -X POST http://localhost:8080/tools/analyze_data_quality \
  -H "Content-Type: application/json" \
  -d '{"event_type": "Transaction"}'
```

## Common Use Cases

### 1. Troubleshooting Performance
```
"Find the slowest transactions in the last 24 hours and show me their error rates"
```

### 2. Infrastructure Monitoring
```
"List all hosts with CPU usage over 80% and their associated applications"
```

### 3. Alert Management
```
"Show me all critical alerts that fired in the last week and their resolution times"
```

### 4. Data Exploration
```
"What custom attributes are we sending with our Transaction events?"
```

## Configuration Options

### Minimal Configuration (.env)
```bash
# Required
NEW_RELIC_API_KEY=your_api_key_here
NEW_RELIC_ACCOUNT_ID=your_account_id_here

# Optional (defaults shown)
MCP_SERVER_PORT=8080
DISCOVERY_ENGINE_PORT=8081
LOG_LEVEL=info
```

### Advanced Configuration
See [Deployment Guide](./DEPLOYMENT.md) for:
- Production configuration
- Performance tuning
- Security settings
- Scaling options

## Troubleshooting

### Service Won't Start
```bash
# Check logs
docker-compose logs -f

# Verify environment
docker-compose exec mcp-server env | grep NEW_RELIC
```

### Connection Issues
```bash
# Test New Relic connection
curl -H "Api-Key: $NEW_RELIC_API_KEY" \
  https://api.newrelic.com/v2/applications.json
```

### Performance Issues
```bash
# Check resource usage
docker stats

# Increase workers
echo "DISCOVERY_WORKER_COUNT=20" >> .env
docker-compose restart
```

## Next Steps

1. **Explore More Tools**: See [API Reference](./API_REFERENCE.md)
2. **Custom Integration**: Read [Development Guide](./DEVELOPMENT.md)
3. **Production Setup**: Follow [Deployment Guide](./DEPLOYMENT.md)
4. **Contribute**: Check [Contributing Guidelines](./DEVELOPMENT.md#contributing)

## Getting Help

- 📚 [Documentation](https://github.com/deepaucksharma/mcp-server-newrelic/docs)
- 💬 [Discussions](https://github.com/deepaucksharma/mcp-server-newrelic/discussions)
- 🐛 [Issue Tracker](https://github.com/deepaucksharma/mcp-server-newrelic/issues)
- 📧 Email: support@example.com

## Quick Reference Card

| Task | Command/Query |
|------|---------------|
| List APM apps | "Show me all my APM applications" |
| Check errors | "What are the top errors in the last hour?" |
| Find slow queries | "Find database queries taking over 1 second" |
| Monitor hosts | "List hosts with high memory usage" |
| View alerts | "Show me all open alerts" |
| Analyze trends | "How has response time changed this week?" |
# UDS CLI

The UDS CLI provides command-line access to the New Relic Unified Data Service, allowing you to discover schemas, analyze patterns, generate queries, and create dashboards.

## Installation

### From Source
```bash
go install github.com/deepaucksharma/mcp-server-newrelic/cmd/uds@latest
```

### Pre-built Binary
```bash
# Download latest release
curl -L https://github.com/deepaucksharma/mcp-server-newrelic/releases/latest/download/uds-$(uname -s)-$(uname -m) -o uds
chmod +x uds
sudo mv uds /usr/local/bin/
```

## Quick Start

### Initialize Configuration
```bash
uds config init
```

### Set API Endpoint
```bash
uds config set api-url https://uds.newrelic.com/api/v1
```

### List Available Schemas
```bash
uds discovery list
```

### Get Schema Details
```bash
uds discovery profile Transaction
```

## Commands

### Discovery
Explore and analyze data schemas:

```bash
# List all schemas
uds discovery list

# List with filters
uds discovery list --filter "Transaction" --min-records 1000

# Get detailed profile
uds discovery profile Transaction --depth full

# Find relationships
uds discovery relationships Transaction PageView

# Assess data quality
uds discovery quality Transaction --time-range 7d
```

### Pattern Analysis
Analyze patterns and detect anomalies:

```bash
# Analyze patterns in event type
uds pattern analyze Transaction --attributes duration,error

# Detect specific pattern types
uds pattern analyze PageView --pattern-type anomaly --time-range 24h
```

### Query Generation
Generate NRQL queries from natural language:

```bash
# Generate from description
uds query generate "show me the average duration of transactions by app"

# Provide context
uds query generate "find errors" --schemas Transaction,PageView --time-range 1h
```

### Dashboard Creation
Create dashboards from specifications:

```bash
# Create from spec file
uds dashboard create dashboard-spec.yaml

# Override dashboard name
uds dashboard create template.yaml --name "My Custom Dashboard"
```

### MCP Interaction
Connect to MCP server for AI agent interactions:

```bash
# Start interactive session
uds mcp connect

# Run MCP server
uds mcp server --transport http --port 9090
```

### Configuration
Manage CLI settings:

```bash
# Show current configuration
uds config show

# Set configuration values
uds config set output json
uds config set verbose true

# Initialize config file
uds config init
```

## Output Formats

The CLI supports multiple output formats:

- **table** (default) - Human-readable tables
- **json** - JSON output for programmatic use
- **yaml** - YAML output

```bash
# Table output (default)
uds discovery list

# JSON output
uds discovery list -o json

# YAML output
uds discovery list -o yaml
```

## Configuration

Configuration can be set via:
1. Config file (`~/.config/.uds.yaml`)
2. Environment variables (prefix: `UDS_`)
3. Command-line flags

### Config File Example
```yaml
api-url: https://uds.newrelic.com/api/v1
output: table
verbose: false
discovery:
  default-depth: standard
  max-schemas: 50
  min-confidence: 0.7
mcp:
  server-path: mcp-server
  transport: stdio
```

### Environment Variables
```bash
export UDS_API_URL=https://uds.newrelic.com/api/v1
export UDS_OUTPUT=json
export UDS_VERBOSE=true
```

## Advanced Usage

### Scripting
The CLI is designed for scripting with consistent JSON output:

```bash
# Get schema names as JSON array
uds discovery list -o json | jq -r '.schemas[].name'

# Find high-quality schemas
uds discovery list -o json | jq '.schemas[] | select(.quality.overallScore > 0.9)'

# Export relationships to CSV
uds discovery relationships Transaction PageView -o json | \
  jq -r '.relationships[] | [.type, .sourceSchema, .targetSchema, .confidence] | @csv'
```

### Bash Completion
Enable bash completion:

```bash
# Generate completion script
uds completion bash > /etc/bash_completion.d/uds

# Or for current session
source <(uds completion bash)
```

### Integration Examples

#### CI/CD Pipeline
```bash
#!/bin/bash
# Check data quality before deployment
QUALITY_SCORE=$(uds discovery quality Transaction -o json | jq '.metrics.overallScore')
if (( $(echo "$QUALITY_SCORE < 0.8" | bc -l) )); then
  echo "Data quality too low: $QUALITY_SCORE"
  exit 1
fi
```

#### Monitoring Script
```bash
#!/bin/bash
# Monitor for new schemas
SCHEMAS=$(uds discovery list -o json | jq -r '.schemas[].name' | sort)
if [ "$SCHEMAS" != "$PREVIOUS_SCHEMAS" ]; then
  echo "New schemas detected!"
  # Send notification
fi
```

## Troubleshooting

### Connection Issues
```bash
# Test API connectivity
curl -v $(uds config show | grep api-url | awk '{print $2}')/health

# Use verbose mode
uds discovery list -v
```

### Debug Mode
```bash
# Enable debug logging
export UDS_VERBOSE=true
uds discovery list
```

### Common Issues

1. **"API error (status 503)"** - API server not available
   - Check if API server is running
   - Verify API URL configuration

2. **"No config file found"** - Configuration not initialized
   - Run `uds config init`

3. **"Rate limit exceeded"** - Too many requests
   - Wait before retrying
   - Consider using API key for higher limits

## Best Practices

1. **Use Config File** - Store common settings in config file
2. **Script with JSON** - Use JSON output for reliable parsing
3. **Handle Errors** - Check exit codes in scripts
4. **Cache Results** - Avoid repeated API calls
5. **Use Filters** - Reduce data transfer with filters

## Examples

### Full Workflow Example
```bash
# 1. Initialize configuration
uds config init

# 2. Discover available schemas
uds discovery list --min-records 10000

# 3. Profile interesting schema
uds discovery profile Transaction --depth full

# 4. Find related schemas
uds discovery relationships Transaction PageView SystemSample

# 5. Generate query
uds query generate "average transaction duration by app last hour"

# 6. Create dashboard
cat > dashboard.yaml << EOF
name: Transaction Overview
widgets:
  - type: line
    query: "SELECT average(duration) FROM Transaction TIMESERIES"
  - type: billboard
    query: "SELECT count(*) FROM Transaction WHERE error = true"
EOF
uds dashboard create dashboard.yaml
```

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for development setup and guidelines.
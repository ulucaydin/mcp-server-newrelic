# Complete Integration Guide: New Relic MCP Server with AI Assistants

## Overview

This comprehensive guide covers how to integrate the New Relic MCP Server with popular AI development assistants including GitHub Copilot, Claude Code, and Claude Desktop. The Model Context Protocol (MCP) enables these AI assistants to securely access New Relic observability data, providing intelligent insights directly within your development workflow.

## Table of Contents

1. [GitHub Copilot Integration](#github-copilot-integration)
2. [Claude Code Integration](#claude-code-integration)
3. [Claude Desktop Integration](#claude-desktop-integration)
4. [Configuration Management](#configuration-management)
5. [Security Considerations](#security-considerations)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Usage Patterns](#advanced-usage-patterns)
8. [Performance Optimization](#performance-optimization)

---

## GitHub Copilot Integration

### Prerequisites

- GitHub Copilot Chat extension for VS Code
- VS Code version 1.85.0 or later
- Python 3.11+ installed
- New Relic API key with appropriate permissions

### Method 1: VS Code Extension Configuration

#### Step 1: Install the MCP Server

```bash
# Clone the repository
git clone <repository-url>
cd mcp-server-newrelic

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your New Relic credentials
```

#### Step 2: Configure VS Code Settings

Create or modify `.vscode/settings.json` in your workspace:

```json
{
  "github.copilot.chat.experimental.mcp": {
    "enabled": true,
    "servers": {
      "newrelic": {
        "command": "python",
        "args": ["/path/to/mcp-server-newrelic/main.py"],
        "env": {
          "MCP_TRANSPORT": "http",
          "HTTP_HOST": "127.0.0.1",
          "HTTP_PORT": "3000",
          "NEW_RELIC_API_KEY": "${env:NEW_RELIC_API_KEY}",
          "NEW_RELIC_ACCOUNT_ID": "${env:NEW_RELIC_ACCOUNT_ID}",
          "LOG_LEVEL": "INFO"
        },
        "initializationOptions": {
          "timeout": 30000,
          "retries": 3
        }
      }
    }
  }
}
```

#### Step 3: Environment Variables Setup

Create a `.env` file in your workspace root:

```bash
NEW_RELIC_API_KEY=NRAK-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
NEW_RELIC_ACCOUNT_ID=1234567
NEW_RELIC_REGION=US
MCP_TRANSPORT=http
HTTP_HOST=127.0.0.1
HTTP_PORT=3000
```

#### Step 4: Start the MCP Server

```bash
# Method A: Direct execution
python main.py

# Method B: Using Docker
docker-compose up mcp-server

# Method C: Using the CLI
python cli.py server --transport http --port 3000
```

#### Step 5: Verify Integration

1. Open VS Code
2. Open GitHub Copilot Chat (`Ctrl+Shift+I` or `Cmd+Shift+I`)
3. Test the integration:

```
@copilot /newrelic What are the current error rates for my applications?
```

### Method 2: GitHub Copilot Extensions API

For deeper integration, you can create a GitHub Copilot Extension:

#### Step 1: Create Extension Manifest

Create `copilot-extension.json`:

```json
{
  "name": "newrelic-mcp-extension",
  "displayName": "New Relic Observability",
  "description": "Access New Relic metrics and insights via MCP",
  "version": "1.0.0",
  "publisher": "your-org",
  "engines": {
    "copilot": "^1.0.0"
  },
  "contributes": {
    "copilot": {
      "instructions": [
        {
          "file": "instructions.md"
        }
      ],
      "tools": [
        {
          "name": "search_entities",
          "description": "Search for New Relic entities"
        },
        {
          "name": "run_nrql_query", 
          "description": "Execute NRQL queries"
        },
        {
          "name": "get_apm_metrics",
          "description": "Get APM application metrics"
        }
      ]
    }
  },
  "scripts": {
    "start": "python main.py"
  }
}
```

#### Step 2: Create Instructions File

Create `instructions.md`:

```markdown
# New Relic MCP Extension

This extension provides access to New Relic observability data through the Model Context Protocol.

## Available Commands

- `/nr-search <query>` - Search for entities
- `/nr-query <nrql>` - Execute NRQL queries  
- `/nr-metrics <app-name>` - Get application metrics
- `/nr-alerts` - List recent alerts and incidents
- `/nr-health` - Check system health status

## Usage Examples

```
/nr-search name:myapp type:APPLICATION
/nr-query "SELECT count(*) FROM Transaction SINCE 1 hour ago"
/nr-metrics "My Web Application"
```
```

---

## Claude Code Integration

### Prerequisites

- Claude Code CLI installed
- Python 3.11+ installed
- New Relic API key

### Step 1: Install and Configure

```bash
# Install Claude Code (if not already installed)
npm install -g @anthropic-ai/claude-code

# Clone and setup MCP server
git clone <repository-url>
cd mcp-server-newrelic
pip install -r requirements.txt
```

### Step 2: Create MCP Configuration

Create `mcp-config.json`:

```json
{
  "mcpServers": {
    "newrelic": {
      "command": "python",
      "args": ["main.py"],
      "cwd": "/path/to/mcp-server-newrelic",
      "env": {
        "NEW_RELIC_API_KEY": "${env:NEW_RELIC_API_KEY}",
        "NEW_RELIC_ACCOUNT_ID": "${env:NEW_RELIC_ACCOUNT_ID}",
        "MCP_TRANSPORT": "stdio",
        "LOG_LEVEL": "INFO",
        "USE_ENHANCED_PLUGINS": "true"
      }
    }
  }
}
```

### Step 3: Initialize Claude Code with MCP

```bash
# Initialize Claude Code with MCP configuration
claude-code init --mcp-config=mcp-config.json

# Or add to existing Claude Code configuration
claude-code config add-mcp-server newrelic \
  --command="python main.py" \
  --cwd="/path/to/mcp-server-newrelic"
```

### Step 4: Environment Setup

```bash
# Set environment variables
export NEW_RELIC_API_KEY="NRAK-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
export NEW_RELIC_ACCOUNT_ID="1234567"
export NEW_RELIC_REGION="US"
```

### Step 5: Usage Examples

```bash
# Start Claude Code with New Relic context
claude-code chat

# Example interactions:
```

**Chat Session:**
```
User: What's the error rate for my applications in the last hour?

Claude: I'll check the error rates for your applications using New Relic.

[Calls: search_entities(entity_type="APPLICATION")]
[Calls: run_nrql_query(nrql="SELECT percentage(count(*), WHERE error IS true) FROM Transaction SINCE 1 hour ago FACET appName")]

Based on the data from New Relic:

1. **WebApp-Production**: 0.23% error rate (23 errors out of 10,045 transactions)
2. **API-Service**: 0.15% error rate (8 errors out of 5,233 transactions)  
3. **Background-Worker**: 0.05% error rate (2 errors out of 4,011 transactions)

All applications are performing within normal thresholds (<1% error rate).
```

### Step 6: Advanced Claude Code Integration

Create a custom workflow file `.claude/workflows/newrelic-analysis.yml`:

```yaml
name: New Relic Analysis
description: Automated observability analysis using New Relic data

triggers:
  - command: "analyze-performance"
  - schedule: "daily"

steps:
  - name: "Get Application Health"
    tool: "search_entities"
    params:
      entity_type: "APPLICATION"
      limit: 20
    
  - name: "Check Error Rates"
    tool: "run_nrql_query"
    params:
      nrql: "SELECT percentage(count(*), WHERE error IS true) FROM Transaction SINCE 24 hours ago FACET appName"
    
  - name: "Performance Analysis"
    tool: "run_nrql_query"
    params:
      nrql: "SELECT average(duration), percentile(duration, 95) FROM Transaction SINCE 24 hours ago FACET appName"
    
  - name: "Alert Summary"
    tool: "list_recent_incidents"
    params:
      hours: 24
      
  - name: "Generate Report"
    action: "summarize"
    template: |
      # Daily New Relic Health Report
      
      ## Application Performance
      {{performance_data}}
      
      ## Error Analysis  
      {{error_data}}
      
      ## Recent Incidents
      {{alerts_data}}
      
      ## Recommendations
      {{ai_recommendations}}
```

---

## Claude Desktop Integration

### Prerequisites

- Claude Desktop application
- Python 3.11+ installed
- New Relic API key

### Step 1: Install Claude Desktop

Download and install Claude Desktop from the official Anthropic website.

### Step 2: Configure MCP Server

Create the MCP configuration file for Claude Desktop:

**On macOS:**
```bash
mkdir -p ~/Library/Application\ Support/Claude/
cat > ~/Library/Application\ Support/Claude/claude_desktop_config.json << 'EOF'
{
  "mcpServers": {
    "newrelic": {
      "command": "python",
      "args": ["/path/to/mcp-server-newrelic/main.py"],
      "env": {
        "NEW_RELIC_API_KEY": "NRAK-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        "NEW_RELIC_ACCOUNT_ID": "1234567",
        "MCP_TRANSPORT": "stdio",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
EOF
```

**On Windows:**
```powershell
$configPath = "$env:APPDATA\Claude\claude_desktop_config.json"
New-Item -ItemType Directory -Force -Path (Split-Path $configPath)

$config = @{
  mcpServers = @{
    newrelic = @{
      command = "python"
      args = @("/path/to/mcp-server-newrelic/main.py")
      env = @{
        NEW_RELIC_API_KEY = "NRAK-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
        NEW_RELIC_ACCOUNT_ID = "1234567"
        MCP_TRANSPORT = "stdio"
        LOG_LEVEL = "INFO"
      }
    }
  }
} | ConvertTo-Json -Depth 4

$config | Out-File -FilePath $configPath -Encoding utf8
```

**On Linux:**
```bash
mkdir -p ~/.config/Claude/
cat > ~/.config/Claude/claude_desktop_config.json << 'EOF'
{
  "mcpServers": {
    "newrelic": {
      "command": "python",
      "args": ["/path/to/mcp-server-newrelic/main.py"],
      "env": {
        "NEW_RELIC_API_KEY": "NRAK-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        "NEW_RELIC_ACCOUNT_ID": "1234567",
        "MCP_TRANSPORT": "stdio",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
EOF
```

### Step 3: Verify Installation

1. Restart Claude Desktop
2. Look for the MCP server icon/indicator in the interface
3. Test with a simple query:

```
Can you show me the current health status of my New Relic monitored applications?
```

### Step 4: Advanced Usage Patterns

#### Performance Analysis Conversations

```
User: I'm seeing slow response times in production. Can you help me investigate?

Claude: I'll help you investigate the performance issues. Let me start by checking your application metrics.

[Analyzes APM data, identifies bottlenecks, provides recommendations]
```

#### Incident Response Workflows

```
User: We have an ongoing incident. Can you give me a situation report?

Claude: I'll gather the current incident status and related metrics to give you a comprehensive situation report.

[Checks recent incidents, correlates with performance data, suggests next steps]
```

#### Proactive Monitoring

```
User: Set up a daily health check routine for my applications.

Claude: I'll create a comprehensive daily health check that covers key metrics and potential issues.

[Establishes baseline metrics, identifies trends, provides alerts]
```

---

## Configuration Management

### Environment-Based Configuration

Create different configuration files for different environments:

#### Development Configuration

```json
{
  "mcpServers": {
    "newrelic-dev": {
      "command": "python",
      "args": ["main.py"],
      "env": {
        "NEW_RELIC_API_KEY": "${env:NEW_RELIC_DEV_API_KEY}",
        "NEW_RELIC_ACCOUNT_ID": "${env:NEW_RELIC_DEV_ACCOUNT_ID}",
        "LOG_LEVEL": "DEBUG",
        "DEBUG_MODE": "true",
        "CACHE_BACKEND": "memory"
      }
    }
  }
}
```

#### Production Configuration

```json
{
  "mcpServers": {
    "newrelic-prod": {
      "command": "python",
      "args": ["main.py"],
      "env": {
        "NEW_RELIC_API_KEY": "${env:NEW_RELIC_PROD_API_KEY}",
        "NEW_RELIC_ACCOUNT_ID": "${env:NEW_RELIC_PROD_ACCOUNT_ID}",
        "LOG_LEVEL": "INFO",
        "ENABLE_AUDIT_LOGGING": "true",
        "CACHE_BACKEND": "redis",
        "REDIS_URL": "redis://localhost:6379"
      }
    }
  }
}
```

### Multi-Account Configuration

For organizations with multiple New Relic accounts:

```json
{
  "mcpServers": {
    "newrelic-team-a": {
      "command": "python",
      "args": ["main.py"],
      "env": {
        "NEW_RELIC_API_KEY": "${env:TEAM_A_API_KEY}",
        "NEW_RELIC_ACCOUNT_ID": "${env:TEAM_A_ACCOUNT_ID}"
      }
    },
    "newrelic-team-b": {
      "command": "python", 
      "args": ["main.py"],
      "env": {
        "NEW_RELIC_API_KEY": "${env:TEAM_B_API_KEY}",
        "NEW_RELIC_ACCOUNT_ID": "${env:TEAM_B_ACCOUNT_ID}"
      }
    }
  }
}
```

---

## Security Considerations

### API Key Management

#### Best Practices

1. **Never hardcode API keys** in configuration files
2. **Use environment variables** or secure credential stores
3. **Rotate API keys regularly** (quarterly recommended)
4. **Use least-privilege access** - only grant necessary permissions
5. **Monitor API key usage** through New Relic's audit logs

#### Secure Storage Options

**Option 1: Environment Variables**
```bash
# .env file (never commit to version control)
NEW_RELIC_API_KEY=NRAK-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
NEW_RELIC_ACCOUNT_ID=1234567
```

**Option 2: OS Keychain (macOS)**
```bash
# Store in keychain
security add-generic-password -a "newrelic-api" -s "mcp-server" -w "NRAK-XXXXXXXX"

# Retrieve in script
API_KEY=$(security find-generic-password -a "newrelic-api" -s "mcp-server" -w)
```

**Option 3: Windows Credential Manager**
```powershell
# Store credential
cmdkey /add:newrelic-api /user:mcp-server /pass:NRAK-XXXXXXXX

# Retrieve in script
$credential = Get-StoredCredential -Target "newrelic-api"
```

**Option 4: Linux Secret Service**
```bash
# Using secret-tool
echo "NRAK-XXXXXXXX" | secret-tool store --label="New Relic API Key" service newrelic-api username mcp-server

# Retrieve
API_KEY=$(secret-tool lookup service newrelic-api username mcp-server)
```

### Network Security

#### HTTPS/TLS Configuration

For HTTP transport mode:

```json
{
  "mcpServers": {
    "newrelic": {
      "command": "python",
      "args": ["main.py"],
      "env": {
        "MCP_TRANSPORT": "https",
        "HTTPS_CERT_FILE": "/path/to/cert.pem",
        "HTTPS_KEY_FILE": "/path/to/key.pem",
        "HTTPS_CA_FILE": "/path/to/ca.pem"
      }
    }
  }
}
```

#### Request Signing (Enhanced Security)

Enable request signing for additional security:

```json
{
  "env": {
    "ENABLE_REQUEST_SIGNING": "true",
    "SIGNING_SECRET_KEY": "${env:MCP_SIGNING_SECRET}",
    "SIGNATURE_ALGORITHM": "HMAC-SHA256",
    "MAX_TIMESTAMP_DRIFT": "300"
  }
}
```

### Access Control

#### Role-Based Access Control (RBAC)

Configure user permissions:

```json
{
  "env": {
    "ENABLE_RBAC": "true",
    "USER_PERMISSIONS": "read:entities,read:metrics,write:none"
  }
}
```

#### IP Allowlisting

Restrict access by IP address:

```json
{
  "env": {
    "ALLOWED_IPS": "192.168.1.0/24,10.0.0.0/8",
    "ENABLE_IP_FILTERING": "true"
  }
}
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. MCP Server Not Starting

**Symptoms:**
- AI assistant can't connect to New Relic
- "Server unavailable" errors
- No response from MCP tools

**Solutions:**

```bash
# Check server status
python main.py --check-health

# Verify environment variables
python -c "import os; print('API Key:', os.getenv('NEW_RELIC_API_KEY', 'NOT SET'))"

# Test API connectivity
python -c "
from core.nerdgraph_client import NerdGraphClient
import asyncio
async def test():
    client = NerdGraphClient(api_key='YOUR_KEY')
    result = await client.query('{ actor { user { email } } }')
    print('Connection successful:', result)
asyncio.run(test())
"

# Check port availability
netstat -an | grep 3000  # Check if port is in use

# Run in debug mode
LOG_LEVEL=DEBUG python main.py
```

#### 2. Authentication Failures

**Symptoms:**
- "Invalid API key" errors
- "Unauthorized" responses
- Empty query results

**Solutions:**

```bash
# Verify API key format
echo $NEW_RELIC_API_KEY | grep -E '^NRAK-[A-Z0-9]{40}$'

# Test API key permissions
curl -H "Api-Key: $NEW_RELIC_API_KEY" \
     -H "Content-Type: application/json" \
     -X POST \
     -d '{"query": "{ actor { user { email } } }"}' \
     https://api.newrelic.com/graphql

# Check account ID
python -c "
import os
print('Account ID:', os.getenv('NEW_RELIC_ACCOUNT_ID'))
print('Type:', type(os.getenv('NEW_RELIC_ACCOUNT_ID')))
"
```

#### 3. Performance Issues

**Symptoms:**
- Slow response times
- Timeout errors
- High memory usage

**Solutions:**

```bash
# Enable performance monitoring
export ENABLE_PROMETHEUS_METRICS=true
export PROMETHEUS_PORT=9090

# Monitor metrics
curl http://localhost:9090/metrics

# Optimize cache settings
export CACHE_MAX_SIZE=2000
export CACHE_MAX_MEMORY_MB=200
export CACHE_DEFAULT_TTL=600

# Increase connection pool size
export CONNECTION_POOL_SIZE=20
export MAX_CONCURRENT_REQUESTS=50

# Run performance benchmarks
python -m pytest tests/benchmarks/ -v
```

#### 4. Integration-Specific Issues

**GitHub Copilot Issues:**
```bash
# Check VS Code MCP configuration
code --list-extensions | grep copilot

# Verify MCP server registration
ls ~/.vscode/extensions/ | grep copilot

# Check VS Code logs
tail -f ~/Library/Logs/com.microsoft.VSCode/main.log
```

**Claude Desktop Issues:**
```bash
# Check configuration file location
ls ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Validate JSON configuration
python -c "
import json
with open('claude_desktop_config.json') as f:
    config = json.load(f)
    print('Configuration valid')
"

# Check Claude Desktop logs (macOS)
tail -f ~/Library/Logs/Claude\ Desktop/main.log
```

### Diagnostic Commands

#### Server Health Check

```bash
# Comprehensive health check
python cli.py health-check

# Individual component checks
python cli.py check --component nerdgraph
python cli.py check --component cache
python cli.py check --component plugins
```

#### Connection Testing

```bash
# Test MCP connection
python cli.py test-mcp-connection

# Test specific tools
python cli.py test-tool search_entities --params '{"limit": 5}'
python cli.py test-tool run_nrql_query --params '{"nrql": "SELECT count(*) FROM Transaction SINCE 1 hour ago"}'
```

#### Log Analysis

```bash
# Real-time log monitoring
tail -f logs/mcp-server.log | grep ERROR

# Performance metrics
grep "Query latency" logs/mcp-server.log | tail -20

# Security events
grep -i "security\|auth\|unauthorized" logs/audit.log
```

---

## Advanced Usage Patterns

### 1. Automated Incident Response

Create AI-driven incident response workflows:

#### GitHub Copilot Workflow

```typescript
// .vscode/copilot-workflows/incident-response.ts
export const incidentResponseWorkflow = {
  name: "Incident Response Analysis",
  trigger: "on-alert",
  
  async execute(context: CopilotContext) {
    // Step 1: Get incident details
    const incidents = await context.mcp.call("list_recent_incidents", {
      status: "open",
      limit: 5
    });
    
    // Step 2: Analyze impact
    for (const incident of incidents) {
      const metrics = await context.mcp.call("get_entity_golden_signals", {
        guid: incident.entityGuid
      });
      
      // Step 3: Check dependencies
      const dependencies = await context.mcp.call("get_entity_relationships", {
        guid: incident.entityGuid
      });
      
      // Step 4: Generate report
      await context.generateIncidentReport({
        incident,
        metrics,
        dependencies
      });
    }
  }
};
```

#### Claude Desktop Conversation Template

```
User: We have a P1 incident affecting our checkout service. Can you help with the incident response?

Claude: I'll immediately analyze the incident and provide a comprehensive response plan.

[Analysis Steps:]
1. Current incident status and severity
2. Impact assessment on critical user journeys  
3. Related system dependencies and cascade effects
4. Historical pattern analysis
5. Immediate mitigation recommendations
6. Communication template for stakeholders

Let me gather the data...

[Executes multiple MCP calls to build complete picture]

## Incident Response Analysis

### Current Status
- **Service**: Checkout Service (GUID: ABC123)
- **Status**: CRITICAL - 15% error rate (baseline: 0.2%)
- **Duration**: 23 minutes
- **Impact**: ~2,400 failed transactions

### Root Cause Analysis
Based on the metrics correlation:
- Error spike started at 14:32 UTC
- Coincides with deployment marker
- Database connection pool exhaustion detected
- Downstream payment service also showing latency

### Immediate Actions
1. **Rollback** the recent deployment (deployed 14:30 UTC)
2. **Scale up** database connection pools
3. **Monitor** payment service recovery
4. **Communicate** with customer support team

### Recovery Plan
[Detailed step-by-step recovery procedures...]
```

### 2. Performance Optimization Workflows

#### Claude Code Integration

Create performance analysis workflows:

```yaml
# .claude/workflows/performance-optimization.yml
name: Weekly Performance Review
description: Automated performance analysis and optimization recommendations

schedule: "0 9 * * MON"  # Every Monday at 9 AM

steps:
  - name: "Collect Performance Data"
    parallel:
      - tool: "run_nrql_query"
        params:
          nrql: "SELECT average(duration), percentile(duration, 95, 99) FROM Transaction SINCE 1 week ago FACET appName"
      - tool: "run_nrql_query" 
        params:
          nrql: "SELECT rate(count(*), 1 minute) FROM Transaction SINCE 1 week ago FACET appName TIMESERIES"
      - tool: "run_nrql_query"
        params:
          nrql: "SELECT percentage(count(*), WHERE error IS true) FROM Transaction SINCE 1 week ago FACET appName"
  
  - name: "Analyze Trends"
    tool: "run_nrql_query"
    params:
      nrql: "SELECT compare(average(duration), 1 week ago) FROM Transaction SINCE 1 week ago FACET appName"
  
  - name: "Identify Bottlenecks"
    tool: "run_nrql_query"
    params:
      nrql: "SELECT count(*), average(databaseDuration), average(externalDuration) FROM Transaction WHERE duration > 2 SINCE 1 week ago FACET name"
  
  - name: "Generate Report"
    action: "compile_report"
    template: "performance-weekly-template.md"
    output: "reports/performance-week-{{date}}.md"
```

### 3. Deployment Impact Analysis

#### Automated Deployment Monitoring

```python
# scripts/deployment-monitor.py
import asyncio
from datetime import datetime, timedelta
from core.nerdgraph_client import NerdGraphClient

async def analyze_deployment_impact(deployment_time, app_name):
    client = NerdGraphClient(api_key=os.getenv("NEW_RELIC_API_KEY"))
    
    # Define time windows
    before_window = deployment_time - timedelta(hours=1)
    after_window = deployment_time + timedelta(hours=1)
    
    # Compare metrics before and after deployment
    comparison_query = f"""
    SELECT 
      average(duration) as avg_response_time,
      percentile(duration, 95) as p95_response_time,
      percentage(count(*), WHERE error IS true) as error_rate,
      rate(count(*), 1 minute) as throughput
    FROM Transaction 
    WHERE appName = '{app_name}'
    SINCE '{before_window.isoformat()}'
    UNTIL '{after_window.isoformat()}'
    TIMESERIES 30 minutes
    """
    
    results = await client.query_nrql(comparison_query)
    
    # Analyze for regressions
    regression_analysis = analyze_regression(results)
    
    return {
        "deployment_time": deployment_time,
        "application": app_name,
        "metrics_comparison": results,
        "regression_detected": regression_analysis.has_regression,
        "recommendations": regression_analysis.recommendations
    }

# Usage in CI/CD pipeline
# python deployment-monitor.py --app "MyApp" --deployment-time "2024-01-15T14:30:00Z"
```

### 4. Capacity Planning

#### Predictive Analysis Workflow

```python
# workflows/capacity-planning.py
async def generate_capacity_forecast():
    """Generate capacity planning recommendations based on trends"""
    
    # Collect historical data
    historical_data = await mcp_client.call("run_nrql_query", {
        "nrql": """
        SELECT average(cpuPercent), average(memoryUsedPercent), 
               rate(count(*), 1 minute) as throughput
        FROM SystemSample, Transaction
        WHERE hostname LIKE 'prod-%'
        SINCE 3 months ago
        TIMESERIES 1 day
        """
    })
    
    # Analyze growth trends
    growth_analysis = analyze_growth_trends(historical_data)
    
    # Predict future requirements
    forecast = generate_forecast(growth_analysis, horizon_days=90)
    
    # Generate recommendations
    recommendations = {
        "scaling_timeline": forecast.scaling_events,
        "resource_requirements": forecast.resource_needs,
        "cost_projections": forecast.cost_estimates,
        "risk_factors": forecast.risk_assessment
    }
    
    return recommendations
```

---

## Performance Optimization

### 1. Caching Strategies

#### Client-Side Caching

Configure aggressive caching for stable data:

```json
{
  "env": {
    "CACHE_DEFAULT_TTL": "900",
    "CACHE_MAX_SIZE": "5000",
    "CACHE_MAX_MEMORY_MB": "500",
    "ENTITY_CACHE_TTL": "3600",
    "METRICS_CACHE_TTL": "300"
  }
}
```

#### Query Optimization

Optimize NRQL queries for better performance:

```sql
-- Inefficient: Scanning all data
SELECT * FROM Transaction SINCE 1 day ago

-- Optimized: Specific fields and constraints
SELECT appName, average(duration), count(*) 
FROM Transaction 
WHERE duration > 0.1 
SINCE 1 day ago 
FACET appName 
LIMIT 100
```

### 2. Connection Pooling

#### Optimal Pool Configuration

```python
# Recommended settings for different environments

# Development
CONNECTION_POOL_SIZE=5
MAX_CONCURRENT_REQUESTS=10

# Staging  
CONNECTION_POOL_SIZE=10
MAX_CONCURRENT_REQUESTS=25

# Production
CONNECTION_POOL_SIZE=20
MAX_CONCURRENT_REQUESTS=50
```

### 3. Monitoring and Alerting

#### Performance Metrics Monitoring

```python
# Set up performance monitoring
ENABLE_PROMETHEUS_METRICS=true
PROMETHEUS_PORT=9090

# Key metrics to monitor:
# - mcp_request_duration_seconds
# - mcp_request_total
# - mcp_cache_hit_ratio
# - mcp_connection_pool_active
# - mcp_memory_usage_bytes
```

#### Alerting Rules

```yaml
# prometheus-alerts.yml
groups:
  - name: mcp-server-alerts
    rules:
      - alert: MCPHighLatency
        expr: histogram_quantile(0.95, mcp_request_duration_seconds_bucket) > 1.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "MCP Server high latency detected"
          
      - alert: MCPHighErrorRate
        expr: rate(mcp_request_total{status="error"}[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "MCP Server error rate too high"
```

---

## Conclusion

This comprehensive integration guide provides everything needed to successfully deploy and use the New Relic MCP Server with popular AI development assistants. The integration enables:

1. **Seamless Observability**: Direct access to New Relic data within development workflows
2. **AI-Powered Insights**: Intelligent analysis and recommendations from observability data
3. **Automated Workflows**: Incident response, performance monitoring, and capacity planning
4. **Enhanced Productivity**: Reduced context switching between tools and interfaces

### Next Steps

1. **Choose your integration method** based on your primary development environment
2. **Follow the setup instructions** for your chosen AI assistant
3. **Configure security settings** appropriate for your organization
4. **Test the integration** with sample queries and workflows
5. **Customize workflows** for your specific use cases
6. **Monitor performance** and optimize configuration as needed

### Support and Resources

- **Documentation**: Full API reference and examples
- **Community**: GitHub discussions and issue tracking
- **Examples**: Sample workflows and integration patterns
- **Security**: Best practices and security guidelines

The New Relic MCP Server transforms how development teams interact with observability data, making it an integral part of the AI-assisted development workflow.

---

*Last updated: January 2025*  
*Version: 1.0.0*  
*Compatible with: GitHub Copilot, Claude Code, Claude Desktop*
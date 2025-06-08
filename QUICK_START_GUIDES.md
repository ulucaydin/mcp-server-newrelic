# Quick Start Guides: New Relic MCP Server Integration

## 🚀 5-Minute Quick Starts

### GitHub Copilot Quick Start

#### Prerequisites Check
```bash
# Verify you have the requirements
code --version  # VS Code 1.85.0+
python3 --version  # Python 3.11+
echo $NEW_RELIC_API_KEY  # Should show your API key
```

#### 1-2-3 Setup
```bash
# 1. Clone and install
git clone <repo-url> && cd mcp-server-newrelic
pip install -r requirements.txt

# 2. Configure VS Code
mkdir -p .vscode
cat > .vscode/settings.json << 'EOF'
{
  "github.copilot.chat.experimental.mcp": {
    "enabled": true,
    "servers": {
      "newrelic": {
        "command": "python",
        "args": ["main.py"],
        "env": {
          "NEW_RELIC_API_KEY": "${env:NEW_RELIC_API_KEY}",
          "MCP_TRANSPORT": "http",
          "HTTP_PORT": "3000"
        }
      }
    }
  }
}
EOF

# 3. Start server and test
python main.py &
code .
```

#### Test in Copilot Chat
```
@copilot /newrelic show me my application error rates
```

---

### Claude Code Quick Start

#### One-Command Setup
```bash
# Complete setup in one go
curl -sSL https://raw.githubusercontent.com/your-org/mcp-server-newrelic/main/scripts/claude-setup.sh | bash
```

#### Manual Setup (Alternative)
```bash
# 1. Install and configure
npm install -g @anthropic-ai/claude-code
git clone <repo-url> && cd mcp-server-newrelic
pip install -r requirements.txt

# 2. Create config
cat > claude-mcp-config.json << 'EOF'
{
  "mcpServers": {
    "newrelic": {
      "command": "python",
      "args": ["main.py"],
      "env": {
        "NEW_RELIC_API_KEY": "${env:NEW_RELIC_API_KEY}",
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
EOF

# 3. Initialize and start
claude-code init --mcp-config=claude-mcp-config.json
claude-code chat
```

#### Test Commands
```bash
# In Claude Code chat:
What are my top 5 slowest transactions today?
Show me any recent alerts or incidents
Analyze the performance trends for my web applications
```

---

### Claude Desktop Quick Start

#### macOS One-Liner
```bash
curl -sSL https://raw.githubusercontent.com/your-org/mcp-server-newrelic/main/scripts/claude-desktop-setup-macos.sh | bash
```

#### Manual Setup
```bash
# 1. Clone and install server
git clone <repo-url> && cd mcp-server-newrelic
pip install -r requirements.txt

# 2. Configure Claude Desktop
mkdir -p ~/Library/Application\ Support/Claude/
cat > ~/Library/Application\ Support/Claude/claude_desktop_config.json << 'EOF'
{
  "mcpServers": {
    "newrelic": {
      "command": "python",
      "args": ["/full/path/to/mcp-server-newrelic/main.py"],
      "env": {
        "NEW_RELIC_API_KEY": "YOUR_API_KEY_HERE",
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
EOF

# 3. Restart Claude Desktop and test
```

#### Test Conversation
```
Can you help me analyze the current health of my New Relic monitored applications?
```

---

## 🎯 Platform-Specific Commands

### GitHub Copilot Chat Commands

```bash
# Application Performance
@copilot /newrelic What's the error rate for MyApp?
@copilot /newrelic Show me slow queries in the last hour
@copilot /newrelic Compare today's performance vs yesterday

# Infrastructure Monitoring  
@copilot /newrelic Which hosts have high CPU usage?
@copilot /newrelic Show me database performance metrics
@copilot /newrelic List all infrastructure alerts

# Incident Management
@copilot /newrelic Are there any open incidents?
@copilot /newrelic What happened during the 2PM deployment?
@copilot /newrelic Show me the blast radius for this alert

# Custom Analysis
@copilot /newrelic Run this NRQL: SELECT count(*) FROM Transaction FACET name
@copilot /newrelic Help me troubleshoot high memory usage
@copilot /newrelic Generate a performance report for last week
```

### Claude Code Workflow Examples

```bash
# Start focused sessions
claude-code chat --context="incident-response"
claude-code chat --context="performance-analysis" 
claude-code chat --context="deployment-validation"

# Generate reports
claude-code generate --template="weekly-performance-report"
claude-code generate --template="incident-postmortem"

# Automated analysis
claude-code analyze --target="production-apps" --type="performance"
claude-code analyze --target="recent-deployments" --type="impact"
```

### Claude Desktop Conversation Starters

```
# Daily Standups
"Give me a quick health summary for our production applications"

# Incident Response
"We're seeing issues with checkout - help me investigate"

# Performance Reviews
"Analyze our application performance trends over the last month"

# Capacity Planning
"Based on current growth, when will we need to scale our infrastructure?"

# Deployment Analysis
"Check if our latest deployment caused any performance regressions"

# Proactive Monitoring
"What potential issues should I be aware of based on current metrics?"
```

---

## 🔧 Common Configuration Patterns

### Multi-Environment Setup

```json
{
  "mcpServers": {
    "newrelic-dev": {
      "command": "python",
      "args": ["main.py"],
      "env": {
        "NEW_RELIC_API_KEY": "${env:NR_DEV_API_KEY}",
        "NEW_RELIC_ACCOUNT_ID": "${env:NR_DEV_ACCOUNT_ID}",
        "ENVIRONMENT": "development"
      }
    },
    "newrelic-prod": {
      "command": "python", 
      "args": ["main.py"],
      "env": {
        "NEW_RELIC_API_KEY": "${env:NR_PROD_API_KEY}",
        "NEW_RELIC_ACCOUNT_ID": "${env:NR_PROD_ACCOUNT_ID}",
        "ENVIRONMENT": "production"
      }
    }
  }
}
```

### Team-Specific Configurations

```json
{
  "mcpServers": {
    "newrelic-frontend": {
      "command": "python",
      "args": ["main.py"],
      "env": {
        "NEW_RELIC_API_KEY": "${env:FRONTEND_TEAM_API_KEY}",
        "DEFAULT_ENTITY_FILTER": "domain = 'BROWSER'",
        "TEAM_CONTEXT": "frontend"
      }
    },
    "newrelic-backend": {
      "command": "python",
      "args": ["main.py"], 
      "env": {
        "NEW_RELIC_API_KEY": "${env:BACKEND_TEAM_API_KEY}",
        "DEFAULT_ENTITY_FILTER": "domain = 'APM'",
        "TEAM_CONTEXT": "backend"
      }
    }
  }
}
```

### High-Performance Configuration

```json
{
  "mcpServers": {
    "newrelic": {
      "command": "python",
      "args": ["main.py"],
      "env": {
        "NEW_RELIC_API_KEY": "${env:NEW_RELIC_API_KEY}",
        "CONNECTION_POOL_SIZE": "25",
        "CACHE_MAX_SIZE": "5000",
        "CACHE_MAX_MEMORY_MB": "500",
        "ENABLE_REDIS_CACHE": "true",
        "REDIS_URL": "redis://localhost:6379"
      }
    }
  }
}
```

---

## 🐛 Quick Troubleshooting

### Server Won't Start

```bash
# Check environment
python -c "import os; print('API Key set:', bool(os.getenv('NEW_RELIC_API_KEY')))"

# Test connection
python -c "
from core.nerdgraph_client import NerdGraphClient
import asyncio
async def test():
    try:
        client = NerdGraphClient(api_key=os.getenv('NEW_RELIC_API_KEY'))
        result = await client.query('{ actor { user { email } } }')
        print('✅ Connection successful')
    except Exception as e:
        print('❌ Connection failed:', e)
asyncio.run(test())
"

# Check dependencies
pip install -r requirements.txt --upgrade

# Run in debug mode
LOG_LEVEL=DEBUG python main.py
```

### AI Assistant Can't Connect

```bash
# Check if server is running
curl http://localhost:3000/health || echo "Server not responding"

# Verify MCP configuration
cat ~/.config/Claude/claude_desktop_config.json | python -m json.tool

# Check logs
tail -f ~/.config/Claude/logs/mcp-server.log

# Restart AI assistant
pkill -f "Claude Desktop" && open -a "Claude Desktop"
```

### Performance Issues

```bash
# Check server metrics
curl http://localhost:9090/metrics | grep mcp_

# Monitor resource usage
htop -p $(pgrep -f "python main.py")

# Optimize cache
export CACHE_MAX_SIZE=2000
export CACHE_DEFAULT_TTL=600

# Enable performance monitoring
export ENABLE_PROMETHEUS_METRICS=true
```

---

## 📋 Setup Verification Checklist

### Pre-Integration Checklist

- [ ] New Relic API key obtained and tested
- [ ] Python 3.11+ installed and accessible
- [ ] Git repository cloned locally
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Environment variables configured
- [ ] AI assistant (Copilot/Claude) installed and updated

### Post-Integration Checklist

- [ ] MCP server starts without errors
- [ ] AI assistant recognizes MCP server
- [ ] Basic New Relic queries work
- [ ] Error handling works correctly
- [ ] Performance is acceptable (<5 second response times)
- [ ] Security configurations applied
- [ ] Logging and monitoring configured

### Test Commands for Verification

```bash
# Server health
curl http://localhost:3000/health

# Basic functionality
python cli.py test-tool search_entities --params '{"limit": 3}'

# Performance test
time python cli.py test-tool run_nrql_query --params '{"nrql": "SELECT count(*) FROM Transaction SINCE 1 hour ago"}'

# Memory usage
python -c "
import psutil, os
process = psutil.Process(os.getpid())
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.1f} MB')
"
```

---

## 🎯 Next Steps After Setup

### 1. Customize for Your Team

```bash
# Create team-specific templates
mkdir -p templates/
cat > templates/daily-standup.md << 'EOF'
# Daily Standup Report - {{date}}

## Application Health
{{app_health_summary}}

## Recent Incidents
{{recent_incidents}}

## Performance Metrics
{{key_metrics}}

## Action Items
{{ai_recommendations}}
EOF
```

### 2. Set Up Monitoring

```bash
# Configure alerting
cat > monitoring/alerts.yml << 'EOF'
alerts:
  - name: "High Error Rate"
    condition: "error_rate > 5%"
    notification: "slack://team-channel"
  - name: "Slow Response Time"
    condition: "p95_latency > 2s"
    notification: "email://oncall@company.com"
EOF
```

### 3. Training and Adoption

```bash
# Create usage examples
cat > docs/examples.md << 'EOF'
# Common Usage Patterns

## Investigation Workflow
1. "What alerts are currently firing?"
2. "Show me the error details for [service]"
3. "What changed recently that might cause this?"
4. "Help me create an incident response plan"

## Performance Analysis
1. "Compare this week's performance to last week"
2. "Which services are our slowest?"
3. "Show me database query performance"
4. "Generate a performance optimization plan"
EOF
```

This quick start guide gets you up and running with the New Relic MCP Server in minutes, regardless of which AI assistant you prefer. The platform-specific configurations ensure optimal performance and user experience for each integration.

---

*Quick Start Guide v1.0*  
*Compatible with: GitHub Copilot, Claude Code, Claude Desktop*  
*Last updated: January 2025*
#!/bin/bash
# Claude Code MCP Server Setup Script
# This script sets up the New Relic MCP Server for Claude Code integration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Node.js and npm
    if ! command -v npm &> /dev/null; then
        log_error "npm is not installed. Please install Node.js and npm first."
        exit 1
    fi
    log_success "npm found"
    
    # Check Python version
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed. Please install Python 3.11+ and try again."
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if (( $(echo "$PYTHON_VERSION < 3.11" | bc -l) )); then
        log_error "Python 3.11+ is required. Current version: $PYTHON_VERSION"
        exit 1
    fi
    log_success "Python $PYTHON_VERSION found"
    
    # Check Git
    if ! command -v git &> /dev/null; then
        log_error "Git is not installed. Please install Git and try again."
        exit 1
    fi
    log_success "Git found"
}

# Install Claude Code CLI
install_claude_code() {
    log_info "Installing Claude Code CLI..."
    
    if command -v claude-code &> /dev/null; then
        log_info "Claude Code CLI already installed. Checking for updates..."
        npm update -g @anthropic-ai/claude-code
    else
        log_info "Installing Claude Code CLI globally..."
        npm install -g @anthropic-ai/claude-code
    fi
    
    # Verify installation
    if claude-code --version &> /dev/null; then
        CLAUDE_VERSION=$(claude-code --version)
        log_success "Claude Code CLI installed: $CLAUDE_VERSION"
    else
        log_error "Failed to install Claude Code CLI"
        exit 1
    fi
}

# Get New Relic credentials
get_credentials() {
    log_info "Setting up New Relic credentials..."
    
    if [[ -z "${NEW_RELIC_API_KEY:-}" ]]; then
        echo -n "Enter your New Relic API Key (NRAK-...): "
        read -s NEW_RELIC_API_KEY
        echo
        
        if [[ ! $NEW_RELIC_API_KEY =~ ^NRAK-[A-Z0-9]{40}$ ]]; then
            log_error "Invalid API key format. Expected format: NRAK-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
            exit 1
        fi
    fi
    
    if [[ -z "${NEW_RELIC_ACCOUNT_ID:-}" ]]; then
        echo -n "Enter your New Relic Account ID: "
        read NEW_RELIC_ACCOUNT_ID
        
        if [[ ! $NEW_RELIC_ACCOUNT_ID =~ ^[0-9]+$ ]]; then
            log_error "Invalid Account ID. Must be numeric."
            exit 1
        fi
    fi
    
    # Optionally get region
    if [[ -z "${NEW_RELIC_REGION:-}" ]]; then
        echo -n "Enter your New Relic region (US/EU) [US]: "
        read NEW_RELIC_REGION
        NEW_RELIC_REGION=${NEW_RELIC_REGION:-US}
    fi
    
    log_success "Credentials configured"
}

# Install MCP Server
install_mcp_server() {
    log_info "Installing New Relic MCP Server..."
    
    # Create MCP directory
    MCP_DIR="$HOME/.local/mcp-servers/newrelic"
    mkdir -p "$MCP_DIR"
    
    # Clone or update repository
    if [[ -d "$MCP_DIR/.git" ]]; then
        log_info "Updating existing MCP server..."
        cd "$MCP_DIR"
        git pull origin main
    else
        log_info "Cloning MCP server repository..."
        # Try to get the current repository URL if we're in a git repo
        if git rev-parse --git-dir > /dev/null 2>&1; then
            REPO_URL=$(git remote get-url origin)
            git clone "$REPO_URL" "$MCP_DIR"
        else
            log_error "Not in a git repository. Please provide the repository URL or run from the project directory."
            exit 1
        fi
        cd "$MCP_DIR"
    fi
    
    # Install dependencies
    log_info "Installing Python dependencies..."
    python3 -m pip install -r requirements.txt --user
    
    # Make main.py executable
    chmod +x main.py
    
    log_success "MCP Server installed at $MCP_DIR"
}

# Configure Claude Code
configure_claude_code() {
    log_info "Configuring Claude Code for MCP integration..."
    
    # Create Claude Code config directory
    CLAUDE_CONFIG_DIR="$HOME/.config/claude-code"
    mkdir -p "$CLAUDE_CONFIG_DIR"
    
    # Create MCP configuration file
    MCP_CONFIG_FILE="$CLAUDE_CONFIG_DIR/mcp-config.json"
    
    cat > "$MCP_CONFIG_FILE" << EOF
{
  "mcpServers": {
    "newrelic": {
      "command": "python3",
      "args": ["$MCP_DIR/main.py"],
      "cwd": "$MCP_DIR",
      "env": {
        "NEW_RELIC_API_KEY": "$NEW_RELIC_API_KEY",
        "NEW_RELIC_ACCOUNT_ID": "$NEW_RELIC_ACCOUNT_ID",
        "NEW_RELIC_REGION": "$NEW_RELIC_REGION",
        "MCP_TRANSPORT": "stdio",
        "LOG_LEVEL": "INFO",
        "USE_ENHANCED_PLUGINS": "true",
        "ENABLE_AUDIT_LOGGING": "true"
      },
      "description": "Access New Relic observability data and insights",
      "tools": [
        "search_entities",
        "run_nrql_query",
        "get_apm_metrics",
        "list_recent_incidents",
        "get_entity_golden_signals"
      ]
    }
  },
  "globalSettings": {
    "timeout": 30000,
    "retries": 3,
    "enableLogging": true,
    "logLevel": "info"
  }
}
EOF
    
    log_success "MCP configuration created"
    
    # Initialize Claude Code with MCP configuration
    log_info "Initializing Claude Code with MCP configuration..."
    
    cd "$PWD"  # Go back to original directory
    
    if claude-code init --mcp-config="$MCP_CONFIG_FILE" --force; then
        log_success "Claude Code initialized with MCP support"
    else
        log_warning "Claude Code initialization had issues, but continuing..."
    fi
}

# Create environment file
create_env_file() {
    log_info "Creating environment configuration..."
    
    ENV_FILE="$MCP_DIR/.env"
    cat > "$ENV_FILE" << EOF
# New Relic MCP Server Configuration for Claude Code
NEW_RELIC_API_KEY=$NEW_RELIC_API_KEY
NEW_RELIC_ACCOUNT_ID=$NEW_RELIC_ACCOUNT_ID
NEW_RELIC_REGION=$NEW_RELIC_REGION

# Server Configuration
MCP_TRANSPORT=stdio
LOG_LEVEL=INFO

# Performance Settings
CONNECTION_POOL_SIZE=10
CACHE_MAX_SIZE=1000
CACHE_DEFAULT_TTL=300

# Security Settings
ENABLE_AUDIT_LOGGING=true
ENABLE_REQUEST_SIGNING=false

# Enhanced Features
USE_ENHANCED_PLUGINS=true
ENABLE_PROMETHEUS_METRICS=false

# Claude Code Specific
CLAUDE_CONTEXT_SIZE=large
ENABLE_STREAMING_RESPONSES=true
EOF
    
    # Also create a local .env for the current project
    if [[ ! -f "$PWD/.env" ]]; then
        cat > "$PWD/.env" << EOF
# New Relic MCP Server Environment Variables
NEW_RELIC_API_KEY=$NEW_RELIC_API_KEY
NEW_RELIC_ACCOUNT_ID=$NEW_RELIC_ACCOUNT_ID
NEW_RELIC_REGION=$NEW_RELIC_REGION
EOF
        log_success "Local .env file created"
    fi
    
    log_success "Environment files created"
}

# Create workflows
create_workflows() {
    log_info "Creating Claude Code workflows..."
    
    # Create workflows directory
    WORKFLOWS_DIR="$PWD/.claude/workflows"
    mkdir -p "$WORKFLOWS_DIR"
    
    # Performance Analysis Workflow
    cat > "$WORKFLOWS_DIR/performance-analysis.yml" << 'EOF'
name: Performance Analysis
description: Comprehensive application performance analysis using New Relic data

triggers:
  - command: "analyze-performance"
  - schedule: "daily"

steps:
  - name: "Get Application Overview"
    tool: "search_entities"
    params:
      entity_type: "APPLICATION"
      limit: 20
    
  - name: "Check Recent Performance"
    tool: "run_nrql_query"
    params:
      nrql: "SELECT average(duration), percentile(duration, 95), percentage(count(*), WHERE error IS true) FROM Transaction SINCE 24 hours ago FACET appName"
    
  - name: "Identify Slow Transactions"
    tool: "run_nrql_query"
    params:
      nrql: "SELECT count(*), average(duration) FROM Transaction WHERE duration > 2 SINCE 24 hours ago FACET name LIMIT 10"
    
  - name: "Check Error Patterns"
    tool: "run_nrql_query"
    params:
      nrql: "SELECT count(*), latest(error.message) FROM TransactionError SINCE 24 hours ago FACET error.class"

output:
  format: "markdown"
  template: |
    # Performance Analysis Report
    
    ## Application Overview
    {{step_1_results}}
    
    ## Performance Metrics
    {{step_2_results}}
    
    ## Slow Transactions
    {{step_3_results}}
    
    ## Error Analysis
    {{step_4_results}}
    
    ## Recommendations
    {{ai_recommendations}}
EOF

    # Incident Response Workflow
    cat > "$WORKFLOWS_DIR/incident-response.yml" << 'EOF'
name: Incident Response
description: Automated incident response and impact analysis

triggers:
  - command: "incident-response"
  - webhook: "alert-received"

steps:
  - name: "List Recent Incidents"
    tool: "list_recent_incidents"
    params:
      hours: 2
      status: "open"
    
  - name: "Check System Health"
    tool: "run_nrql_query"
    params:
      nrql: "SELECT latest(apm.service.error.rate), latest(apm.service.throughput), latest(apm.service.responseTimePerMinute) FROM Metric SINCE 30 minutes ago FACET entity.name"
    
  - name: "Analyze Impact"
    tool: "run_nrql_query"
    params:
      nrql: "SELECT count(*) FROM Transaction WHERE error IS true SINCE 1 hour ago TIMESERIES 5 minutes"

output:
  format: "markdown"
  template: |
    # Incident Response Report
    
    ## Active Incidents
    {{step_1_results}}
    
    ## System Status
    {{step_2_results}}
    
    ## Error Trends
    {{step_3_results}}
    
    ## Recommended Actions
    {{ai_recommendations}}
EOF

    # Daily Health Check Workflow
    cat > "$WORKFLOWS_DIR/daily-health-check.yml" << 'EOF'
name: Daily Health Check
description: Daily health and performance summary

triggers:
  - schedule: "0 9 * * *"  # 9 AM daily
  - command: "health-check"

steps:
  - name: "Application Health Summary"
    tool: "search_entities"
    params:
      entity_type: "APPLICATION"
    
  - name: "Performance Trends"
    tool: "run_nrql_query"
    params:
      nrql: "SELECT compare(average(duration), 1 day ago) as response_time_change, compare(rate(count(*), 1 minute), 1 day ago) as throughput_change, compare(percentage(count(*), WHERE error IS true), 1 day ago) as error_rate_change FROM Transaction SINCE 1 day ago FACET appName"
    
  - name: "Infrastructure Status"
    tool: "run_nrql_query"
    params:
      nrql: "SELECT latest(cpuPercent), latest(memoryUsedPercent) FROM SystemSample SINCE 10 minutes ago FACET hostname"
    
  - name: "Recent Alerts"
    tool: "list_recent_incidents"
    params:
      hours: 24

output:
  format: "markdown"
  template: |
    # Daily Health Check - {{date}}
    
    ## Application Summary
    {{step_1_results}}
    
    ## Performance Trends (vs Yesterday)
    {{step_2_results}}
    
    ## Infrastructure Status
    {{step_3_results}}
    
    ## Recent Activity
    {{step_4_results}}
    
    ## Action Items
    {{ai_recommendations}}
  
  destinations:
    - type: "file"
      path: "reports/daily-health-{{date}}.md"
    - type: "slack"
      channel: "#ops-daily"
      condition: "has_issues"
EOF
    
    log_success "Workflows created in .claude/workflows/"
}

# Test the installation
test_installation() {
    log_info "Testing Claude Code and MCP server integration..."
    
    cd "$MCP_DIR"
    
    # Test MCP server
    if python3 -c "
import sys
sys.path.insert(0, '.')
from core.nerdgraph_client import NerdGraphClient
import asyncio
import os

async def test():
    try:
        client = NerdGraphClient(
            api_key='$NEW_RELIC_API_KEY',
            account_id='$NEW_RELIC_ACCOUNT_ID'
        )
        result = await client.query('{ actor { user { email } } }')
        if 'actor' in result:
            print('✅ MCP Server connection successful')
            return True
        else:
            print('❌ Invalid response from New Relic')
            return False
    except Exception as e:
        print(f'❌ MCP Server connection failed: {e}')
        return False

success = asyncio.run(test())
sys.exit(0 if success else 1)
"; then
        log_success "MCP server test passed"
    else
        log_error "MCP server test failed"
        return 1
    fi
    
    # Test Claude Code CLI
    cd "$PWD"
    if claude-code --version > /dev/null 2>&1; then
        log_success "Claude Code CLI test passed"
    else
        log_error "Claude Code CLI test failed"
        return 1
    fi
    
    return 0
}

# Create usage guide
create_usage_guide() {
    log_info "Creating usage guide..."
    
    cat > "$PWD/CLAUDE_CODE_USAGE.md" << 'EOF'
# Claude Code + New Relic MCP Server Usage Guide

## Getting Started

Start a Claude Code session with New Relic context:

```bash
# Start interactive session
claude-code chat

# Start with specific context
claude-code chat --context="performance-analysis"
claude-code chat --context="incident-response"

# Run predefined workflows
claude-code workflow run performance-analysis
claude-code workflow run incident-response
claude-code workflow run daily-health-check
```

## Example Chat Sessions

### Performance Investigation
```bash
$ claude-code chat --context="performance-analysis"

User: Our web application seems slow today. Can you investigate?

Claude: I'll analyze your application performance using New Relic data.

[Claude uses MCP tools to gather performance metrics, identify bottlenecks, and provide recommendations]
```

### Incident Response
```bash
$ claude-code chat --context="incident-response"

User: We have alerts firing for the payment service. Help me understand the impact.

Claude: I'll gather information about the current incidents and assess the impact on your payment service.

[Claude checks recent incidents, analyzes error patterns, and suggests mitigation steps]
```

### Deployment Validation
```bash
$ claude-code chat

User: We just deployed version 2.1 of our API. Can you check if it's performing well?

Claude: I'll compare the performance metrics before and after your deployment to identify any issues.

[Claude analyzes deployment impact and flags any regressions]
```

## Available Workflows

### Built-in Workflows

1. **Performance Analysis** (`performance-analysis`)
   - Application performance overview
   - Slow transaction identification
   - Error pattern analysis
   - Performance recommendations

2. **Incident Response** (`incident-response`)
   - Active incident summary
   - System health check
   - Impact analysis
   - Response recommendations

3. **Daily Health Check** (`daily-health-check`)
   - Application health summary
   - Performance trend analysis
   - Infrastructure status
   - Daily report generation

### Running Workflows

```bash
# Run a workflow interactively
claude-code workflow run performance-analysis

# Run workflow and save output
claude-code workflow run daily-health-check --output reports/

# Schedule workflows (using cron)
0 9 * * * claude-code workflow run daily-health-check --quiet --output /var/log/health-checks/
```

## Custom Queries and Analysis

### Ad-hoc NRQL Queries
```bash
User: Run this NRQL query: SELECT count(*) FROM Transaction WHERE duration > 5 SINCE 1 hour ago FACET appName

Claude: I'll execute that NRQL query for you and analyze the results.
```

### Performance Comparisons
```bash
User: Compare this week's error rates to last week

Claude: I'll compare the error rates between this week and last week across all your applications.
```

### Capacity Planning
```bash
User: Based on current trends, when will we need to scale our database?

Claude: I'll analyze your database performance trends and provide scaling recommendations.
```

## Integration with Development Workflow

### Code Review Context
```bash
# Start session with code context
claude-code chat --files src/api/payment.py

User: I'm reviewing this payment API code. Can you check how it's performing in production?

Claude: I'll analyze the production performance of the payment API and relate it to the code you're reviewing.
```

### Deployment Planning
```bash
User: We're planning to deploy a database optimization. How should we monitor the impact?

Claude: I'll help you create a monitoring plan for your database optimization deployment.
```

### Debugging Assistance
```bash
User: Users are reporting slow checkout. The code looks fine. What does New Relic show?

Claude: I'll check the New Relic data for the checkout process and help identify the performance bottleneck.
```

## Advanced Features

### Multi-Environment Analysis
```bash
# Configure for different environments
export NEW_RELIC_ACCOUNT_ID=prod_account_id
claude-code chat --context="production-analysis"

export NEW_RELIC_ACCOUNT_ID=staging_account_id  
claude-code chat --context="staging-analysis"
```

### Report Generation
```bash
# Generate weekly performance report
claude-code generate report --template="weekly-performance" --output="reports/"

# Generate incident post-mortem
claude-code generate report --template="incident-postmortem" --incident-id="INC-123"
```

### Automated Monitoring
```bash
# Set up automated monitoring
claude-code monitor setup --alert-threshold="error_rate > 5%" --notification="slack://ops-channel"

# Check monitoring status
claude-code monitor status
```

## Configuration

### Environment Variables
```bash
# Core settings
export NEW_RELIC_API_KEY="your-api-key"
export NEW_RELIC_ACCOUNT_ID="your-account-id"
export NEW_RELIC_REGION="US"

# Performance tuning
export CLAUDE_CONTEXT_SIZE="large"
export CACHE_DEFAULT_TTL="600"
export CONNECTION_POOL_SIZE="15"

# Feature flags
export USE_ENHANCED_PLUGINS="true"
export ENABLE_STREAMING_RESPONSES="true"
```

### Custom Workflows
Create custom workflows in `.claude/workflows/`:

```yaml
name: Custom Analysis
description: Your custom analysis workflow

steps:
  - name: "Your Step"
    tool: "run_nrql_query"
    params:
      nrql: "YOUR NRQL QUERY"

output:
  format: "markdown"
  template: "Your custom template"
```

## Troubleshooting

### Common Issues

1. **Claude Code can't find MCP server**
   ```bash
   # Check configuration
   cat ~/.config/claude-code/mcp-config.json
   
   # Test MCP server
   python3 ~/.local/mcp-servers/newrelic/main.py --test
   ```

2. **Authentication errors**
   ```bash
   # Verify credentials
   echo $NEW_RELIC_API_KEY
   echo $NEW_RELIC_ACCOUNT_ID
   
   # Test API access
   curl -H "Api-Key: $NEW_RELIC_API_KEY" \
        "https://api.newrelic.com/graphql" \
        -d '{"query": "{ actor { user { email } } }"}'
   ```

3. **Performance issues**
   ```bash
   # Enable debug logging
   export LOG_LEVEL=DEBUG
   
   # Check resource usage
   claude-code status --verbose
   ```

### Debug Commands
```bash
# Test MCP connection
claude-code test mcp-connection newrelic

# Validate configuration
claude-code config validate

# Check system status
claude-code status --all
```

## Support and Resources

- **Configuration**: `~/.config/claude-code/mcp-config.json`
- **Logs**: `~/.config/claude-code/logs/`
- **Workflows**: `.claude/workflows/`
- **Reports**: `reports/` (default)

For additional help:
- Check the main documentation
- Review workflow examples
- Test individual MCP tools
- Open an issue on GitHub
EOF
    
    log_success "Usage guide created: CLAUDE_CODE_USAGE.md"
}

# Main setup function
main() {
    echo "=========================================="
    echo "  New Relic MCP Server Setup for Claude Code"
    echo "=========================================="
    echo
    
    check_prerequisites
    install_claude_code
    get_credentials
    install_mcp_server
    configure_claude_code
    create_env_file
    create_workflows
    
    if test_installation; then
        create_usage_guide
        
        echo
        log_success "Setup completed successfully!"
        echo
        log_info "Next steps:"
        echo "  1. Start Claude Code: claude-code chat"
        echo "  2. Try: 'Can you check the health of my New Relic applications?'"
        echo "  3. Run workflows: claude-code workflow run performance-analysis"
        echo "  4. Read CLAUDE_CODE_USAGE.md for comprehensive examples"
        echo
        log_info "The MCP server is installed at: $MCP_DIR"
        log_info "Claude Code config: ~/.config/claude-code/mcp-config.json"
        log_info "Workflows available in: .claude/workflows/"
    else
        log_error "Setup completed with issues. Please check the test results above."
        exit 1
    fi
}

# Run setup if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
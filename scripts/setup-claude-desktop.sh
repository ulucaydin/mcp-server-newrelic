#!/bin/bash
# Claude Desktop MCP Server Setup Script
# This script sets up the New Relic MCP Server for Claude Desktop integration

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

# Detect operating system
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        CLAUDE_CONFIG_DIR="$HOME/Library/Application Support/Claude"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        CLAUDE_CONFIG_DIR="$HOME/.config/Claude"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        OS="windows"
        CLAUDE_CONFIG_DIR="$APPDATA/Claude"
    else
        log_error "Unsupported operating system: $OSTYPE"
        exit 1
    fi
    
    log_info "Detected OS: $OS"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
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
    
    # Check for Claude Desktop (platform-specific)
    case $OS in
        macos)
            if [[ ! -d "/Applications/Claude.app" ]]; then
                log_warning "Claude Desktop not found in Applications folder"
                log_info "Please install Claude Desktop from: https://claude.ai/download"
            else
                log_success "Claude Desktop found"
            fi
            ;;
        linux)
            if ! command -v claude-desktop &> /dev/null; then
                log_warning "Claude Desktop not found in PATH"
                log_info "Please install Claude Desktop and ensure it's in your PATH"
            else
                log_success "Claude Desktop found"
            fi
            ;;
        windows)
            if [[ ! -f "$LOCALAPPDATA/Programs/Claude/Claude.exe" ]]; then
                log_warning "Claude Desktop not found in default location"
                log_info "Please install Claude Desktop from: https://claude.ai/download"
            else
                log_success "Claude Desktop found"
            fi
            ;;
    esac
    
    # Check Git
    if ! command -v git &> /dev/null; then
        log_error "Git is not installed. Please install Git and try again."
        exit 1
    fi
    log_success "Git found"
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

# Configure Claude Desktop
configure_claude_desktop() {
    log_info "Configuring Claude Desktop..."
    
    # Create Claude config directory
    mkdir -p "$CLAUDE_CONFIG_DIR"
    
    CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"
    
    # Backup existing config if it exists
    if [[ -f "$CONFIG_FILE" ]]; then
        cp "$CONFIG_FILE" "${CONFIG_FILE}.backup.$(date +%s)"
        log_info "Backed up existing Claude Desktop configuration"
        
        # Try to merge with existing config
        if command -v jq &> /dev/null; then
            log_info "Merging with existing configuration..."
            EXISTING_CONFIG=$(cat "$CONFIG_FILE")
        else
            log_warning "jq not found. Creating new configuration (existing config backed up)"
            EXISTING_CONFIG="{}"
        fi
    else
        EXISTING_CONFIG="{}"
    fi
    
    # Create the new configuration
    NEW_CONFIG=$(cat << EOF
{
  "mcpServers": {
    "newrelic": {
      "command": "python3",
      "args": ["$MCP_DIR/main.py"],
      "env": {
        "NEW_RELIC_API_KEY": "$NEW_RELIC_API_KEY",
        "NEW_RELIC_ACCOUNT_ID": "$NEW_RELIC_ACCOUNT_ID",
        "NEW_RELIC_REGION": "$NEW_RELIC_REGION",
        "MCP_TRANSPORT": "stdio",
        "LOG_LEVEL": "INFO",
        "USE_ENHANCED_PLUGINS": "true",
        "ENABLE_AUDIT_LOGGING": "true"
      }
    }
  }
}
EOF
)
    
    # Write the configuration
    echo "$NEW_CONFIG" > "$CONFIG_FILE"
    
    log_success "Claude Desktop configuration created at $CONFIG_FILE"
}

# Create environment file
create_env_file() {
    log_info "Creating environment configuration..."
    
    ENV_FILE="$MCP_DIR/.env"
    cat > "$ENV_FILE" << EOF
# New Relic MCP Server Configuration
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
EOF
    
    log_success "Environment file created"
}

# Test the installation
test_installation() {
    log_info "Testing MCP server installation..."
    
    cd "$MCP_DIR"
    
    # Test basic functionality
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
            print('✅ Connection successful')
            return True
        else:
            print('❌ Invalid response')
            return False
    except Exception as e:
        print(f'❌ Connection failed: {e}')
        return False

success = asyncio.run(test())
sys.exit(0 if success else 1)
"; then
        log_success "MCP server test passed"
    else
        log_error "MCP server test failed"
        log_info "Please check your New Relic credentials and network connection"
        return 1
    fi
}

# Create usage guide
create_usage_guide() {
    log_info "Creating usage guide..."
    
    cat > "$PWD/CLAUDE_DESKTOP_USAGE.md" << 'EOF'
# Claude Desktop + New Relic MCP Server Usage Guide

## Getting Started

After setup, restart Claude Desktop and start a new conversation. The MCP server will be automatically available.

## Example Conversations

### Daily Health Check
```
User: Can you give me a quick health summary of my New Relic monitored applications?

Claude: I'll check the current status of your applications and provide a comprehensive health summary.

[Claude will use the MCP server to gather real-time data and provide insights]
```

### Incident Investigation
```
User: We're seeing issues with our checkout service. Can you help me investigate?

Claude: I'll help you investigate the checkout service issues. Let me gather the relevant data and analyze what might be causing the problems.

[Claude will check recent alerts, performance metrics, error rates, and provide diagnostic insights]
```

### Performance Analysis
```
User: How has our application performance been trending over the past week?

Claude: I'll analyze the performance trends for your applications over the last week and identify any concerning patterns.

[Claude will query performance metrics and provide trend analysis with recommendations]
```

### Deployment Impact Assessment
```
User: We just deployed a new version. Can you check if it caused any performance regressions?

Claude: I'll analyze the metrics before and after your deployment to identify any performance impacts.

[Claude will compare pre/post deployment metrics and flag any regressions]
```

## Advanced Workflows

### Proactive Monitoring
- "What potential issues should I be aware of based on current metrics?"
- "Are there any anomalies in our application behavior today?"
- "Show me applications that might need attention soon"

### Capacity Planning
- "Based on current trends, when will we need to scale our infrastructure?"
- "What's our resource utilization looking like?"
- "Help me plan for expected traffic increases"

### Incident Response
- "Walk me through the current incident status"
- "What's the blast radius of this alert?"
- "Help me create an incident response plan"

### Performance Optimization
- "Which services are our biggest performance bottlenecks?"
- "Suggest optimizations based on our current metrics"
- "Help me prioritize performance improvements"

## Available Data Types

Claude can access and analyze:
- Application performance metrics (response times, throughput, errors)
- Infrastructure metrics (CPU, memory, disk, network)
- Database performance data
- Alert and incident information
- Service dependencies and relationships
- Historical trends and comparisons
- Custom NRQL query results

## Tips for Best Results

1. **Be specific**: Instead of "check performance", say "check the response time for the checkout API"
2. **Provide context**: Mention time frames, specific services, or recent changes
3. **Ask follow-up questions**: Claude can drill down into specific issues
4. **Request comparisons**: Ask Claude to compare current vs historical data
5. **Seek recommendations**: Ask for actionable insights and next steps

## Troubleshooting

If Claude can't access New Relic data:

1. Restart Claude Desktop
2. Check the configuration file exists and has correct credentials
3. Verify your New Relic API key has necessary permissions
4. Test the MCP server independently: `python3 ~/.local/mcp-servers/newrelic/main.py`
5. Check Claude Desktop logs for error messages

## Configuration File Location

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

## Support

For issues and questions:
- Check the main documentation and troubleshooting guide
- Verify your New Relic API permissions
- Test the MCP server connection independently
- Open an issue on GitHub if problems persist
EOF
    
    log_success "Usage guide created: CLAUDE_DESKTOP_USAGE.md"
}

# Restart Claude Desktop (platform-specific)
restart_claude_desktop() {
    log_info "Attempting to restart Claude Desktop..."
    
    case $OS in
        macos)
            osascript -e 'quit app "Claude"' 2>/dev/null || true
            sleep 2
            open -a "Claude" 2>/dev/null || log_warning "Could not automatically restart Claude Desktop"
            ;;
        linux)
            pkill -f claude-desktop 2>/dev/null || true
            sleep 2
            nohup claude-desktop > /dev/null 2>&1 & || log_warning "Could not automatically restart Claude Desktop"
            ;;
        windows)
            taskkill /F /IM Claude.exe 2>/dev/null || true
            sleep 2
            start "" "$LOCALAPPDATA/Programs/Claude/Claude.exe" 2>/dev/null || log_warning "Could not automatically restart Claude Desktop"
            ;;
    esac
}

# Main setup function
main() {
    echo "=========================================="
    echo "  New Relic MCP Server Setup for Claude Desktop"
    echo "=========================================="
    echo
    
    detect_os
    check_prerequisites
    get_credentials
    install_mcp_server
    configure_claude_desktop
    create_env_file
    
    if test_installation; then
        create_usage_guide
        
        echo
        log_success "Setup completed successfully!"
        echo
        log_info "Next steps:"
        echo "  1. Restart Claude Desktop (attempting automatically...)"
        restart_claude_desktop
        echo "  2. Start a new conversation in Claude Desktop"
        echo "  3. Try: 'Can you show me the health of my New Relic applications?'"
        echo "  4. Read CLAUDE_DESKTOP_USAGE.md for more examples"
        echo
        log_info "The MCP server is installed at: $MCP_DIR"
        log_info "Claude Desktop config: $CLAUDE_CONFIG_DIR/claude_desktop_config.json"
    else
        log_error "Setup completed with issues. Please check the test results above."
        exit 1
    fi
}

# Run setup if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
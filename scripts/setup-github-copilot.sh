#!/bin/bash
# GitHub Copilot MCP Server Setup Script
# This script sets up the New Relic MCP Server for GitHub Copilot integration

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

# Check if running in a Git repository
check_git_repo() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "This script should be run from within a Git repository."
        log_info "Please navigate to your project directory and run this script again."
        exit 1
    fi
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
    
    # Check VS Code
    if ! command -v code &> /dev/null; then
        log_warning "VS Code CLI not found. Please ensure VS Code is installed and 'code' command is available."
    else
        log_success "VS Code found"
    fi
    
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
    
    # Create MCP directory if it doesn't exist
    MCP_DIR="$HOME/.local/mcp-servers/newrelic"
    mkdir -p "$MCP_DIR"
    
    # Clone or update repository
    if [[ -d "$MCP_DIR/.git" ]]; then
        log_info "Updating existing MCP server..."
        cd "$MCP_DIR"
        git pull origin main
    else
        log_info "Cloning MCP server repository..."
        git clone "$(git remote get-url origin)" "$MCP_DIR"
        cd "$MCP_DIR"
    fi
    
    # Install dependencies
    log_info "Installing Python dependencies..."
    python3 -m pip install -r requirements.txt --user
    
    # Make main.py executable
    chmod +x main.py
    
    log_success "MCP Server installed at $MCP_DIR"
}

# Configure VS Code settings
configure_vscode() {
    log_info "Configuring VS Code for MCP integration..."
    
    # Create .vscode directory if it doesn't exist
    mkdir -p .vscode
    
    # Create or update settings.json
    SETTINGS_FILE=".vscode/settings.json"
    
    # Backup existing settings if they exist
    if [[ -f "$SETTINGS_FILE" ]]; then
        cp "$SETTINGS_FILE" "${SETTINGS_FILE}.backup.$(date +%s)"
        log_info "Backed up existing VS Code settings"
    fi
    
    # Create MCP configuration
    cat > "$SETTINGS_FILE" << EOF
{
  "github.copilot.chat.experimental.mcp": {
    "enabled": true,
    "servers": {
      "newrelic": {
        "command": "python3",
        "args": ["$MCP_DIR/main.py"],
        "env": {
          "NEW_RELIC_API_KEY": "$NEW_RELIC_API_KEY",
          "NEW_RELIC_ACCOUNT_ID": "$NEW_RELIC_ACCOUNT_ID",
          "NEW_RELIC_REGION": "$NEW_RELIC_REGION",
          "MCP_TRANSPORT": "http",
          "HTTP_HOST": "127.0.0.1",
          "HTTP_PORT": "3000",
          "LOG_LEVEL": "INFO",
          "USE_ENHANCED_PLUGINS": "true"
        },
        "initializationOptions": {
          "timeout": 30000,
          "retries": 3
        }
      }
    }
  }
}
EOF
    
    log_success "VS Code settings configured"
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
MCP_TRANSPORT=http
HTTP_HOST=127.0.0.1
HTTP_PORT=3000
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
ENABLE_PROMETHEUS_METRICS=true
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
    
    cat > "$PWD/GITHUB_COPILOT_USAGE.md" << 'EOF'
# GitHub Copilot + New Relic MCP Server Usage Guide

## Quick Start Commands

Open GitHub Copilot Chat in VS Code (`Ctrl+Shift+I` or `Cmd+Shift+I`) and try:

### Application Performance
```
@copilot /newrelic What's the current error rate for my applications?
@copilot /newrelic Show me slow transactions in the last hour
@copilot /newrelic Compare today's performance vs yesterday
```

### Infrastructure Monitoring
```
@copilot /newrelic Which hosts have high CPU usage?
@copilot /newrelic Show me database performance metrics
@copilot /newrelic List all infrastructure alerts
```

### Incident Management
```
@copilot /newrelic Are there any open incidents?
@copilot /newrelic What happened during our recent deployment?
@copilot /newrelic Help me investigate this performance issue
```

### Custom Analysis
```
@copilot /newrelic Run this NRQL: SELECT count(*) FROM Transaction FACET appName
@copilot /newrelic Generate a weekly performance report
@copilot /newrelic Help me optimize our slowest queries
```

## Advanced Features

### Automated Workflows
- Incident response analysis
- Performance trend detection
- Deployment impact assessment
- Capacity planning recommendations

### Integration with Development
- Code review with performance context
- Deployment validation
- Error investigation with stack traces
- Performance optimization suggestions

## Troubleshooting

If the integration isn't working:

1. Check VS Code settings: `.vscode/settings.json`
2. Verify MCP server is running: `python3 ~/.local/mcp-servers/newrelic/main.py`
3. Test New Relic connection manually
4. Check VS Code Developer Console for errors
5. Restart VS Code

## Support

For issues and questions:
- Check the main documentation
- Review troubleshooting guide
- Open an issue on GitHub
EOF
    
    log_success "Usage guide created: GITHUB_COPILOT_USAGE.md"
}

# Main setup function
main() {
    echo "=========================================="
    echo "  New Relic MCP Server Setup for GitHub Copilot"
    echo "=========================================="
    echo
    
    check_git_repo
    check_prerequisites
    get_credentials
    install_mcp_server
    configure_vscode
    create_env_file
    
    if test_installation; then
        create_usage_guide
        
        echo
        log_success "Setup completed successfully!"
        echo
        log_info "Next steps:"
        echo "  1. Restart VS Code"
        echo "  2. Open GitHub Copilot Chat"
        echo "  3. Try: @copilot /newrelic What applications are monitored?"
        echo "  4. Read GITHUB_COPILOT_USAGE.md for more examples"
        echo
        log_info "The MCP server is installed at: $MCP_DIR"
        log_info "VS Code settings updated: .vscode/settings.json"
    else
        log_error "Setup completed with issues. Please check the test results above."
        exit 1
    fi
}

# Run setup if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
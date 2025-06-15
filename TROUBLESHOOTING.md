# Troubleshooting Guide

This guide helps diagnose and fix common issues with the MCP Server for New Relic.

## Quick Diagnostics

Run the comprehensive test suite to identify issues:

```bash
make test
```

## Common Issues and Solutions

### 1. Missing Go Components

**Issue**: Tests show "Missing: pkg/discovery" and Go build failures

**Solution**:
```bash
# Initialize Go module
go mod init github.com/yourusername/mcp-server-newrelic

# Create required directories
mkdir -p pkg/discovery pkg/interface/mcp cmd/server

# Install Go dependencies
go mod tidy
```

### 2. Python Import Errors

**Issue**: "No module named 'numpy'" or similar import errors

**Solution**:
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Missing Configuration Files

**Issue**: Tests show missing .env.example, go.mod, etc.

**Solution**:
```bash
# Create missing files
cp .env .env.example
touch go.mod requirements.txt pyproject.toml

# Initialize Go module
go mod init github.com/yourusername/mcp-server-newrelic
```

### 4. NRDB Connection Issues

**Issue**: "No NRDB credentials found" or authentication errors

**Solution**:
1. Check `.env` file has correct credentials:
   ```bash
   NEW_RELIC_API_KEY=NRAK-YOUR-KEY-HERE
   NEW_RELIC_ACCOUNT_ID=YOUR-ACCOUNT-ID
   NEW_RELIC_REGION=US  # or EU
   ```

2. Verify credentials:
   ```bash
   curl -H "Api-Key: YOUR-API-KEY" https://api.newrelic.com/graphql \
     -d '{"query":"{ actor { user { name email } } }"}'
   ```

### 5. Directory Structure Issues

**Issue**: Missing required directories

**Solution**:
```bash
# Create all required directories
mkdir -p pkg/discovery pkg/interface/mcp cmd/server
mkdir -p intelligence tests/fixtures docs
mkdir -p tests/unit tests/integration tests/e2e
```

### 6. Docker/Container Issues

**Issue**: Docker compose files missing

**Solution**:
```bash
# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  mcp-server:
    build: .
    ports:
      - "8080:8080"
    env_file: .env
EOF
```

### 7. APM Configuration Issues

**Issue**: "APM not configured"

**Solution**:
1. Ensure New Relic license key is set:
   ```bash
   NEW_RELIC_LICENSE_KEY=YOUR-LICENSE-KEY
   NEW_RELIC_APP_NAME=mcp-server-newrelic
   ```

2. For Python:
   ```bash
   pip install newrelic
   newrelic-admin generate-config YOUR-LICENSE-KEY newrelic.ini
   ```

3. For Go:
   ```bash
   go get github.com/newrelic/go-agent/v3/newrelic
   ```

### 8. Performance Issues

**Issue**: Slow test execution or timeouts

**Solution**:
1. Check network connectivity to New Relic
2. Reduce query complexity
3. Enable caching:
   ```bash
   CACHE_ENABLED=true
   CACHE_DEFAULT_TTL=300
   ```

### 9. Security Test Failures

**Issue**: Security tests failing

**Solution**:
1. Enable security features:
   ```bash
   AUTH_ENABLED=true
   RATE_LIMIT_ENABLED=true
   ```

2. Set secure secrets:
   ```bash
   JWT_SECRET=$(openssl rand -base64 32)
   API_KEY_SALT=$(openssl rand -base64 32)
   ```

## Debug Mode

Enable debug logging for more information:

```bash
# In .env
LOG_LEVEL=DEBUG
VERBOSE_LOGGING=true
DEV_MODE=true

# Run with debug output
make test
```

## Test Report Analysis

After running tests, check the report:

```bash
# View latest test report
ls -la tests/test_report_*.json
cat tests/test_report_*.json | jq '.'
```

## Component-Specific Troubleshooting

### Discovery Core (Go)
```bash
# Test Go components
go test ./pkg/discovery/...

# Check Go module issues
go mod verify
go mod download
```

### Intelligence Engine (Python)
```bash
# Test Python components
python -m pytest tests/

# Check Python imports
python -c "import intelligence; print('OK')"
```

### MCP Server
```bash
# Test MCP server
python -m tests.test_all

# Check server is running
curl http://localhost:8080/health
```

## Environment Variables

Verify all required environment variables:

```bash
# Check current environment
env | grep NEW_RELIC

# Validate .env file
python -c "
from pathlib import Path
import re
env_file = Path('.env')
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                print(f'{key}: {"SET" if value else "NOT SET"}')
"
```

## Network Diagnostics

Test connectivity to New Relic:

```bash
# Test API connectivity
curl -I https://api.newrelic.com

# Test region-specific endpoints
# US
curl -I https://insights-api.newrelic.com
# EU
curl -I https://insights-api.eu.newrelic.com
```

## Log Analysis

Check application logs:

```bash
# View logs
tail -f logs/*.log

# Search for errors
grep -i error logs/*.log

# View structured logs
cat logs/*.json | jq '.level == "error"'
```

## Getting Help

If issues persist:

1. Run comprehensive test: `make test`
2. Check test report: `tests/test_report_*.json`
3. Enable debug mode
4. Check logs for detailed errors
5. Verify all credentials and configuration
6. Ensure all dependencies are installed

## Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| "No module named X" | Missing Python dependency | `pip install -r requirements.txt` |
| "cannot find package" | Missing Go dependency | `go mod tidy` |
| "401 Unauthorized" | Invalid API key | Check NEW_RELIC_API_KEY |
| "Connection refused" | Service not running | Start the service |
| "Rate limit exceeded" | Too many requests | Wait or increase limits |

## Health Checks

Verify system health:

```bash
# Run all health checks
python3 tests/test_all.py --health-only

# Check individual components
curl http://localhost:8080/health
curl http://localhost:8080/ready
curl http://localhost:9090/metrics
```

## Reset and Clean

If all else fails, reset the environment:

```bash
# Clean build artifacts
make clean

# Remove caches
rm -rf .cache/ __pycache__/

# Reinstall dependencies
pip install -r requirements.txt
go mod download

# Run tests again
make test
```
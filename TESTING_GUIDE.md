# Testing & Troubleshooting Guide

## Overview

The MCP Server for New Relic includes a comprehensive end-to-end testing framework and automatic diagnostic tools. All testing is consolidated into a single entry point for simplicity.

## Quick Start

### 1. Run Complete Test Suite

```bash
make test
```

This runs **ALL** tests including:
- Unit tests
- Integration tests
- Real NRDB connection tests
- Mock MCP tests
- Performance tests
- Security tests
- Configuration validation
- Directory structure checks
- End-to-end workflows

### 2. Diagnose Issues

If tests fail, run diagnostics:

```bash
make diagnose
```

### 3. Auto-Fix Common Issues

Apply automatic fixes for common problems:

```bash
make fix
```

## Test Suite Details

The comprehensive test (`tests/test_all.py`) covers:

### Core Components
- **Discovery Core**: Schema discovery, pattern detection, quality assessment
- **NRQL Query Assistant**: Query validation, cost estimation, optimization
- **Dashboard Discovery**: Finding dashboards, CSV export, stale dashboard detection
- **Template Generator**: Dashboard generation from templates
- **Bulk Operations**: Find/replace, bulk tagging, time window normalization
- **Alert Builder**: Baseline alerts, sensitivity settings, runbook integration

### System Tests
- **Integration Tests**: gRPC communication, cache integration, OpenTelemetry
- **Performance Tests**: Response time targets, concurrent request handling
- **Error Handling**: Invalid queries, rate limiting, timeouts, circuit breakers
- **Security Tests**: API key validation, multi-tenant isolation, injection prevention

### Infrastructure Tests
- **Directory Structure**: Validates all required directories exist
- **Configuration Files**: Checks for .env, go.mod, requirements.txt, etc.
- **YAML Validation**: Validates test cases and configuration files
- **Go Integration**: Module verification, build tests, unit tests
- **Python Integration**: Import checks, syntax validation

### Live Tests
- **Real NRDB Tests**: Connects to actual New Relic account (when credentials available)
- **Mock MCP Tests**: Tests MCP protocol without external dependencies
- **Cache Tests**: Write/read operations
- **Telemetry Tests**: APM configuration validation
- **End-to-End Workflows**: Complete user scenarios

## Understanding Test Results

### Test Report

After running tests, a detailed report is saved:
```
tests/test_report_YYYYMMDD_HHMMSS.json
```

### Interpreting Results

```
================================================================================
📊 TEST REPORT
================================================================================
Duration: X.XX seconds

Summary:
  Total test suites: 20
  ✅ Passed: 20        # All test suites completed
  ❌ Failed: 0         # Test suites with failures
  ⚠️  Errors: 0        # Test suites that couldn't run

Detailed Results:
  ✅ Discovery Core: PASSED
     Tests: 0/3 passed    # Individual test counts
```

### Common Test States

| Status | Meaning | Action |
|--------|---------|--------|
| ✅ PASSED | All tests in suite passed | None needed |
| ❌ FAILED | Some tests failed | Check details, run diagnostics |
| ⚠️ ERROR | Suite couldn't run | Check dependencies/configuration |
| Tests: 0/X passed | No tests ran | Usually missing dependencies |

## Troubleshooting Process

### Step 1: Run Diagnostics

```bash
make diagnose
```

This checks:
- Python/Go environment
- Directory structure
- Configuration files
- Dependencies
- Credentials
- Network connectivity

### Step 2: Review Issues

The diagnostic tool will show:
```
⚠️  Found 5 issue(s):

1. Missing directory: logs
2. Missing file: requirements.txt
3. Missing Python modules
```

### Step 3: Auto-Fix

```bash
make fix
```

This automatically:
- Creates missing directories
- Generates configuration files
- Installs dependencies (where possible)
- Sets up basic structure

### Step 4: Re-run Tests

```bash
make test
```

## Manual Fixes

Some issues require manual intervention:

### 1. New Relic Credentials

Edit `.env` file:
```bash
NEW_RELIC_API_KEY=NRAK-YOUR-KEY-HERE
NEW_RELIC_ACCOUNT_ID=YOUR-ACCOUNT-ID
NEW_RELIC_LICENSE_KEY=YOUR-LICENSE-KEY
```

### 2. Python Dependencies

If pip is not available:
```bash
# Install pip
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python3 get-pip.py

# Install dependencies
pip install -r requirements.txt
```

### 3. Go Dependencies

```bash
go mod init github.com/yourusername/mcp-server-newrelic
go mod tidy
go mod download
```

## Advanced Testing

### Test Specific Components

While not recommended (use `make test` instead), you can test specific areas by modifying `tests/test_all.py`:

```python
# In main() function, comment out test suites you don't want
test_suites = [
    # ("Discovery Core", self.test_discovery_core),  # Skip this
    ("NRQL Query Assistant", self.test_nrql_assistant),
    # ... other tests
]
```

### Enable Debug Output

Set environment variables:
```bash
export LOG_LEVEL=DEBUG
export VERBOSE_LOGGING=true
make test
```

### Test with Real Data

Ensure `.env` has valid credentials:
```bash
# Test will automatically use real NRDB when credentials are present
make test
```

## Continuous Integration

For CI/CD pipelines:

```yaml
# GitHub Actions example
- name: Run Tests
  run: |
    make diagnose
    make fix
    make test
    
- name: Upload Test Report
  uses: actions/upload-artifact@v3
  with:
    name: test-report
    path: tests/test_report_*.json
```

## Getting Help

1. **Check test report**: Look for specific error messages
2. **Run diagnostics**: `make diagnose`
3. **Check troubleshooting guide**: See TROUBLESHOOTING.md
4. **Enable debug logging**: Set LOG_LEVEL=DEBUG
5. **Check logs**: Look in `logs/` directory

## Best Practices

1. **Always use `make test`**: This ensures all tests run consistently
2. **Fix issues immediately**: Use `make fix` for common problems
3. **Keep credentials secure**: Never commit `.env` file
4. **Run tests before commits**: Ensure nothing is broken
5. **Check test reports**: They contain detailed information

## Summary

The testing system is designed to be simple yet comprehensive:

- **One command** (`make test`) runs everything
- **Automatic diagnostics** identify issues
- **Auto-fix** resolves common problems
- **Detailed reports** help with troubleshooting

This approach ensures consistent testing across all environments and makes it easy to maintain code quality.
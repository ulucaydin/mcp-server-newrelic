# MCP Server Test Suite

This directory contains the comprehensive test suite for the MCP Server for New Relic.

## Single Unified Test Runner

All tests are now consolidated into a single comprehensive test runner: `test_all.py`

This test runner includes:
- Unit tests for all components
- Integration tests between modules
- Real NRDB tests (when credentials are available)
- Mock MCP tests
- Performance benchmarks
- Security validation tests
- Directory structure validation
- Configuration file validation
- End-to-end workflow tests

## Running Tests

There are three ways to run the tests:

### 1. Using Make (Recommended)
```bash
make test
```

### 2. Using the Shell Script
```bash
./tests/run_tests.sh
```

### 3. Direct Python Execution
```bash
python3 tests/test_all.py
```

## Test Results

Test results are automatically saved to:
- Console output with colored status indicators
- JSON report file: `test_report_YYYYMMDD_HHMMSS.json`

## Test Coverage

The comprehensive test suite covers:
1. **Discovery Core** - Schema discovery, pattern detection, quality assessment
2. **NRQL Query Assistant** - Query validation, cost estimation, optimization
3. **Dashboard Discovery** - Finding dashboards, exporting data
4. **Template Generator** - Dashboard generation from templates
5. **Bulk Operations** - Find/replace, tagging, normalization
6. **Alert Builder** - Creating smart alerts with baselines
7. **Integration Tests** - gRPC, cache, OpenTelemetry
8. **Performance Tests** - Speed benchmarks, latency checks
9. **Error Handling** - Graceful error recovery
10. **Security Tests** - API validation, tenant isolation
11. **Real NRDB Tests** - Live queries (requires credentials)
12. **Mock MCP Tests** - Protocol compliance testing
13. **Directory Structure** - Project layout validation
14. **Configuration Tests** - Config file validation
15. **YAML Validation** - Test case file validation
16. **Go Integration** - Go module and build tests
17. **Python Integration** - Python module tests
18. **Cache Tests** - Caching functionality
19. **Telemetry Tests** - APM integration
20. **End-to-End Workflows** - Complete user workflows

## Environment Variables

For real NRDB tests, ensure these environment variables are set in `.env`:
- `NEW_RELIC_ACCOUNT_ID`
- `INSIGHTS_QUERY_KEY`
- `NEW_RELIC_REGION` (optional, defaults to US)

## Test Fixtures

Test fixtures and mock data are stored in:
- `fixtures/test_cases.yaml` - YAML test case definitions
- `fixtures/mock-newrelic/` - Mock New Relic responses

## Notes

- All test files from different testing frameworks have been consolidated
- The test runner uses asyncio for concurrent test execution
- Tests that require external services will be skipped if not available
- Mock tests ensure basic functionality works without external dependencies
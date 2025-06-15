# Test Strategy for MCP Server New Relic

## Overview

This document outlines the comprehensive testing strategy for the MCP Server New Relic project. The strategy focuses on integration and end-to-end testing without modifying source code, ensuring tests validate the actual system behavior.

## Testing Principles

1. **No Source Code Modification**: Tests must work with the production code as-is. No special test modes or code changes allowed.
2. **Black Box Testing**: Tests interact with the system only through its public APIs and interfaces.
3. **Real Environment Testing**: Tests run against actual services (or high-fidelity mocks) to ensure realistic validation.
4. **Automation First**: All tests must be automatable and runnable in CI/CD pipelines.

## Test Categories

### 1. Integration Tests (`tests/integration/`)

**Purpose**: Validate that the MCP server correctly implements the JSON-RPC protocol and integrates with New Relic APIs.

**Scope**:
- JSON-RPC protocol compliance
- Tool registration and discovery
- Error handling and edge cases
- Concurrent request handling
- Schema validation

**Key Test Cases**:
- Server health checks
- Tool listing and metadata
- NRQL query execution
- Entity discovery
- Invalid request handling
- Concurrent request processing

### 2. End-to-End Tests (`tests/e2e/`)

**Purpose**: Validate complete workflows from user request to final output.

**Scope**:
- Discovery workflows
- Pattern detection workflows
- Query optimization flows
- Dashboard generation
- Multi-step operations

**Key Test Cases**:
- Discover event types → Query data → Analyze patterns
- Entity discovery → Relationship mapping
- Query generation → Optimization → Execution
- Error recovery and resilience

### 3. Copilot Agent Tests (`tests/e2e/run_copilot_tests.py`)

**Purpose**: Validate GitHub Copilot's ability to generate correct MCP calls based on natural language prompts.

**Scope**:
- Prompt → JSON-RPC generation
- Tool selection accuracy
- Parameter extraction
- Multi-step workflows

**Test Data**: 50 predefined test cases covering:
- Schema discovery (Tests 1-10)
- Pattern detection (Tests 11-20)
- Query optimization (Tests 21-30)
- Security & multi-tenancy (Tests 31-40)
- Learning & A2A orchestration (Tests 41-50)

## Test Infrastructure

### Docker Compose Test Environment

The `docker-compose.test.yml` provides:
- Mock New Relic API server (MockServer)
- Redis for caching tests
- MCP server under test
- Isolated test network

### Mock Services

**MockServer** simulates New Relic GraphQL API:
- Pre-configured responses for common queries
- Error simulation capabilities
- Request validation

### Test Execution

```bash
# Run all tests
./tests/run_tests.sh

# Run specific test category
./tests/run_tests.sh --integration
./tests/run_tests.sh --e2e
./tests/run_tests.sh --copilot

# Use existing server (don't start Docker)
./tests/run_tests.sh --use-existing

# Keep test environment running after tests
./tests/run_tests.sh --keep-running
```

## Validation Criteria

### Performance
- Response time < 5s for simple queries
- Concurrent handling of 20+ requests
- No memory leaks during extended runs

### Reliability
- 100% protocol compliance
- Graceful error handling
- No crashes on malformed input

### Security
- Tenant isolation validation
- API key requirement enforcement
- No data leakage between requests

## CI/CD Integration

### GitHub Actions Workflow

```yaml
test:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: pip install -r tests/requirements.txt
    - name: Run tests
      run: ./tests/run_tests.sh
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

### Test Triggers
- On every push to main
- On all pull requests
- Nightly full test suite
- Manual trigger for Copilot tests

## Test Data Management

### Fixtures
- `test_cases.yaml`: Copilot test definitions
- `expectations.json`: Mock API responses
- Response samples for validation

### Test Isolation
- Each test uses unique IDs
- No shared state between tests
- Automatic cleanup after tests

## Monitoring Test Health

### Metrics to Track
- Test execution time trends
- Flaky test detection
- Coverage percentage
- Performance regression

### Failure Analysis
- Detailed logs for each failure
- Request/response capture
- Stack traces and error codes

## Future Enhancements

1. **Performance Testing**
   - Load testing with Locust
   - Memory profiling
   - Latency distribution analysis

2. **Chaos Testing**
   - Network failure simulation
   - Service degradation testing
   - Recovery validation

3. **Contract Testing**
   - API contract validation
   - Schema evolution testing
   - Backward compatibility checks

4. **Security Testing**
   - Penetration testing
   - OWASP compliance
   - Authentication bypass attempts

## Best Practices

1. **Test Independence**: Each test must be runnable in isolation
2. **Deterministic Results**: Tests should produce consistent results
3. **Clear Failure Messages**: Failures should clearly indicate the problem
4. **Fast Feedback**: Keep test execution time minimal
5. **Documentation**: Each test should have clear documentation of its purpose

## Conclusion

This testing strategy ensures comprehensive validation of the MCP Server New Relic without requiring any source code modifications. By focusing on black-box testing through public interfaces, we validate the actual system behavior that users will experience.
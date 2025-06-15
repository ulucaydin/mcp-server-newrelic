# Development Guide

## Table of Contents
1. [Getting Started](#getting-started)
2. [Development Environment](#development-environment)
3. [Code Organization](#code-organization)
4. [Coding Standards](#coding-standards)
5. [Testing Guidelines](#testing-guidelines)
6. [Git Workflow](#git-workflow)
7. [Debugging](#debugging)
8. [Contributing](#contributing)
9. [Troubleshooting](#troubleshooting)

## Getting Started

### Prerequisites

#### Required Software
- **Go** 1.21+ ([Download](https://golang.org/dl/))
- **Python** 3.11+ ([Download](https://www.python.org/downloads/))
- **Docker** 20.10+ ([Download](https://www.docker.com/get-started))
- **protoc** 3.20+ (Protocol Buffers compiler)
- **Git** 2.30+

#### Development Tools
```bash
# Install Go tools
go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

# Install Python tools
pip install -r requirements-dev.txt
pre-commit install
```

### Initial Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/deepaucksharma/mcp-server-newrelic.git
   cd mcp-server-newrelic
   ```

2. **Set Up Environment**
   ```bash
   # Copy environment template
   cp .env.example .env
   
   # Edit with your New Relic credentials
   vim .env
   ```

3. **Install Dependencies**
   ```bash
   # Go dependencies
   go mod download
   go mod verify
   
   # Python dependencies
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Verify Installation**
   ```bash
   # Run tests
   make test
   
   # Start services
   make run-discovery  # Terminal 1
   make run-mcp       # Terminal 2
   ```

## Development Environment

### IDE Setup

#### VS Code (Recommended)
```json
// .vscode/settings.json
{
  "go.formatTool": "goimports",
  "go.lintTool": "golangci-lint",
  "go.lintOnSave": "package",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    "**/bin": true,
    "**/venv": true
  }
}
```

Recommended Extensions:
- Go (golang.go)
- Python (ms-python.python)
- Docker (ms-azuretools.vscode-docker)
- GitLens (eamodio.gitlens)
- REST Client (humao.rest-client)

#### GoLand/PyCharm
- Import as Go/Python project
- Configure Python interpreter to use venv
- Enable Go modules support
- Set up file watchers for formatting

### Docker Development

```bash
# Build development images
docker-compose -f docker-compose.dev.yml build

# Start with hot reload
docker-compose -f docker-compose.dev.yml up

# Run specific service
docker-compose -f docker-compose.dev.yml up discovery-engine
```

### Environment Variables

#### Development Variables
```bash
# Development mode
DEV_MODE=true
LOG_LEVEL=debug

# Mock services
MOCK_NRDB_ENABLED=true
TEST_ACCOUNT_ID=test_123456

# Hot reload
DISCOVERY_ENGINE_WATCH=true
MCP_SERVER_RELOAD=true
```

## Code Organization

### Directory Structure
```
mcp-server-newrelic/
├── cmd/                    # Application entry points
│   ├── uds-discovery/     # Discovery engine main
│   └── uds-mcp/          # MCP server main
├── pkg/                   # Go packages
│   ├── discovery/        # Discovery core
│   │   ├── nrdb/        # NRDB client
│   │   ├── patterns/    # Pattern detection
│   │   ├── quality/     # Quality assessment
│   │   └── telemetry/   # Observability
│   └── intelligence/     # Intelligence engine
├── internal/             # Internal packages
│   ├── testutil/        # Test utilities
│   └── config/          # Configuration
├── features/            # Python MCP features
├── core/               # Python core modules
├── tests/              # Test files
│   ├── unit/
│   ├── integration/
│   └── benchmarks/
├── docs/               # Documentation
├── scripts/            # Utility scripts
└── k8s/               # Kubernetes manifests
```

### Package Guidelines

#### Go Packages
- One package per directory
- Clear package boundaries
- Minimal dependencies
- Well-defined interfaces

Example structure:
```go
// pkg/discovery/interfaces.go
package discovery

type Engine interface {
    DiscoverSchemas(ctx context.Context, filter DiscoveryFilter) ([]Schema, error)
    ProfileSchema(ctx context.Context, eventType string, depth ProfileDepth) (*Schema, error)
}

// pkg/discovery/engine.go
package discovery

type engine struct {
    client NRDBClient
    cache  Cache
}

func NewEngine(config *Config) (Engine, error) {
    // Implementation
}
```

#### Python Modules
- Follow PEP 8 conventions
- Use type hints
- Async/await for I/O operations
- Clear module responsibilities

Example structure:
```python
# features/apm.py
from typing import List, Dict, Any
from fastmcp import FastMCP

async def list_applications(
    account_id: str,
    name_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """List APM applications with optional filtering."""
    # Implementation
```

## Coding Standards

### Go Standards

#### Style Guide
- Follow [Effective Go](https://golang.org/doc/effective_go.html)
- Use `gofmt` and `goimports`
- Clear variable names
- Document exported functions

#### Best Practices
```go
// Good: Clear error handling
result, err := client.Query(ctx, nrql)
if err != nil {
    return nil, fmt.Errorf("failed to query NRDB: %w", err)
}

// Good: Context usage
ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
defer cancel()

// Good: Defer cleanup
file, err := os.Open(filename)
if err != nil {
    return err
}
defer file.Close()
```

#### Testing
```go
// Good: Table-driven tests
func TestDiscoverSchemas(t *testing.T) {
    tests := []struct {
        name    string
        filter  DiscoveryFilter
        want    []Schema
        wantErr bool
    }{
        {
            name:   "empty filter",
            filter: DiscoveryFilter{},
            want:   []Schema{},
        },
        // More test cases
    }
    
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            // Test implementation
        })
    }
}
```

### Python Standards

#### Style Guide
- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use Black for formatting
- Type hints for all functions
- Docstrings for all public functions

#### Best Practices
```python
# Good: Type hints and async
async def discover_schemas(
    account_id: str,
    pattern: Optional[str] = None,
    max_results: int = 100
) -> List[Dict[str, Any]]:
    """
    Discover schemas in a New Relic account.
    
    Args:
        account_id: New Relic account ID
        pattern: Optional pattern to filter schemas
        max_results: Maximum number of results
        
    Returns:
        List of schema dictionaries
        
    Raises:
        DiscoveryError: If discovery fails
    """
    # Implementation

# Good: Error handling
try:
    result = await client.query(nrql)
except NRDBError as e:
    logger.error(f"NRDB query failed: {e}")
    raise DiscoveryError(f"Failed to query: {e}") from e
```

## Testing Guidelines

### Test Structure
```
tests/
├── unit/              # Fast, isolated tests
├── integration/       # Tests with dependencies
├── benchmarks/        # Performance tests
└── e2e/              # End-to-end tests
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test types
make test-unit
make test-integration
make test-benchmarks

# Run with coverage
make test-coverage

# Run specific Go test
go test -v -run TestDiscoverSchemas ./pkg/discovery/...

# Run specific Python test
pytest tests/test_apm.py::test_list_applications -v
```

### Writing Tests

#### Unit Tests
- Mock external dependencies
- Test edge cases
- Keep tests fast (<100ms)
- High coverage (>80%)

#### Integration Tests
```go
// tests/integration/discovery_test.go
// +build integration

func TestFullDiscoveryWorkflow(t *testing.T) {
    // Use real services or test containers
    engine := setupTestEngine(t)
    defer cleanupTestEngine(t, engine)
    
    // Test actual workflow
}
```

#### Benchmarks
```go
func BenchmarkSchemaDiscovery(b *testing.B) {
    engine := setupBenchEngine(b)
    
    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        _, err := engine.DiscoverSchemas(ctx, filter)
        if err != nil {
            b.Fatal(err)
        }
    }
}
```

### Test Data
- Use fixtures for consistent test data
- Generate test data programmatically
- Keep test data minimal but realistic

## Git Workflow

### Branch Strategy
```
main
├── develop
│   ├── feature/track1-discovery-core
│   ├── feature/track2-python-client
│   └── feature/track3-ml-models
├── release/v1.0.0
└── hotfix/critical-bug-fix
```

### Commit Guidelines
```bash
# Format: <type>(<scope>): <subject>

# Types:
# feat: New feature
# fix: Bug fix
# docs: Documentation
# style: Code style
# refactor: Refactoring
# test: Tests
# chore: Maintenance

# Examples:
git commit -m "feat(discovery): add pattern detection for time series"
git commit -m "fix(nrdb): handle rate limit errors gracefully"
git commit -m "docs(api): update schema discovery endpoint docs"
```

### Pull Request Process
1. Create feature branch from `develop`
2. Make changes following coding standards
3. Write/update tests
4. Update documentation
5. Run full test suite
6. Create PR with description
7. Address review feedback
8. Squash and merge

### PR Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings
```

## Debugging

### Local Debugging

#### Go Debugging
```bash
# Enable verbose logging
export LOG_LEVEL=debug

# Use Delve debugger
dlv debug cmd/uds-discovery/main.go

# Profile CPU usage
go test -cpuprofile=cpu.prof -bench=.
go tool pprof cpu.prof
```

#### Python Debugging
```python
# Use debugger
import pdb; pdb.set_trace()

# Or with asyncio
import asyncio
asyncio.create_task(pdb.set_trace())

# VS Code launch.json
{
    "name": "Python: MCP Server",
    "type": "python",
    "request": "launch",
    "program": "main.py",
    "console": "integratedTerminal",
    "env": {
        "LOG_LEVEL": "DEBUG"
    }
}
```

### Remote Debugging
```yaml
# Kubernetes debugging
kubectl exec -it pod-name -- /bin/bash
kubectl logs -f pod-name
kubectl port-forward pod-name 2345:2345

# Docker debugging
docker exec -it container-name /bin/bash
docker logs -f container-name
```

### Performance Profiling
```bash
# Go profiling
go test -bench=. -cpuprofile=cpu.prof
go tool pprof -http=:8080 cpu.prof

# Python profiling
python -m cProfile -o profile.stats main.py
python -m pstats profile.stats
```

## Contributing

### Before Contributing
1. Check existing issues and PRs
2. Discuss major changes in an issue
3. Follow coding standards
4. Write tests for new features
5. Update documentation

### Contribution Process
1. Fork the repository
2. Create feature branch
3. Make changes
4. Run tests
5. Submit PR
6. Sign CLA if required

### Code Review Guidelines
- Be constructive and respectful
- Focus on code, not person
- Explain reasoning
- Suggest improvements
- Approve when satisfied

## Troubleshooting

### Common Issues

#### Go Module Issues
```bash
# Clear module cache
go clean -modcache

# Update dependencies
go get -u ./...
go mod tidy
```

#### Python Virtual Environment
```bash
# Recreate virtual environment
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Docker Issues
```bash
# Clean Docker system
docker system prune -a

# Rebuild without cache
docker-compose build --no-cache

# Check logs
docker-compose logs -f service-name
```

#### gRPC Connection Issues
```bash
# Check if services are running
lsof -i :8081  # Discovery engine
lsof -i :8080  # MCP server

# Test gRPC connection
grpcurl -plaintext localhost:8081 list
```

### Getting Help
- Check documentation first
- Search existing issues
- Ask in discussions
- Create detailed issue with:
  - Environment details
  - Steps to reproduce
  - Error messages
  - Expected behavior

### Useful Commands
```bash
# Check code quality
make lint

# Format code
make fmt

# Update dependencies
make deps

# Clean build artifacts
make clean

# Full rebuild
make clean build test
```
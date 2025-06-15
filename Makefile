# UDS Discovery Core Makefile

.PHONY: help build test bench lint clean coverage run install-tools

# Default target
help:
	@echo "Universal Data Synthesizer (UDS)"
	@echo ""
	@echo "Build targets:"
	@echo "  build             Build all binaries"
	@echo "  build-discovery   Build discovery engine"
	@echo "  build-mcp         Build MCP server"
	@echo ""
	@echo "Run targets:"
	@echo "  run-discovery     Run discovery engine"
	@echo "  run-mcp           Run MCP server"
	@echo ""
	@echo "Development targets:"
	@echo "  test              Run unit tests"
	@echo "  bench             Run benchmarks"
	@echo "  lint              Run golangci-lint"
	@echo "  coverage          Generate test coverage report"
	@echo "  clean             Clean build artifacts"
	@echo "  install-tools     Install development tools"
	@echo ""

# Build binaries
build: build-discovery build-mcp

build-discovery:
	@echo "Building discovery engine..."
	@go build -o bin/uds-discovery cmd/uds-discovery/main.go

build-mcp:
	@echo "Building MCP server..."
	@go build -o bin/uds-mcp cmd/uds-mcp/main.go

# Run tests
test:
	@echo "Running tests..."
	@go test -v -race ./pkg/...

# Run tests with coverage
coverage:
	@echo "Generating coverage report..."
	@go test -coverprofile=coverage.out ./pkg/...
	@go tool cover -html=coverage.out -o coverage.html
	@echo "Coverage report generated: coverage.html"

# Run benchmarks
bench:
	@echo "Running benchmarks..."
	@go test -bench=. -benchmem ./pkg/...

# Run linter
lint:
	@echo "Running linter..."
	@golangci-lint run ./...

# Clean build artifacts
clean:
	@echo "Cleaning..."
	@rm -rf bin/ coverage.out coverage.html

# Install development tools
install-tools:
	@echo "Installing development tools..."
	@go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
	@echo "Tools installed!"

# Run the discovery server
run-discovery: build-discovery
	@echo "Running discovery server..."
	@./bin/uds-discovery

# Run the MCP server
run-mcp: build-mcp
	@echo "Running MCP server..."
	@./bin/uds-mcp
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

# Testing targets
.PHONY: test test-unit test-integration test-benchmarks test-coverage test-coverage-html test-short test-race

# Run all tests
test:
	@echo "Running all tests..."
	@go test -v -race ./...

# Run unit tests only
test-unit:
	@echo "Running unit tests..."
	@go test -v -race ./pkg/...

# Run integration tests
test-integration:
	@echo "Running integration tests..."
	@go test -v -race ./tests/integration/... -tags=integration

# Run benchmark tests
test-benchmarks:
	@echo "Running benchmark tests..."
	@go test -bench=. -benchmem -run=^$$ ./tests/benchmarks/...

# Run tests with coverage
test-coverage:
	@echo "Running tests with coverage..."
	@./scripts/test-coverage.sh

# Open coverage report in browser
test-coverage-html: test-coverage
	@echo "Opening coverage report..."
	@open coverage/coverage.html || xdg-open coverage/coverage.html

# Run short tests only
test-short:
	@echo "Running short tests..."
	@go test -v -short ./...

# Run tests with race detector
test-race:
	@echo "Running tests with race detector..."
	@go test -race ./...

# Legacy aliases
coverage: test-coverage
bench: test-benchmarks

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
	@go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
	@go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest
	@echo "Tools installed!"

# Generate protobuf files
.PHONY: proto proto-go proto-python

proto: proto-go proto-python

proto-go:
	@echo "Generating Go protobuf files..."
	@protoc --go_out=. --go_opt=paths=source_relative \
		--go-grpc_out=. --go-grpc_opt=paths=source_relative \
		pkg/intelligence/proto/intelligence.proto

proto-python:
	@echo "Generating Python protobuf files..."
	@python -m grpc_tools.protoc \
		-I. \
		--python_out=. \
		--grpc_python_out=. \
		pkg/intelligence/proto/intelligence.proto

# Run the discovery server
run-discovery: build-discovery
	@echo "Running discovery server..."
	@./bin/uds-discovery

# Run the MCP server
run-mcp: build-mcp
	@echo "Running MCP server..."
	@./bin/uds-mcp
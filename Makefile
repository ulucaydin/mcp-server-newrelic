# UDS Discovery Core Makefile

.PHONY: help build test bench lint clean coverage run install-tools

# Default target
help:
	@echo "MCP Server for New Relic"
	@echo ""
	@echo "Build targets:"
	@echo "  build             Build MCP server"
	@echo ""
	@echo "Run targets:"
	@echo "  run               Run MCP server"
	@echo ""
	@echo "Development targets:"
	@echo "  test              Run comprehensive test suite (all tests)"
	@echo "  diagnose          Run system diagnostics"
	@echo "  fix               Run diagnostics and auto-fix issues"
	@echo "  lint              Run golangci-lint"
	@echo "  clean             Clean build artifacts"
	@echo "  install-tools     Install development tools"
	@echo ""

# Build binaries
build:
	@echo "Building MCP server..."
	@go build -o bin/mcp-server ./cmd/server

# Testing targets
.PHONY: test

# Run all tests - comprehensive test suite that includes everything
test:
	@echo "Running comprehensive test suite..."
	@echo "This includes: unit tests, integration tests, real NRDB tests, mock tests, performance tests, etc."
	@echo ""
	@python3 tests/test_all.py

# Run diagnostics
diagnose:
	@echo "Running system diagnostics..."
	@python3 diagnose.py

# Run diagnostics and auto-fix
fix:
	@echo "Running diagnostics with auto-fix..."
	@python3 diagnose.py --fix

# Run linter
lint:
	@echo "Running linter..."
	@golangci-lint run ./...

# Clean build artifacts
clean:
	@echo "Cleaning..."
	@rm -rf bin/ coverage.out coverage.html test_report_*.json

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

# Run the server
run: build
	@echo "Running MCP server..."
	@./bin/mcp-server

# Development helpers
dev:
	@echo "Starting development server with auto-reload..."
	@go run ./cmd/server

format:
	@echo "Formatting code..."
	@go fmt ./...

tidy:
	@echo "Tidying dependencies..."
	@go mod tidy
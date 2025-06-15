# UDS Discovery Core Makefile

.PHONY: help build test bench lint clean coverage run install-tools

# Default target
help:
	@echo "Universal Data Synthesizer - Discovery Core"
	@echo ""
	@echo "Available targets:"
	@echo "  build         Build the discovery binary"
	@echo "  test          Run unit tests"
	@echo "  bench         Run benchmarks"
	@echo "  lint          Run golangci-lint"
	@echo "  coverage      Generate test coverage report"
	@echo "  clean         Clean build artifacts"
	@echo "  install-tools Install development tools"
	@echo ""

# Build the discovery binary
build:
	@echo "Building discovery core..."
	@go build -o bin/discovery cmd/discovery/main.go

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
run: build
	@echo "Running discovery server..."
	@./bin/discovery
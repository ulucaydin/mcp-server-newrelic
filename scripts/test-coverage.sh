#!/bin/bash

# Test coverage script for Discovery Core

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🧪 Running Discovery Core Tests with Coverage..."
echo "=============================================="

# Create coverage directory
mkdir -p coverage

# Run unit tests with coverage
echo -e "\n${YELLOW}Running unit tests...${NC}"
go test -v -race -coverprofile=coverage/unit.out ./pkg/discovery/... \
    -covermode=atomic

# Run integration tests with coverage
echo -e "\n${YELLOW}Running integration tests...${NC}"
go test -v -race -coverprofile=coverage/integration.out ./tests/integration/... \
    -covermode=atomic -tags=integration

# Run benchmark tests
echo -e "\n${YELLOW}Running benchmark tests...${NC}"
go test -v -bench=. -benchmem -run=^$ ./tests/benchmarks/... \
    -benchtime=10s > coverage/benchmarks.txt

# Merge coverage files
echo -e "\n${YELLOW}Merging coverage reports...${NC}"
echo "mode: atomic" > coverage/total.out
tail -q -n +2 coverage/unit.out coverage/integration.out >> coverage/total.out

# Generate HTML coverage report
echo -e "\n${YELLOW}Generating HTML coverage report...${NC}"
go tool cover -html=coverage/total.out -o coverage/coverage.html

# Calculate total coverage
COVERAGE=$(go tool cover -func=coverage/total.out | grep total | awk '{print $3}')
echo -e "\n${GREEN}Total Coverage: ${COVERAGE}${NC}"

# Check coverage threshold
THRESHOLD=70.0
COVERAGE_NUM=$(echo $COVERAGE | sed 's/%//')
if (( $(echo "$COVERAGE_NUM < $THRESHOLD" | bc -l) )); then
    echo -e "${RED}❌ Coverage ${COVERAGE} is below threshold ${THRESHOLD}%${NC}"
    exit 1
else
    echo -e "${GREEN}✅ Coverage ${COVERAGE} meets threshold ${THRESHOLD}%${NC}"
fi

# Print benchmark summary
echo -e "\n${YELLOW}Benchmark Summary:${NC}"
echo "===================="
grep -E "Benchmark|ns/op|allocs/op" coverage/benchmarks.txt | head -20

# Generate coverage badge (optional)
if command -v gocov &> /dev/null; then
    echo -e "\n${YELLOW}Generating coverage badge...${NC}"
    gocov convert coverage/total.out | gocov report
fi

echo -e "\n${GREEN}✅ All tests completed!${NC}"
echo "Coverage report available at: coverage/coverage.html"
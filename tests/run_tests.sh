#!/bin/bash
# Single unified test runner for MCP server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "MCP Server Comprehensive Test Suite"
echo "==================================="
echo ""

# Change to project root
cd "$(dirname "$0")/.."

# Run the unified test runner
echo -e "${YELLOW}Running all tests...${NC}"
echo "This includes:"
echo "  - Unit tests"
echo "  - Integration tests"
echo "  - Real NRDB tests (if credentials available)"
echo "  - Mock MCP tests"
echo "  - Performance tests"
echo "  - Security tests"
echo "  - Directory structure tests"
echo "  - Configuration tests"
echo "  - End-to-end workflows"
echo ""

python3 tests/test_all.py

EXIT_CODE=$?

# Summary
echo ""
echo -e "${YELLOW}Test Summary${NC}"
echo "============"
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}All tests completed!${NC}"
else
    echo -e "${RED}Tests completed with failures!${NC}"
fi

exit $EXIT_CODE
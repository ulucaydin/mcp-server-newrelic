#!/bin/bash
# Comprehensive test runner for MCP Server New Relic

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

# Parse command line arguments
RUN_UNIT=true
RUN_INTEGRATION=false
RUN_LINT=true
RUN_SECURITY=true
RUN_COVERAGE=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --all)
            RUN_INTEGRATION=true
            RUN_COVERAGE=true
            shift
            ;;
        --integration)
            RUN_INTEGRATION=true
            shift
            ;;
        --no-lint)
            RUN_LINT=false
            shift
            ;;
        --no-security)
            RUN_SECURITY=false
            shift
            ;;
        --coverage)
            RUN_COVERAGE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --all           Run all tests including integration tests"
            echo "  --integration   Include integration tests"
            echo "  --no-lint       Skip linting checks"
            echo "  --no-security   Skip security checks"
            echo "  --coverage      Generate coverage report"
            echo "  --verbose       Show detailed output"
            echo "  --help          Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check if virtual environment is activated
if [[ -z "${VIRTUAL_ENV}" ]]; then
    if [ -d "venv" ]; then
        print_info "Activating virtual environment..."
        source venv/bin/activate
    else
        print_error "No virtual environment found. Run scripts/setup-dev.sh first."
        exit 1
    fi
fi

# Create test results directory
mkdir -p test-results

echo "========================================="
echo "Running MCP Server New Relic Tests"
echo "========================================="
echo ""

# Track overall status
FAILED=0

# Run linting checks
if [ "$RUN_LINT" = true ]; then
    print_info "Running code formatting checks..."
    
    # Black
    if black --check . > test-results/black.log 2>&1; then
        print_status "Black formatting check passed"
    else
        print_error "Black formatting issues found"
        if [ "$VERBOSE" = true ]; then
            cat test-results/black.log
        fi
        FAILED=$((FAILED + 1))
    fi
    
    # isort
    if isort --check-only . > test-results/isort.log 2>&1; then
        print_status "Import sorting check passed"
    else
        print_error "Import sorting issues found"
        if [ "$VERBOSE" = true ]; then
            cat test-results/isort.log
        fi
        FAILED=$((FAILED + 1))
    fi
    
    # Ruff
    if ruff check . > test-results/ruff.log 2>&1; then
        print_status "Ruff linting passed"
    else
        print_warning "Ruff found issues"
        if [ "$VERBOSE" = true ]; then
            cat test-results/ruff.log
        fi
    fi
    
    # MyPy
    if mypy . --ignore-missing-imports > test-results/mypy.log 2>&1; then
        print_status "Type checking passed"
    else
        print_warning "Type checking found issues"
        if [ "$VERBOSE" = true ]; then
            cat test-results/mypy.log
        fi
    fi
fi

# Run security checks
if [ "$RUN_SECURITY" = true ]; then
    print_info "Running security checks..."
    
    # Bandit
    if bandit -r . -f json -o test-results/bandit.json > /dev/null 2>&1; then
        print_status "Bandit security scan passed"
    else
        print_warning "Bandit found potential security issues"
        if [ "$VERBOSE" = true ]; then
            bandit -r . -f txt
        fi
    fi
    
    # Safety check
    if safety check --json > test-results/safety.json 2>&1; then
        print_status "No known vulnerabilities in dependencies"
    else
        print_warning "Safety found vulnerabilities"
        if [ "$VERBOSE" = true ]; then
            safety check
        fi
    fi
fi

# Run unit tests
if [ "$RUN_UNIT" = true ]; then
    print_info "Running unit tests..."
    
    PYTEST_ARGS="-v"
    if [ "$RUN_COVERAGE" = true ]; then
        PYTEST_ARGS="$PYTEST_ARGS --cov=. --cov-report=html --cov-report=xml --cov-report=term-missing"
    fi
    
    if [ "$VERBOSE" = true ]; then
        PYTEST_ARGS="$PYTEST_ARGS -s"
    fi
    
    if pytest tests/ $PYTEST_ARGS -m "not integration" --junit-xml=test-results/junit.xml; then
        print_status "Unit tests passed"
    else
        print_error "Unit tests failed"
        FAILED=$((FAILED + 1))
    fi
fi

# Run integration tests
if [ "$RUN_INTEGRATION" = true ]; then
    print_info "Running integration tests..."
    
    # Check if API credentials are available
    if [[ -z "${NEW_RELIC_API_KEY}" ]]; then
        print_warning "NEW_RELIC_API_KEY not set, skipping integration tests"
    else
        PYTEST_ARGS="-v"
        if [ "$VERBOSE" = true ]; then
            PYTEST_ARGS="$PYTEST_ARGS -s"
        fi
        
        if pytest tests/ $PYTEST_ARGS -m integration --junit-xml=test-results/junit-integration.xml; then
            print_status "Integration tests passed"
        else
            print_error "Integration tests failed"
            FAILED=$((FAILED + 1))
        fi
    fi
fi

# Generate coverage report
if [ "$RUN_COVERAGE" = true ] && [ -f "coverage.xml" ]; then
    print_info "Coverage report generated:"
    echo "  - HTML report: htmlcov/index.html"
    echo "  - XML report: coverage.xml"
    
    # Show coverage summary
    coverage report --skip-covered --skip-empty | tail -n 10
fi

# Summary
echo ""
echo "========================================="
if [ $FAILED -eq 0 ]; then
    print_status "All tests passed!"
    echo "========================================="
    exit 0
else
    print_error "$FAILED test suites failed"
    echo "========================================="
    echo ""
    echo "To fix issues:"
    echo "  - Formatting: make format"
    echo "  - Linting: review test-results/*.log"
    echo "  - Tests: review test output above"
    echo ""
    echo "For detailed output, run with --verbose"
    exit 1
fi
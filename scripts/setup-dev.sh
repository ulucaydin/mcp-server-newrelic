#!/bin/bash
# Development environment setup script for MCP Server New Relic

set -e  # Exit on error

echo "Setting up development environment for MCP Server New Relic..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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

# Check Python version
echo "Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    print_status "Python $PYTHON_VERSION found"
    
    # Check if version is 3.9 or higher
    if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 9) else 1)'; then
        print_status "Python version is compatible"
    else
        print_error "Python 3.9 or higher is required"
        exit 1
    fi
else
    print_error "Python 3 not found. Please install Python 3.9 or higher"
    exit 1
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    print_status "Virtual environment created"
else
    print_warning "Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
print_status "Virtual environment activated"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip --quiet
print_status "Pip upgraded"

# Install dependencies
echo "Installing production dependencies..."
pip install -r requirements.txt --quiet
print_status "Production dependencies installed"

# Install development dependencies
echo "Installing development dependencies..."
pip install -e ".[dev]" --quiet 2>/dev/null || {
    print_warning "Could not install from pyproject.toml, installing dev dependencies from requirements.txt"
    pip install black ruff isort mypy pytest pytest-asyncio pytest-cov pytest-mock bandit safety --quiet
}
print_status "Development dependencies installed"

# Install pre-commit hooks
if command -v pre-commit &> /dev/null; then
    echo "Installing pre-commit hooks..."
    pre-commit install
    print_status "Pre-commit hooks installed"
else
    print_warning "pre-commit not found, skipping hook installation"
fi

# Create necessary directories
echo "Creating project directories..."
mkdir -p data/entity_definitions
mkdir -p configs/plugins
mkdir -p audit_logs
mkdir -p logs
print_status "Project directories created"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    print_warning "Please edit .env file with your New Relic API credentials"
else
    print_status ".env file already exists"
fi

# Run initial checks
echo "Running initial checks..."

# Check code formatting
echo "Checking code style..."
if black --check . &> /dev/null; then
    print_status "Code formatting is correct"
else
    print_warning "Code formatting issues found. Run 'make format' to fix"
fi

# Display next steps
echo ""
echo "========================================="
echo "Development environment setup complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your New Relic API credentials"
echo "2. Run 'source venv/bin/activate' to activate the virtual environment"
echo "3. Run 'make test' to run the test suite"
echo "4. Run 'make run-dev' to start the server in development mode"
echo ""
echo "Useful commands:"
echo "  make help      - Show all available commands"
echo "  make format    - Format code with black and isort"
echo "  make lint      - Run all linters"
echo "  make test      - Run tests"
echo "  make run       - Run the server"
echo ""
print_status "Setup complete!"
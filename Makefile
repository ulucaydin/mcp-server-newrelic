.PHONY: help install install-dev format lint test test-unit test-integration test-coverage clean build docker-build docker-run docs

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
PIP := $(PYTHON) -m pip
PROJECT_NAME := mcp-server-newrelic
DOCKER_IMAGE := $(PROJECT_NAME):latest

# Colors for terminal output
COLOR_RESET := \033[0m
COLOR_BOLD := \033[1m
COLOR_GREEN := \033[32m
COLOR_YELLOW := \033[33m
COLOR_BLUE := \033[34m

help: ## Show this help message
	@echo "$(COLOR_BOLD)$(PROJECT_NAME) Development Commands$(COLOR_RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "$(COLOR_GREEN)%-20s$(COLOR_RESET) %s\n", $$1, $$2}'

install: ## Install production dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install-dev: install ## Install development dependencies
	$(PIP) install -e ".[dev]"
	pre-commit install || echo "pre-commit not installed"

format: ## Format code with black and isort
	@echo "$(COLOR_YELLOW)Formatting code...$(COLOR_RESET)"
	black .
	isort .

lint: ## Run all linters
	@echo "$(COLOR_YELLOW)Running linters...$(COLOR_RESET)"
	ruff check . --fix
	black --check .
	isort --check-only .
	mypy . --ignore-missing-imports || true

security: ## Run security checks
	@echo "$(COLOR_YELLOW)Running security checks...$(COLOR_RESET)"
	bandit -r . -f json -o bandit-report.json || true
	safety check --json || true

test: ## Run all tests
	@echo "$(COLOR_YELLOW)Running tests...$(COLOR_RESET)"
	pytest tests/ -v

test-unit: ## Run unit tests only
	@echo "$(COLOR_YELLOW)Running unit tests...$(COLOR_RESET)"
	pytest tests/ -v -m "not integration"

test-integration: ## Run integration tests only
	@echo "$(COLOR_YELLOW)Running integration tests...$(COLOR_RESET)"
	pytest tests/ -v -m integration

test-coverage: ## Run tests with coverage report
	@echo "$(COLOR_YELLOW)Running tests with coverage...$(COLOR_RESET)"
	pytest tests/ -v --cov=. --cov-report=html --cov-report=term-missing -m "not integration"
	@echo "Coverage report generated in htmlcov/index.html"

clean: ## Clean up generated files
	@echo "$(COLOR_YELLOW)Cleaning up...$(COLOR_RESET)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	rm -rf .eggs
	rm -f bandit-report.json

build: clean ## Build distribution packages
	@echo "$(COLOR_YELLOW)Building distribution packages...$(COLOR_RESET)"
	$(PYTHON) -m build

docker-build: ## Build Docker image
	@echo "$(COLOR_YELLOW)Building Docker image...$(COLOR_RESET)"
	docker build -t $(DOCKER_IMAGE) .

docker-run: ## Run Docker container
	@echo "$(COLOR_YELLOW)Running Docker container...$(COLOR_RESET)"
	docker run --rm -it \
		-e NEW_RELIC_API_KEY="$${NEW_RELIC_API_KEY}" \
		-e NEW_RELIC_ACCOUNT_ID="$${NEW_RELIC_ACCOUNT_ID}" \
		$(DOCKER_IMAGE)

docs: ## Generate documentation
	@echo "$(COLOR_YELLOW)Generating documentation...$(COLOR_RESET)"
	# Add documentation generation commands here
	@echo "Documentation generation not yet implemented"

run: ## Run the MCP server locally
	@echo "$(COLOR_YELLOW)Starting MCP server...$(COLOR_RESET)"
	$(PYTHON) main.py

run-dev: ## Run the MCP server in development mode
	@echo "$(COLOR_YELLOW)Starting MCP server in dev mode...$(COLOR_RESET)"
	MCP_TRANSPORT=stdio LOG_LEVEL=DEBUG $(PYTHON) main.py

check-env: ## Check if required environment variables are set
	@echo "$(COLOR_YELLOW)Checking environment variables...$(COLOR_RESET)"
	@test -n "$${NEW_RELIC_API_KEY}" || (echo "$(COLOR_BOLD)ERROR: NEW_RELIC_API_KEY not set$(COLOR_RESET)" && exit 1)
	@test -n "$${NEW_RELIC_ACCOUNT_ID}" || (echo "$(COLOR_BOLD)WARNING: NEW_RELIC_ACCOUNT_ID not set$(COLOR_RESET)")
	@echo "$(COLOR_GREEN)Environment check passed!$(COLOR_RESET)"

pre-commit: format lint test-unit ## Run pre-commit checks
	@echo "$(COLOR_GREEN)Pre-commit checks passed!$(COLOR_RESET)"

release: clean build ## Prepare a release
	@echo "$(COLOR_YELLOW)Preparing release...$(COLOR_RESET)"
	twine check dist/*
	@echo "$(COLOR_GREEN)Release preparation complete!$(COLOR_RESET)"
	@echo "Run 'twine upload dist/*' to upload to PyPI"

update-deps: ## Update dependencies
	@echo "$(COLOR_YELLOW)Updating dependencies...$(COLOR_RESET)"
	$(PIP) list --outdated
	@echo ""
	@echo "Update requirements.txt manually with the versions you want"

init-project: install-dev ## Initialize project for development
	@echo "$(COLOR_YELLOW)Initializing project...$(COLOR_RESET)"
	mkdir -p data/entity_definitions
	touch data/entity_definitions/.gitkeep
	mkdir -p configs/plugins
	mkdir -p audit_logs
	@echo "$(COLOR_GREEN)Project initialized!$(COLOR_RESET)"

.PHONY: all
all: clean install-dev lint test build ## Run all checks and build
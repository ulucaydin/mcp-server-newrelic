# Multi-stage Dockerfile for MCP Server New Relic

# Stage 1: Base image with system dependencies
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 mcp && \
    useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash mcp

WORKDIR /app

# Stage 2: Dependencies
FROM base as dependencies

# Copy dependency files
COPY requirements.txt .
COPY pyproject.toml* .
COPY setup.py* .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Stage 3: Development image
FROM dependencies as development

# Install development dependencies
RUN pip install --no-cache-dir \
    black ruff isort mypy \
    pytest pytest-asyncio pytest-cov pytest-timeout pytest-mock \
    watchdog ipython

# Copy all source code
COPY --chown=mcp:mcp . .

# Create necessary directories
RUN mkdir -p audit_logs logs .cache data/entity_definitions configs/plugins && \
    chown -R mcp:mcp audit_logs logs .cache data configs

# Switch to non-root user
USER mcp

# Development environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV MCP_TRANSPORT=http
ENV LOG_LEVEL=DEBUG
ENV LOG_FORMAT=text

# Run with auto-reload for development
CMD ["python", "-m", "watchdog.auto_restart", "--patterns=*.py", "--", "python", "main.py"]

# Stage 4: Testing image
FROM dependencies as test

# Install test dependencies
RUN pip install --no-cache-dir \
    pytest pytest-asyncio pytest-cov pytest-timeout pytest-mock \
    black ruff isort mypy bandit safety

# Copy source code and tests
COPY --chown=mcp:mcp . .

# Switch to non-root user for testing
USER mcp

# Run linting and tests
RUN python -m black --check . && \
    python -m isort --check-only . && \
    python -m ruff check . && \
    python -m pytest tests/ -v --cov=. --cov-report=term-missing -m "not integration" || true

# Stage 5: Production image
FROM base as production

# Set production environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    MCP_TRANSPORT=stdio

# Copy only necessary files from dependencies stage
COPY --from=dependencies /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# Copy application code (excluding tests and dev files)
COPY --chown=mcp:mcp core core/
COPY --chown=mcp:mcp features features/
COPY --chown=mcp:mcp transports transports/
COPY --chown=mcp:mcp main.py server.py config.py client.py cli.py ./
COPY --chown=mcp:mcp configs configs/
COPY --chown=mcp:mcp data data/

# Create necessary directories
RUN mkdir -p audit_logs logs .cache /home/mcp/.newrelic-mcp && \
    chown -R mcp:mcp audit_logs logs .cache /home/mcp

# Switch to non-root user
USER mcp

# Cache entity definitions at build time (optional)
RUN python -c "\
from core.entity_definitions import EntityDefinitionsCache; \
try: \
    cache = EntityDefinitionsCache(); \
    print('Entity definitions cached successfully'); \
except Exception as e: \
    print(f'Warning: Could not cache entity definitions: {e}')" || true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "\
import os; \
transport = os.getenv('MCP_TRANSPORT', 'stdio'); \
if transport == 'http': \
    import httpx; \
    try: \
        resp = httpx.get('http://localhost:3000/health', timeout=5); \
        resp.raise_for_status(); \
        exit(0); \
    except: exit(1); \
else: \
    from core.account_manager import AccountManager; \
    try: \
        AccountManager().get_current_credentials(); \
        exit(0); \
    except: exit(1)"

# Expose ports
EXPOSE 3000 9090

# Run the server
CMD ["python", "main.py"]
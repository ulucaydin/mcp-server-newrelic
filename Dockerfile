# New Relic MCP Server Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MCP_TRANSPORT=stdio

# Create a non-root user
RUN groupadd --gid 1000 mcp && \
    useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash mcp

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /home/mcp/.newrelic-mcp

# Change ownership to mcp user
RUN chown -R mcp:mcp /app /home/mcp

# Switch to non-root user
USER mcp

# Cache entity definitions at build time (optional)
RUN python -c "
from core.entity_definitions import EntityDefinitionsCache
try:
    cache = EntityDefinitionsCache()
    print('Entity definitions cached successfully')
except Exception as e:
    print(f'Warning: Could not cache entity definitions: {e}')
" || true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "
import asyncio
import sys
try:
    from core.account_manager import AccountManager
    manager = AccountManager()
    creds = manager.get_current_credentials()
    print('Health check passed')
    sys.exit(0)
except Exception as e:
    print(f'Health check failed: {e}')
    sys.exit(1)
"

# Expose port for HTTP transport (if used)
EXPOSE 3000

# Default command
CMD ["python", "main.py"]
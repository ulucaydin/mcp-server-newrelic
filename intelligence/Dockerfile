# Dockerfile for Intelligence Engine
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy language model
RUN python -m spacy download en_core_web_sm

# Copy intelligence module
COPY . .

# Create directories for models and config
RUN mkdir -p /app/models /app/config /app/logs

# Set environment variables
ENV PYTHONPATH=/app
ENV INTELLIGENCE_LOG_LEVEL=INFO
ENV INTELLIGENCE_GRPC_HOST=0.0.0.0
ENV INTELLIGENCE_GRPC_PORT=50051
ENV INTELLIGENCE_METRICS_PORT=8080

# Expose ports
EXPOSE 50051 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import grpc; channel = grpc.insecure_channel('localhost:50051'); channel.channel_ready()" || exit 1

# Default command runs gRPC server
CMD ["python", "-m", "intelligence.grpc_server"]
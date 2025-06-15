# Docker Deployment Guide for Intelligence Engine

This guide explains how to build and deploy the Intelligence Engine using Docker.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+ (optional, for full stack)
- At least 2GB of available memory
- Port 50051 (gRPC) and 8080 (metrics) available

## Quick Start

### Using the Build Script

The easiest way to manage the Intelligence Engine container is using the provided build script:

```bash
# Build the Docker image
./docker-build.sh build

# Run the container
./docker-build.sh run

# Check logs
./docker-build.sh logs

# Test gRPC connection
./docker-build.sh test
```

### Manual Docker Commands

If you prefer manual control:

```bash
# Build image
docker build -t intelligence-engine:latest .

# Run container
docker run -d \
  --name intelligence-engine \
  -p 50051:50051 \
  -p 8080:8080 \
  -v $(pwd)/config:/app/config:ro \
  -v intelligence-models:/app/models \
  intelligence-engine:latest

# Check status
docker ps
docker logs intelligence-engine
```

## Docker Compose Stack

For a complete monitoring stack with Prometheus and Grafana:

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f intelligence-engine

# Stop all services
docker-compose down
```

This will start:
- Intelligence Engine (port 50051 for gRPC, 8080 for metrics)
- Prometheus (port 9090) - metrics collection
- Grafana (port 3000) - visualization dashboards

Access Grafana at http://localhost:3000 (default credentials: admin/admin)

## Configuration

### Environment Variables

The container supports configuration through environment variables:

```yaml
# Logging
INTELLIGENCE_LOG_LEVEL: INFO|DEBUG|WARNING|ERROR

# gRPC Server
INTELLIGENCE_GRPC_HOST: 0.0.0.0
INTELLIGENCE_GRPC_PORT: 50051
INTELLIGENCE_GRPC_MAX_WORKERS: 10

# Metrics
INTELLIGENCE_ENABLE_METRICS: true
INTELLIGENCE_METRICS_PORT: 8080

# Pattern Detection
INTELLIGENCE_PATTERN_MIN_CONFIDENCE: 0.7
INTELLIGENCE_PATTERN_ENABLE_CACHING: true

# Query Generation
INTELLIGENCE_QUERY_CACHE_SIZE: 100
INTELLIGENCE_QUERY_OPTIMIZER_MODE: balanced|cost|speed
```

### Configuration File

Mount a configuration file for more detailed settings:

```bash
docker run -d \
  --name intelligence-engine \
  -v $(pwd)/my-config.yaml:/app/config/intelligence.yaml:ro \
  intelligence-engine:latest
```

See `config/intelligence.yaml.example` for configuration options.

## Volumes

The container uses several volumes:

- `/app/config` - Configuration files (read-only)
- `/app/models` - ML model registry (persistent)
- `/app/logs` - Application logs

Example with named volumes:

```bash
docker run -d \
  --name intelligence-engine \
  -v intelligence-config:/app/config:ro \
  -v intelligence-models:/app/models \
  -v intelligence-logs:/app/logs \
  intelligence-engine:latest
```

## Health Checks

The container includes health checks:

```bash
# Check health status
docker inspect --format='{{.State.Health.Status}}' intelligence-engine

# Manual health check
docker exec intelligence-engine python -c \
  "import grpc; channel = grpc.insecure_channel('localhost:50051'); print('Healthy' if channel.channel_ready() else 'Unhealthy')"
```

## Resource Limits

Recommended resource limits:

```yaml
# docker-compose.yml
services:
  intelligence-engine:
    # ...
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

Or with docker run:

```bash
docker run -d \
  --name intelligence-engine \
  --cpus="2" \
  --memory="2g" \
  intelligence-engine:latest
```

## Networking

### Connecting from Other Containers

When running in a Docker network:

```python
# From another container in the same network
import grpc
channel = grpc.insecure_channel('intelligence-engine:50051')
```

### Host Networking

For development, you can use host networking:

```bash
docker run -d \
  --name intelligence-engine \
  --network host \
  intelligence-engine:latest
```

## Monitoring

### Prometheus Metrics

The engine exposes Prometheus metrics on port 8080:

```bash
# View raw metrics
curl http://localhost:8080/metrics

# Key metrics to monitor:
# - intelligence_operation_duration_seconds
# - intelligence_patterns_detected_total
# - intelligence_queries_generated_total
# - intelligence_errors_total
# - intelligence_cpu_usage_percent
# - intelligence_memory_usage_bytes
```

### Grafana Dashboards

Import the provided dashboards from `grafana/dashboards/`:

1. Navigate to http://localhost:3000
2. Login with admin/admin
3. Go to Dashboards → Import
4. Upload the dashboard JSON files

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs intelligence-engine

# Common issues:
# - Port already in use: change ports in docker-compose.yml
# - Memory limit too low: increase to at least 1GB
# - Missing config: ensure config directory exists
```

### gRPC Connection Failed

```bash
# Test from inside container
docker exec intelligence-engine python -m intelligence.grpc_server

# Check if port is exposed
docker port intelligence-engine

# Test with grpcurl
grpcurl -plaintext localhost:50051 list
```

### High Memory Usage

```bash
# Check memory usage
docker stats intelligence-engine

# Reduce memory usage:
# - Lower INTELLIGENCE_PATTERN_SAMPLE_SIZE
# - Reduce INTELLIGENCE_QUERY_CACHE_SIZE
# - Disable unused pattern detectors
```

### Model Loading Issues

```bash
# Check model volume
docker exec intelligence-engine ls -la /app/models

# Reset model registry
docker volume rm intelligence-models
docker volume create intelligence-models
```

## Production Deployment

### Security Considerations

1. **Use TLS for gRPC**:
   ```python
   # In grpc_server.py
   credentials = grpc.ssl_server_credentials(...)
   server.add_secure_port('[::]:50051', credentials)
   ```

2. **Run as non-root user**:
   ```dockerfile
   # In Dockerfile
   RUN useradd -m -u 1000 intelligence
   USER intelligence
   ```

3. **Limit network exposure**:
   ```yaml
   # docker-compose.yml
   ports:
     - "127.0.0.1:50051:50051"  # Only localhost
   ```

### Scaling

For horizontal scaling:

```yaml
# docker-compose.yml
services:
  intelligence-engine:
    # ...
    deploy:
      replicas: 3
    # Use external load balancer for gRPC
```

### Logging

Configure centralized logging:

```yaml
# docker-compose.yml
services:
  intelligence-engine:
    # ...
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

Or use external logging:

```bash
docker run -d \
  --name intelligence-engine \
  --log-driver=syslog \
  --log-opt syslog-address=tcp://logserver:514 \
  intelligence-engine:latest
```

## Backup and Recovery

### Backup Models

```bash
# Backup model registry
docker run --rm \
  -v intelligence-models:/models \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/models-$(date +%Y%m%d).tar.gz -C /models .
```

### Restore Models

```bash
# Restore model registry
docker run --rm \
  -v intelligence-models:/models \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/models-20240115.tar.gz -C /models
```

## Updates

To update the Intelligence Engine:

```bash
# Pull or build new image
docker build -t intelligence-engine:new .

# Stop old container
docker stop intelligence-engine
docker rm intelligence-engine

# Start new container with same volumes
docker run -d \
  --name intelligence-engine \
  -v intelligence-models:/app/models \
  intelligence-engine:new
```

## Useful Commands

```bash
# View real-time metrics
watch -n 1 'curl -s localhost:8080/metrics | grep intelligence_'

# Export container logs
docker logs intelligence-engine > intelligence-$(date +%Y%m%d).log

# Inspect container
docker inspect intelligence-engine

# Execute Python commands
docker exec intelligence-engine python -c "from intelligence.patterns.engine import PatternEngine; print(PatternEngine)"

# Clean up everything
docker-compose down -v
docker system prune -a
```
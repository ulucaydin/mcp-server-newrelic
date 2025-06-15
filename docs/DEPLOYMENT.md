# Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Configuration](#configuration)
3. [Deployment Options](#deployment-options)
4. [Production Setup](#production-setup)
5. [Monitoring](#monitoring)
6. [Scaling](#scaling)
7. [Security](#security)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### Infrastructure Requirements

#### Minimum Requirements (Development)
- **CPU**: 4 cores
- **RAM**: 8 GB
- **Storage**: 20 GB SSD
- **Network**: 100 Mbps

#### Recommended Requirements (Production)
- **CPU**: 8+ cores per service
- **RAM**: 16+ GB per service
- **Storage**: 100+ GB SSD with high IOPS
- **Network**: 1 Gbps with low latency to New Relic

### Software Requirements
- **Docker**: 20.10+
- **Kubernetes**: 1.24+ (for K8s deployment)
- **PostgreSQL**: 14+
- **Redis**: 7+

### New Relic Requirements
- Valid New Relic API Key
- Account ID
- Appropriate permissions for API access

## Configuration

### Environment Variables

Create a production `.env` file:

```bash
# New Relic Configuration
NEW_RELIC_API_KEY=your_production_api_key
NEW_RELIC_USER_KEY=your_production_user_key
NEW_RELIC_ACCOUNT_ID=your_account_id
NEW_RELIC_REGION=US  # or EU

# Service Configuration
DISCOVERY_ENGINE_HOST=discovery-engine
DISCOVERY_ENGINE_PORT=8081
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8080

# Database Configuration
DATABASE_URL=postgresql://user:password@postgres:5432/uds_production?sslmode=require
REDIS_URL=redis://:password@redis:6379/0

# Security
JWT_SECRET=generate_strong_secret_here
API_KEY_SALT=generate_strong_salt_here
ENCRYPTION_KEY=generate_32_byte_key_here

# Observability
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp.nr-data.net:4317
OTEL_EXPORTER_OTLP_HEADERS=Api-Key=your_new_relic_license_key
OTEL_SERVICE_NAME=uds-production
OTEL_RESOURCE_ATTRIBUTES=service.name=uds,service.version=1.0.0,environment=production

# Performance
DISCOVERY_WORKER_COUNT=20
DISCOVERY_CACHE_TTL=10m
DISCOVERY_CACHE_SIZE=10000
NRDB_RATE_LIMIT_REQUESTS_PER_SECOND=50

# Production Settings
LOG_LEVEL=info
LOG_FORMAT=json
DEV_MODE=false
```

### Configuration Files

#### `config/production.yaml`
```yaml
server:
  port: 8080
  read_timeout: 30s
  write_timeout: 30s
  max_request_size: 10MB

discovery:
  worker_count: 20
  batch_size: 100
  cache:
    type: redis
    ttl: 10m
    max_size: 10000

security:
  rate_limit:
    requests_per_minute: 100
    burst: 200
  cors:
    allowed_origins:
      - https://your-domain.com
    allowed_methods:
      - GET
      - POST
    allowed_headers:
      - Authorization
      - Content-Type

monitoring:
  metrics:
    enabled: true
    port: 9090
  health:
    enabled: true
    interval: 30s
```

## Deployment Options

### Option 1: Docker Compose (Simple)

#### `docker-compose.prod.yml`
```yaml
version: '3.8'

services:
  mcp-server:
    image: ghcr.io/deepaucksharma/uds-mcp:latest
    env_file:
      - .env.production
    ports:
      - "8080:8080"
    depends_on:
      - discovery-engine
      - postgres
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G

  discovery-engine:
    image: ghcr.io/deepaucksharma/uds-discovery:latest
    env_file:
      - .env.production
    ports:
      - "8081:8081"
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "/health-check"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G

  postgres:
    image: postgres:14-alpine
    environment:
      POSTGRES_DB: uds_production
      POSTGRES_USER: uds
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

Deploy with:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Option 2: Kubernetes (Recommended)

#### Namespace and ConfigMap
```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: uds

---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: uds-config
  namespace: uds
data:
  DISCOVERY_ENGINE_HOST: "discovery-service"
  DISCOVERY_ENGINE_PORT: "8081"
  MCP_SERVER_PORT: "8080"
  LOG_LEVEL: "info"
  LOG_FORMAT: "json"
```

#### Secrets
```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: uds-secrets
  namespace: uds
type: Opaque
stringData:
  NEW_RELIC_API_KEY: "your_api_key"
  DATABASE_URL: "postgresql://user:password@postgres:5432/uds"
  REDIS_URL: "redis://:password@redis:6379/0"
  JWT_SECRET: "your_jwt_secret"
```

#### Deployments
```yaml
# k8s/mcp-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-server
  namespace: uds
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mcp-server
  template:
    metadata:
      labels:
        app: mcp-server
    spec:
      containers:
      - name: mcp-server
        image: ghcr.io/deepaucksharma/uds-mcp:latest
        ports:
        - containerPort: 8080
        envFrom:
        - configMapRef:
            name: uds-config
        - secretRef:
            name: uds-secrets
        resources:
          requests:
            cpu: 1000m
            memory: 2Gi
          limits:
            cpu: 2000m
            memory: 4Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10

---
# k8s/discovery-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: discovery-engine
  namespace: uds
spec:
  replicas: 5
  selector:
    matchLabels:
      app: discovery-engine
  template:
    metadata:
      labels:
        app: discovery-engine
    spec:
      containers:
      - name: discovery-engine
        image: ghcr.io/deepaucksharma/uds-discovery:latest
        ports:
        - containerPort: 8081
        envFrom:
        - configMapRef:
            name: uds-config
        - secretRef:
            name: uds-secrets
        resources:
          requests:
            cpu: 2000m
            memory: 4Gi
          limits:
            cpu: 4000m
            memory: 8Gi
```

#### Services
```yaml
# k8s/services.yaml
apiVersion: v1
kind: Service
metadata:
  name: mcp-service
  namespace: uds
spec:
  type: LoadBalancer
  selector:
    app: mcp-server
  ports:
  - port: 80
    targetPort: 8080

---
apiVersion: v1
kind: Service
metadata:
  name: discovery-service
  namespace: uds
spec:
  type: ClusterIP
  selector:
    app: discovery-engine
  ports:
  - port: 8081
    targetPort: 8081
```

#### Ingress
```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: uds-ingress
  namespace: uds
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - api.your-domain.com
    secretName: uds-tls
  rules:
  - host: api.your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: mcp-service
            port:
              number: 80
```

Deploy with:
```bash
kubectl apply -f k8s/
```

### Option 3: Cloud-Specific Deployments

#### AWS ECS
```json
{
  "family": "uds-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "containerDefinitions": [
    {
      "name": "mcp-server",
      "image": "ghcr.io/deepaucksharma/uds-mcp:latest",
      "portMappings": [
        {
          "containerPort": 8080,
          "protocol": "tcp"
        }
      ],
      "environment": [...],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/uds",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "mcp"
        }
      }
    }
  ]
}
```

#### Google Cloud Run
```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: uds-mcp
spec:
  template:
    metadata:
      annotations:
        run.googleapis.com/execution-environment: gen2
    spec:
      containers:
      - image: ghcr.io/deepaucksharma/uds-mcp:latest
        resources:
          limits:
            cpu: '4'
            memory: 8Gi
        env:
        - name: NEW_RELIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: uds-secrets
              key: api-key
```

## Production Setup

### 1. SSL/TLS Configuration

#### Let's Encrypt with Cert-Manager
```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.12.0/cert-manager.yaml

# Create issuer
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

### 2. Database Setup

#### PostgreSQL Initialization
```sql
-- Create database and user
CREATE DATABASE uds_production;
CREATE USER uds_user WITH ENCRYPTED PASSWORD 'strong_password';
GRANT ALL PRIVILEGES ON DATABASE uds_production TO uds_user;

-- Create schema
\c uds_production;

CREATE TABLE discovery_cache (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_discovery_cache_key ON discovery_cache(key);
CREATE INDEX idx_discovery_cache_expires ON discovery_cache(expires_at);

-- Add other tables as needed
```

### 3. Redis Configuration

```conf
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
requirepass your_redis_password
```

## Monitoring

### 1. Prometheus Setup

```yaml
# prometheus-config.yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'uds-mcp'
    static_configs:
      - targets: ['mcp-service:9090']
  
  - job_name: 'uds-discovery'
    static_configs:
      - targets: ['discovery-service:9090']
```

### 2. Grafana Dashboards

Import provided dashboards:
- `dashboards/uds-overview.json`
- `dashboards/uds-performance.json`
- `dashboards/uds-errors.json`

### 3. Alerts

```yaml
# alerts.yaml
groups:
  - name: uds_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(mcp_requests_total{status="error"}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"
          
      - alert: SlowResponse
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        annotations:
          summary: "95th percentile response time > 1s"
```

## Scaling

### Horizontal Pod Autoscaling

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mcp-hpa
  namespace: uds
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mcp-server
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Vertical Pod Autoscaling

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: discovery-vpa
  namespace: uds
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: discovery-engine
  updatePolicy:
    updateMode: "Auto"
```

## Security

### 1. Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: uds-network-policy
  namespace: uds
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: uds
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: uds
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 443  # HTTPS for external APIs
```

### 2. Pod Security Policy

```yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: uds-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
```

### 3. Secrets Management

Use external secret management:
```yaml
# Using Sealed Secrets
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: uds-secrets
  namespace: uds
spec:
  encryptedData:
    NEW_RELIC_API_KEY: AgB3Lw1K...
```

## Troubleshooting

### Common Issues

#### 1. Service Not Starting
```bash
# Check logs
kubectl logs -f deployment/mcp-server -n uds
kubectl describe pod <pod-name> -n uds

# Check events
kubectl get events -n uds --sort-by='.lastTimestamp'
```

#### 2. Database Connection Issues
```bash
# Test connection
kubectl run -it --rm debug --image=postgres:14 --restart=Never -- \
  psql postgresql://user:password@postgres:5432/uds

# Check network
kubectl exec -it <pod-name> -- nc -zv postgres 5432
```

#### 3. High Memory Usage
```bash
# Check resource usage
kubectl top pods -n uds

# Get detailed metrics
kubectl exec -it <pod-name> -- cat /proc/meminfo
```

### Health Checks

```bash
# Check overall health
curl http://api.your-domain.com/health

# Check specific component
kubectl exec -it <pod-name> -- curl localhost:8080/health
```

### Performance Tuning

1. **Increase Worker Count**
   ```bash
   kubectl set env deployment/discovery-engine DISCOVERY_WORKER_COUNT=30
   ```

2. **Adjust Cache Size**
   ```bash
   kubectl set env deployment/mcp-server DISCOVERY_CACHE_SIZE=20000
   ```

3. **Scale Replicas**
   ```bash
   kubectl scale deployment/mcp-server --replicas=5
   ```

## Backup and Recovery

### Database Backup
```bash
# Automated backup
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: uds
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: postgres-backup
            image: postgres:14
            command:
            - /bin/bash
            - -c
            - |
              pg_dump $DATABASE_URL | gzip > /backup/uds-$(date +%Y%m%d).sql.gz
              # Upload to S3 or other storage
          restartPolicy: OnFailure
EOF
```

### Disaster Recovery
1. **Regular Backups**: Database and configuration
2. **Multi-Region**: Deploy in multiple regions
3. **Monitoring**: Alert on failures
4. **Runbooks**: Document recovery procedures
# Architecture Overview

## Table of Contents
1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Data Flow](#data-flow)
4. [Integration Points](#integration-points)
5. [Security Architecture](#security-architecture)
6. [Performance Considerations](#performance-considerations)
7. [Scalability Design](#scalability-design)

## System Overview

The Universal Data Synthesizer (UDS) is a multi-tiered system designed to provide intelligent data discovery, analysis, and visualization capabilities for New Relic users through AI assistants.

### Design Principles
- **Modularity**: Each component has a single responsibility
- **Language Optimization**: Go for performance-critical paths, Python for AI/ML
- **Resilience**: Circuit breakers, retries, and graceful degradation
- **Observability**: Comprehensive tracing and metrics
- **Security**: Defense in depth with multiple security layers

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              User Layer                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │
│  │   Claude    │  │   Cursor    │  │  Continue   │  │  Web Client  │  │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬───────┘  │
└─────────┼────────────────┼────────────────┼────────────────┼──────────┘
          │                │                │                │
          └────────────────┴────────────────┴────────────────┘
                                   │
                           MCP/A2A Protocol
                                   │
┌─────────────────────────────────▼───────────────────────────────────────┐
│                          Interface Layer                                 │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                      Python MCP Server                              │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │ │
│  │  │   MCP    │  │  Plugin  │  │  Auth    │  │  Rate Limiter    │  │ │
│  │  │ Handler  │  │ Manager  │  │ Manager  │  │                  │  │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                   │                                      │
│                              gRPC/HTTP                                   │
│                                   │                                      │
│  ┌────────────────────────────────▼───────────────────────────────────┐ │
│  │                    Go Discovery Engine                              │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │ │
│  │  │  Schema  │  │ Pattern  │  │ Quality  │  │  Relationship    │  │ │
│  │  │Discovery │  │Detection │  │ Assessor │  │    Miner         │  │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
┌─────────────────────────────────▼───────────────────────────────────────┐
│                         Intelligence Layer                               │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                  Python Intelligence Engine                         │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │ │
│  │  │   NLP    │  │    ML    │  │ Insight  │  │   Recommender    │  │ │
│  │  │ Engine   │  │  Models  │  │Generator │  │                  │  │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
┌─────────────────────────────────▼───────────────────────────────────────┐
│                          Data Layer                                      │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌────────────────────┐  │
│  │New Relic  │  │PostgreSQL │  │  Redis    │  │  S3/Object Store  │  │
│  │   APIs    │  │           │  │   Cache   │  │                   │  │
│  └───────────┘  └───────────┘  └───────────┘  └────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. Interface Layer (Track 2)

#### Python MCP Server
- **Purpose**: AI-facing interface and tool orchestration
- **Technology**: Python 3.11+, FastMCP, asyncio
- **Key Components**:
  - MCP Handler: Protocol implementation and handshake
  - Plugin Manager: Dynamic tool loading and management
  - Auth Manager: API key and JWT validation
  - Rate Limiter: Request throttling and quota enforcement

#### Go Discovery Engine
- **Purpose**: High-performance data analysis
- **Technology**: Go 1.21+, gRPC, OpenTelemetry
- **Key Components**:
  - Schema Discovery: Parallel schema exploration
  - Pattern Detection: Time series and statistical analysis
  - Quality Assessor: Multi-dimensional data quality scoring
  - Relationship Miner: Cross-schema relationship discovery

### 2. Intelligence Layer (Track 3)

#### Python Intelligence Engine
- **Purpose**: AI/ML-powered analysis and insights
- **Technology**: Python, TensorFlow/PyTorch, scikit-learn
- **Components**:
  - NLP Engine: Natural language to NRQL translation
  - ML Models: Anomaly detection, forecasting
  - Insight Generator: Automated insight creation
  - Recommender: Dashboard and query recommendations

### 3. Data Layer

#### External Services
- **New Relic APIs**: NerdGraph, REST API, NRDB
- **PostgreSQL**: Metadata, user preferences, ML models
- **Redis**: Distributed cache, session storage
- **S3/Object Store**: Large datasets, model artifacts

## Data Flow

### 1. Tool Invocation Flow
```
AI Assistant → MCP Request → Python Server → Tool Registry
                                    ↓
                            Tool Execution
                                    ↓
                        [Simple Tool]  [Complex Tool]
                             ↓               ↓
                      Direct NR API    Discovery Engine
                             ↓               ↓
                         Response ← ← ← ← Merge Results
```

### 2. Discovery Flow
```
Discovery Request → gRPC → Discovery Engine
                              ↓
                    ┌─────────┴─────────┐
                    ↓                   ↓
            Schema Discovery      Pattern Detection
                    ↓                   ↓
              NRDB Queries         Data Analysis
                    ↓                   ↓
                    └─────────┬─────────┘
                              ↓
                        Merge & Cache
                              ↓
                      Return Schemas
```

### 3. Intelligence Flow
```
User Query → NLP Processing → Intent Recognition
                                    ↓
                            Query Planning
                                    ↓
                    ┌───────────────┴───────────────┐
                    ↓                               ↓
            Data Collection                  Model Inference
                    ↓                               ↓
            Discovery Engine                   ML Models
                    ↓                               ↓
                    └───────────────┬───────────────┘
                                    ↓
                            Insight Generation
                                    ↓
                            Recommendation
```

## Integration Points

### 1. Python ↔ Go Integration

#### gRPC Interface
```protobuf
service DiscoveryService {
  rpc DiscoverSchemas(DiscoverSchemasRequest) returns (DiscoverSchemasResponse);
  rpc ProfileSchema(ProfileSchemaRequest) returns (ProfileSchemaResponse);
  rpc IntelligentDiscovery(IntelligentDiscoveryRequest) returns (IntelligentDiscoveryResponse);
  rpc FindRelationships(FindRelationshipsRequest) returns (FindRelationshipsResponse);
  rpc AssessQuality(AssessQualityRequest) returns (AssessQualityResponse);
}
```

#### Communication Patterns
- **Synchronous**: Direct gRPC calls for immediate responses
- **Asynchronous**: Message queue for long-running analyses
- **Streaming**: Real-time updates for continuous discovery

### 2. External Integrations

#### New Relic APIs
- **NerdGraph**: GraphQL API for complex queries
- **REST API**: Legacy endpoints and admin operations
- **NRDB**: Direct database queries via NRQL

#### Observability Stack
- **OpenTelemetry**: Distributed tracing
- **Prometheus**: Metrics collection
- **New Relic APM**: Application monitoring

## Security Architecture

### 1. Authentication & Authorization

```
┌─────────────────┐
│   API Request   │
└────────┬────────┘
         ↓
┌────────▼────────┐
│  Rate Limiter   │ ← Check quota
└────────┬────────┘
         ↓
┌────────▼────────┐
│ Auth Middleware │ ← Validate token
└────────┬────────┘
         ↓
┌────────▼────────┐
│ Permission Check│ ← Verify access
└────────┬────────┘
         ↓
┌────────▼────────┐
│ Tool Execution  │
└─────────────────┘
```

### 2. Security Layers

#### Network Security
- TLS 1.3 for all external communication
- mTLS for internal service communication
- Network segmentation with firewalls

#### Application Security
- Input validation and sanitization
- NRQL injection prevention
- Output filtering for sensitive data

#### Data Security
- Encryption at rest (AES-256)
- Encryption in transit (TLS)
- Key rotation and management

### 3. Compliance & Audit

- Comprehensive audit logging
- GDPR/CCPA compliance
- SOC2 controls implementation

## Performance Considerations

### 1. Caching Strategy

```
┌─────────────────┐
│  Request Cache  │ ← 1 min TTL
└────────┬────────┘
         ↓ Miss
┌────────▼────────┐
│  Redis Cache    │ ← 5 min TTL
└────────┬────────┘
         ↓ Miss
┌────────▼────────┐
│ Discovery Engine│
└────────┬────────┘
         ↓
┌────────▼────────┐
│  Write Through  │
└─────────────────┘
```

### 2. Query Optimization

- **Parallel Processing**: Worker pools for concurrent operations
- **Batch Operations**: Combine multiple queries
- **Smart Sampling**: Adaptive sampling based on data volume
- **Query Planning**: Optimize NRQL before execution

### 3. Resource Management

- **Connection Pooling**: Reuse HTTP/gRPC connections
- **Memory Management**: Bounded queues and buffers
- **CPU Optimization**: Profile-guided optimization
- **I/O Optimization**: Async operations where possible

## Scalability Design

### 1. Horizontal Scaling

```
                    Load Balancer
                         │
        ┌────────────────┼────────────────┐
        ↓                ↓                ↓
   MCP Server 1    MCP Server 2    MCP Server N
        ↓                ↓                ↓
        └────────────────┼────────────────┘
                         │
                 Discovery Engine
                    (Stateless)
```

### 2. Deployment Patterns

#### Container Architecture
```yaml
Services:
  - mcp-server (scaled horizontally)
  - discovery-engine (scaled horizontally)
  - intelligence-engine (scaled horizontally)
  
Data Stores:
  - postgresql (primary-replica setup)
  - redis (clustered mode)
  
Load Balancing:
  - Application load balancer
  - Service mesh for internal communication
```

### 3. Auto-scaling Policies

- **CPU-based**: Scale at 70% CPU utilization
- **Memory-based**: Scale at 80% memory usage
- **Request-based**: Scale based on request queue depth
- **Custom metrics**: Scale based on NRDB query latency

## Future Architecture Considerations

### 1. Multi-Region Deployment
- Active-active configuration
- Data replication strategies
- Edge caching with CDN

### 2. Event-Driven Architecture
- Apache Kafka for event streaming
- Event sourcing for audit trail
- CQRS for read/write separation

### 3. Microservices Evolution
- Service mesh (Istio/Linkerd)
- API gateway pattern
- Distributed transaction management
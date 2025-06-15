# New Relic APM Setup Guide

This guide explains how to set up and use New Relic Application Performance Monitoring (APM) with the MCP Server for New Relic.

## Overview

The MCP Server for New Relic includes comprehensive APM instrumentation for both Go and Python services:

- **Go Services**: Discovery engine, API server, MCP server
- **Python Services**: Intelligence engine (pattern analysis, query generation, visualization)

## Prerequisites

1. New Relic account with APM access
2. New Relic API key and License key
3. `.env` file configured with New Relic credentials

## Configuration

### 1. Environment Variables

Copy `.env.example` to `.env` and configure the following New Relic settings:

```bash
# New Relic API Configuration
NEW_RELIC_API_KEY=your-api-key-here
NEW_RELIC_ACCOUNT_ID=your-account-id
NEW_RELIC_REGION=US  # or EU

# New Relic APM Configuration
NEW_RELIC_LICENSE_KEY=your-license-key-here
NEW_RELIC_APP_NAME=mcp-server-newrelic
NEW_RELIC_ENVIRONMENT=development
NEW_RELIC_MONITOR_MODE=true
NEW_RELIC_DISTRIBUTED_TRACING_ENABLED=true
NEW_RELIC_LOG_LEVEL=info
```

### 2. Application Names

By default, the following application names are used in New Relic:

- **Go Services**: `mcp-server-newrelic`
- **Python Services**: `intelligence-engine`

You can customize these by setting:
- `NEW_RELIC_APP_NAME` for Go services
- `NEW_RELIC_APP_NAME` for Python services (in their respective environments)

## Features

### 1. Automatic Transaction Tracing

All HTTP endpoints and gRPC methods are automatically instrumented:

#### Go Services
- REST API endpoints (`/api/v1/*`)
- MCP protocol handlers
- Discovery engine operations
- Database queries (NRDB)

#### Python Services
- gRPC service methods
- Pattern analysis operations
- Query generation
- Visualization recommendations

### 2. Custom Metrics

The following custom metrics are automatically recorded:

#### Discovery Metrics
- `Discovery/DiscoverSchemas/Duration` - Time to discover schemas
- `Discovery/FindRelationships/Duration` - Time to find relationships
- `Discovery/ProfileSchema/Duration` - Time to profile a schema

#### Intelligence Metrics
- `Intelligence/PatternAnalysis/Duration` - Pattern analysis time
- `Intelligence/PatternAnalysis/PatternsFound` - Number of patterns found
- `Intelligence/QueryGeneration/Duration` - Query generation time
- `Intelligence/QueryGeneration/Confidence` - Query confidence score
- `Intelligence/Visualization/Duration` - Visualization recommendation time
- `Intelligence/Visualization/RecommendationCount` - Number of recommendations

### 3. Custom Events

The following custom events are recorded:

#### Go Services
- `SchemaDiscovery` - Fired when schemas are discovered
  - `schemas_found`: Number of schemas found
  - `event_types`: Number of event types analyzed
  - `cache_key`: Cache key used

- `RelationshipDiscovery` - Fired when relationships are found
  - `schemas_analyzed`: Number of schemas analyzed
  - `relationships_found`: Number of relationships found

#### Python Services
- `PatternAnalysis` - Fired for pattern analysis requests
  - `data_size`: Size of data analyzed
  - `has_columns`: Whether columns were specified
  - `has_context`: Whether context was provided

- `QueryGeneration` - Fired for query generation
  - `query_length`: Length of natural language query
  - `has_context`: Whether context was provided

### 4. Error Tracking

All errors are automatically captured and sent to New Relic with:
- Stack traces
- Request context
- Custom attributes

### 5. Distributed Tracing

When distributed tracing is enabled, you can track requests across:
- API Gateway → Discovery Engine
- API Gateway → Intelligence Engine
- Discovery Engine → NRDB

## Monitoring

### 1. APM Dashboard

Access your APM data at:
- US: https://one.newrelic.com/apm
- EU: https://one.eu.newrelic.com/apm

### 2. Key Metrics to Monitor

#### Performance
- Response time by endpoint
- Throughput (requests per minute)
- Error rate
- Apdex score

#### Discovery Operations
- Schema discovery time
- Cache hit rate
- NRDB query performance
- Concurrent discovery operations

#### Intelligence Operations
- Pattern analysis duration
- Query generation confidence
- Visualization recommendation accuracy

### 3. Alerts

Consider setting up alerts for:
- Response time > 1 second
- Error rate > 1%
- Apdex score < 0.9
- Custom metric thresholds

## Development

### 1. Local Development

For local development, you can disable APM by setting:
```bash
NEW_RELIC_MONITOR_MODE=false
```

### 2. Debug Mode

Enable debug logging for APM:
```bash
NEW_RELIC_LOG_LEVEL=debug
```

### 3. Testing APM Integration

Test that APM is working:

```bash
# Check Go service
curl http://localhost:8080/api/v1/health

# Check Python service  
grpcurl -plaintext localhost:50051 intelligence.IntelligenceService/HealthCheck
```

Then verify transactions appear in New Relic within 1-2 minutes.

## Troubleshooting

### 1. No Data in New Relic

- Verify `NEW_RELIC_LICENSE_KEY` is correct
- Check `NEW_RELIC_MONITOR_MODE=true`
- Ensure network connectivity to New Relic
- Check application logs for APM initialization messages

### 2. Missing Transactions

- Verify APM is initialized before handling requests
- Check that middleware is properly configured
- Ensure distributed tracing headers are propagated

### 3. Performance Impact

APM typically adds < 3% overhead. If you see higher impact:
- Reduce custom metrics frequency
- Disable debug logging
- Consider sampling transactions

## Best Practices

1. **Use Environment-Specific App Names**
   ```bash
   NEW_RELIC_APP_NAME=mcp-server-${ENVIRONMENT}
   ```

2. **Tag Deployments**
   Use New Relic deployment markers when deploying:
   ```bash
   curl -X POST "https://api.newrelic.com/v2/applications/${APP_ID}/deployments.json" \
     -H "X-Api-Key:${NEW_RELIC_API_KEY}" \
     -H "Content-Type: application/json" \
     -d '{"deployment": {"revision": "v1.2.3"}}'
   ```

3. **Monitor Business Metrics**
   Add custom attributes for business context:
   - Account ID
   - Feature flags
   - User segments

4. **Use Transaction Naming**
   Ensure transactions have meaningful names that group similar operations

5. **Leverage Custom Dashboards**
   Create dashboards specific to your use cases combining:
   - APM metrics
   - Custom events
   - NRDB queries

## Integration with Other New Relic Products

### 1. New Relic Logs

Configure log forwarding to correlate logs with APM traces:
```yaml
logging:
  newrelic:
    enabled: true
    license_key: ${NEW_RELIC_LICENSE_KEY}
```

### 2. New Relic Infrastructure

Monitor the underlying infrastructure:
- Container metrics
- Host metrics  
- Process metrics

### 3. New Relic Browser

If building a web UI, add Browser monitoring for end-to-end visibility.

## Security

- Never commit `.env` files with real credentials
- Use environment-specific license keys
- Rotate keys periodically
- Consider using New Relic's high security mode for sensitive environments

## Support

For issues related to:
- **APM Setup**: Check New Relic documentation
- **Application Integration**: See our GitHub issues
- **Performance**: Review custom metrics and traces
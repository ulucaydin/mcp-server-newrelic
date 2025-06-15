# New Relic UDS TypeScript Client

Official TypeScript client library for the New Relic Unified Data Service (UDS) API.

## Installation

```bash
npm install @newrelic/uds-client
# or
yarn add @newrelic/uds-client
```

## Quick Start

```typescript
import { UDSClient } from '@newrelic/uds-client';

// Create a client instance
const client = new UDSClient({
  baseURL: 'https://api.newrelic.com/uds/v1',
  apiKey: 'your-api-key'
});

// Check API health
const health = await client.health();
console.log('API Status:', health.status);

// List schemas
const schemas = await client.discovery.listSchemas({
  eventType: 'Transaction',
  minRecordCount: 1000
});
```

## Configuration

The client accepts the following configuration options:

```typescript
interface ClientConfig {
  baseURL?: string;      // API base URL (default: http://localhost:8080/api/v1)
  apiKey?: string;       // API authentication key
  timeout?: number;      // Request timeout in ms (default: 30000)
  retryMax?: number;     // Maximum retry attempts (default: 3)
  retryWait?: number;    // Base retry wait time in ms (default: 1000)
  userAgent?: string;    // Custom user agent string
}
```

## Services

### Discovery Service

Discover and analyze data schemas:

```typescript
// List all schemas
const schemas = await client.discovery.listSchemas();

// Get specific schema
const schema = await client.discovery.getSchema('Transaction');

// Analyze schema quality
const quality = await client.discovery.analyzeQuality('Transaction');

// Compare schemas
const comparison = await client.discovery.compareSchemas('Schema1', 'Schema2');

// Get recommendations
const recommendations = await client.discovery.getRecommendations();
```

### Patterns Service

Manage and execute query patterns:

```typescript
// Search patterns
const patterns = await client.patterns.search({
  query: 'error rate',
  category: 'monitoring'
});

// Create a pattern
const pattern = await client.patterns.create({
  name: 'Error Rate Pattern',
  description: 'Calculate error rate over time',
  query: 'SELECT rate(errors) FROM Transaction',
  category: 'monitoring',
  tags: ['errors', 'performance']
});

// Execute a pattern
const results = await client.patterns.execute(pattern.id, {
  timeRange: { from: '-1h', to: 'now' }
});
```

### Query Service

Execute and manage queries:

```typescript
// Execute a query
const response = await client.query.execute({
  query: 'SELECT * FROM Transaction WHERE duration > 100',
  timeRange: {
    from: '2024-01-01T00:00:00Z',
    to: '2024-12-31T23:59:59Z'
  },
  options: {
    maxResults: 1000
  }
});

// Validate query syntax
const validation = await client.query.validate('SELECT * FROM Transaction');

// Get query suggestions
const suggestions = await client.query.suggest('SEL', {
  cursorPosition: 3
});

// Format a query
const formatted = await client.query.format('select*from Transaction');

// Get query history
const history = await client.query.getHistory({
  limit: 10,
  timeRange: { from: '-7d', to: 'now' }
});
```

### Dashboard Service

Create and manage dashboards:

```typescript
// List dashboards
const dashboards = await client.dashboard.list({
  search: 'production',
  tags: ['monitoring']
});

// Create a dashboard
const dashboard = await client.dashboard.create({
  name: 'Production Monitoring',
  description: 'Key metrics for production environment',
  widgets: [{
    type: 'line-chart',
    title: 'Response Time',
    query: 'SELECT avg(duration) FROM Transaction TIMESERIES',
    visualization: {
      type: 'line',
      options: { showLegend: true }
    }
  }]
});

// Clone a dashboard
const cloned = await client.dashboard.clone(dashboard.id, 'Production Copy');

// Export/Import dashboards
const exported = await client.dashboard.export(dashboard.id, 'json');
const imported = await client.dashboard.import(exported, 'json');
```

## Error Handling

The client provides typed error responses:

```typescript
try {
  const schema = await client.discovery.getSchema('NonExistent');
} catch (error) {
  if (error.statusCode === 404) {
    console.error('Schema not found:', error.message);
  } else {
    console.error('API Error:', error);
  }
}
```

## Retry Logic

The client includes built-in retry logic with exponential backoff:

```typescript
const client = new UDSClient({
  retryMax: 5,        // Retry up to 5 times
  retryWait: 1000     // Start with 1 second delay
});
```

Retries occur on:
- Network errors
- 408 Request Timeout
- 429 Too Many Requests
- 502 Bad Gateway
- 503 Service Unavailable
- 504 Gateway Timeout

## Advanced Usage

### Custom Requests

Make custom API requests:

```typescript
const customData = await client.request({
  method: 'GET',
  url: '/custom/endpoint',
  params: { filter: 'active' }
});
```

### Update API Key

Change the API key at runtime:

```typescript
client.setApiKey('new-api-key');
```

### TypeScript Support

The library is written in TypeScript and provides full type definitions:

```typescript
import { Schema, Pattern, QueryResponse } from '@newrelic/uds-client';

function processSchema(schema: Schema): void {
  console.log(`Schema ${schema.name} has ${schema.attributes.length} attributes`);
}
```

## Testing

The library includes comprehensive test coverage. To run tests:

```bash
npm test
npm run test:watch  # Watch mode
npm run coverage    # Generate coverage report
```

## Development

```bash
# Install dependencies
npm install

# Build the library
npm run build

# Run linter
npm run lint

# Run tests
npm test
```

## License

Apache License 2.0
# New Relic UDS Python Client

Modern, async-first Python client library for the New Relic Unified Data Service (UDS) API.

## Features

- **Async and Sync Support**: Both async and sync clients for maximum flexibility
- **Type Safety**: Full type hints with Pydantic models
- **Automatic Retry**: Built-in retry logic with exponential backoff
- **Comprehensive Services**: Discovery, Patterns, Query, and Dashboard APIs
- **Python 3.8+**: Support for modern Python versions

## Installation

```bash
pip install newrelic-uds
```

## Quick Start

### Async Client

```python
import asyncio
from newrelic_uds import AsyncUDSClient, ClientConfig

async def main():
    # Create client with configuration
    config = ClientConfig(
        base_url="https://api.newrelic.com/uds/v1",
        api_key="your-api-key"
    )
    
    async with AsyncUDSClient(config) as client:
        # Check API health
        health = await client.health()
        print(f"API Status: {health.status}")
        
        # List schemas
        schemas = await client.discovery.list_schemas()
        for schema in schemas.schemas:
            print(f"Schema: {schema.name}, Records: {schema.record_count}")

asyncio.run(main())
```

### Sync Client

```python
from newrelic_uds import SyncUDSClient, ClientConfig

# Create client
client = SyncUDSClient(ClientConfig(
    base_url="https://api.newrelic.com/uds/v1",
    api_key="your-api-key"
))

# Check API health
health = client.health()
print(f"API Status: {health.status}")

# List schemas
schemas = client.discovery.list_schemas()
for schema in schemas.schemas:
    print(f"Schema: {schema.name}")
```

## Configuration

The client accepts various configuration options:

```python
from newrelic_uds import ClientConfig

config = ClientConfig(
    base_url="https://api.newrelic.com/uds/v1",  # API base URL
    api_key="your-api-key",                       # API authentication key
    timeout=30.0,                                 # Request timeout in seconds
    max_retries=3,                                # Maximum retry attempts
    retry_wait=1.0,                               # Base retry wait time
    retry_max_wait=30.0,                          # Maximum retry wait time
    user_agent="my-app/1.0.0"                     # Custom user agent
)
```

## Services

### Discovery Service

Discover and analyze data schemas:

```python
from newrelic_uds import AsyncUDSClient, ListSchemasOptions

async with AsyncUDSClient() as client:
    # List schemas with filtering
    options = ListSchemasOptions(
        event_type="Transaction",
        min_record_count=1000,
        include_metadata=True
    )
    schemas = await client.discovery.list_schemas(options)
    
    # Get specific schema
    schema = await client.discovery.get_schema("Transaction")
    
    # Analyze schema quality
    quality = await client.discovery.analyze_quality("Transaction")
    print(f"Quality Score: {quality.overall_score}")
    
    # Compare schemas
    comparison = await client.discovery.compare_schemas("Schema1", "Schema2")
    
    # Get recommendations
    recommendations = await client.discovery.get_recommendations("Transaction")
```

### Patterns Service

Manage and execute query patterns:

```python
from newrelic_uds import AsyncUDSClient, SearchPatternsOptions

async with AsyncUDSClient() as client:
    # Search patterns
    options = SearchPatternsOptions(
        query="error rate",
        category="monitoring",
        tags=["errors", "performance"]
    )
    patterns = await client.patterns.search(options)
    
    # Create a pattern
    pattern = await client.patterns.create(
        name="Error Rate Pattern",
        description="Calculate error rate over time",
        query="SELECT rate(errors) FROM Transaction",
        category="monitoring",
        tags=["errors", "performance"]
    )
    
    # Execute a pattern
    results = await client.patterns.execute(
        pattern.id,
        variables={"timeRange": "1 hour"}
    )
    
    # Update a pattern
    updated = await client.patterns.update(
        pattern.id,
        description="Updated description"
    )
    
    # Delete a pattern
    await client.patterns.delete(pattern.id)
```

### Query Service

Execute and manage queries:

```python
from newrelic_uds import AsyncUDSClient, QueryRequest, TimeRange

async with AsyncUDSClient() as client:
    # Execute a query
    request = QueryRequest(
        query="SELECT * FROM Transaction WHERE duration > 100",
        time_range=TimeRange(
            from_time="2024-01-01T00:00:00Z",
            to_time="2024-12-31T23:59:59Z"
        ),
        options={"max_results": 1000}
    )
    response = await client.query.execute(request)
    
    # Validate query syntax
    validation = await client.query.validate("SELECT * FROM Transaction")
    if validation["valid"]:
        print("Query is valid")
    
    # Get query suggestions
    suggestions = await client.query.suggest("SEL", cursor_position=3)
    
    # Format a query
    formatted = await client.query.format("select*from Transaction")
    print(formatted["formatted"])
    
    # Get query history
    history = await client.query.get_history(limit=10)
    
    # Export query results
    csv_data = await client.query.export("query-id", format="csv")
```

### Dashboard Service

Create and manage dashboards:

```python
from newrelic_uds import AsyncUDSClient, ListDashboardsOptions

async with AsyncUDSClient() as client:
    # List dashboards
    options = ListDashboardsOptions(
        search="production",
        tags=["monitoring"]
    )
    dashboards = await client.dashboard.list(options)
    
    # Create a dashboard
    dashboard = await client.dashboard.create(
        name="Production Monitoring",
        widgets=[{
            "id": "widget-1",
            "type": "line-chart",
            "title": "Response Time",
            "query": "SELECT avg(duration) FROM Transaction TIMESERIES",
            "visualization": {
                "type": "line",
                "options": {"showLegend": True}
            }
        }],
        description="Key production metrics"
    )
    
    # Clone a dashboard
    cloned = await client.dashboard.clone(dashboard.id, "Production Copy")
    
    # Export/Import dashboards
    exported = await client.dashboard.export(dashboard.id, format="json")
    imported = await client.dashboard.import_dashboard(exported, format="json")
    
    # Render a widget
    widget_data = await client.dashboard.render_widget(
        dashboard.id,
        "widget-1",
        variables={"timeRange": "1 hour"}
    )
```

## Error Handling

The client provides typed error responses:

```python
from newrelic_uds import AsyncUDSClient, APIError

async with AsyncUDSClient() as client:
    try:
        schema = await client.discovery.get_schema("NonExistent")
    except APIError as e:
        print(f"Error: {e.error}")
        print(f"Message: {e.message}")
        print(f"Status Code: {e.status_code}")
        print(f"Details: {e.details}")
```

## Retry Configuration

Configure retry behavior for resilience:

```python
from newrelic_uds import ClientConfig

config = ClientConfig(
    max_retries=5,           # Retry up to 5 times
    retry_wait=2.0,          # Start with 2 second delay
    retry_max_wait=60.0      # Cap at 60 seconds
)

# The client will automatically retry on:
# - Network errors
# - Timeout errors
# - HTTP 429 (Rate Limit)
# - HTTP 502, 503, 504 (Server errors)
```

## Advanced Usage

### Custom Requests

Make custom API requests not covered by the service methods:

```python
async with AsyncUDSClient() as client:
    # Custom GET request
    data = await client.get("/custom/endpoint", params={"filter": "active"})
    
    # Custom POST request
    result = await client.post("/custom/endpoint", json={"data": "value"})
```

### Update API Key

Change the API key at runtime:

```python
client = AsyncUDSClient()
client.set_api_key("new-api-key")
```

### Type Safety

All models are fully typed with Pydantic:

```python
from newrelic_uds import Schema, Pattern, QueryResponse

def process_schema(schema: Schema) -> None:
    print(f"Schema {schema.name} has {len(schema.attributes)} attributes")
    print(f"Quality score: {schema.quality.overall_score}")

def analyze_pattern(pattern: Pattern) -> None:
    print(f"Pattern {pattern.name} in category {pattern.category}")
    if pattern.tags:
        print(f"Tags: {', '.join(pattern.tags)}")
```

## Testing

The library includes comprehensive test coverage:

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=newrelic_uds

# Run specific test file
pytest tests/test_client.py

# Run async tests only
pytest -k "async"
```

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Format code
black src tests

# Sort imports
isort src tests

# Type checking
mypy src

# Linting
flake8 src tests

# Build documentation
cd docs && make html
```

## License

Apache License 2.0
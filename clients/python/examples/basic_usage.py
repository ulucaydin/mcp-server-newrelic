#!/usr/bin/env python3
"""Basic usage example for the New Relic UDS Python client."""

import asyncio
from datetime import datetime, timedelta

from newrelic_uds import (
    AsyncUDSClient,
    ClientConfig,
    ListSchemasOptions,
    QueryRequest,
    TimeRange,
)


async def main():
    """Demonstrate basic client usage."""
    
    # Configure the client
    config = ClientConfig(
        base_url="http://localhost:8080/api/v1",
        api_key="your-api-key",
        timeout=30.0,
    )
    
    # Use async context manager for automatic cleanup
    async with AsyncUDSClient(config) as client:
        print("=== UDS Python Client Demo ===\n")
        
        # 1. Check API health
        print("1. Checking API health...")
        try:
            health = await client.health()
            print(f"   Status: {health.status}")
            print(f"   Version: {health.version}")
            print(f"   Uptime: {health.uptime}\n")
        except Exception as e:
            print(f"   Error: {e}\n")
        
        # 2. List schemas
        print("2. Listing schemas...")
        try:
            options = ListSchemasOptions(
                event_type="Transaction",
                min_record_count=1000,
                max_schemas=5,
                include_metadata=True,
            )
            schemas = await client.discovery.list_schemas(options)
            
            print(f"   Found {len(schemas.schemas)} schemas:")
            for schema in schemas.schemas:
                print(f"   - {schema.name}: {schema.record_count:,} records")
                print(f"     Quality score: {schema.quality.overall_score:.2f}")
            
            if schemas.metadata:
                print(f"   Execution time: {schemas.metadata.execution_time}\n")
        except Exception as e:
            print(f"   Error: {e}\n")
        
        # 3. Get specific schema details
        print("3. Getting schema details...")
        try:
            schema = await client.discovery.get_schema("Transaction")
            print(f"   Schema: {schema.name}")
            print(f"   Attributes: {len(schema.attributes)}")
            print(f"   First 5 attributes:")
            for attr in schema.attributes[:5]:
                print(f"   - {attr.name} ({attr.data_type})")
            print()
        except Exception as e:
            print(f"   Error: {e}\n")
        
        # 4. Search for patterns
        print("4. Searching patterns...")
        try:
            patterns = await client.patterns.search()
            print(f"   Found {patterns.total} patterns")
            for pattern in patterns.patterns[:3]:
                print(f"   - {pattern.name} ({pattern.category})")
                if pattern.tags:
                    print(f"     Tags: {', '.join(pattern.tags)}")
            print()
        except Exception as e:
            print(f"   Error: {e}\n")
        
        # 5. Execute a query
        print("5. Executing a query...")
        try:
            # Calculate time range for last 24 hours
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=24)
            
            request = QueryRequest(
                query="SELECT count(*) FROM Transaction WHERE duration > 100",
                time_range=TimeRange(
                    from_time=start_time.isoformat() + "Z",
                    to_time=end_time.isoformat() + "Z",
                ),
                options={"max_results": 10},
            )
            
            response = await client.query.execute(request)
            print(f"   Query executed successfully")
            print(f"   Results: {len(response.results)} result set(s)")
            
            if response.metadata:
                print(f"   Execution time: {response.metadata.execution_time}")
            print()
        except Exception as e:
            print(f"   Error: {e}\n")
        
        # 6. List dashboards
        print("6. Listing dashboards...")
        try:
            dashboards = await client.dashboard.list()
            print(f"   Found {dashboards.total} dashboards")
            for dashboard in dashboards.dashboards[:3]:
                print(f"   - {dashboard.name}")
                print(f"     Widgets: {len(dashboard.widgets)}")
            print()
        except Exception as e:
            print(f"   Error: {e}\n")
        
        print("=== Demo Complete ===")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
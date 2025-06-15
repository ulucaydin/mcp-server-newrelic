#!/usr/bin/env python3
"""Synchronous client usage example."""

from newrelic_uds import SyncUDSClient, ClientConfig, APIError


def main():
    """Demonstrate sync client usage."""
    
    # Configure the client
    config = ClientConfig(
        base_url="http://localhost:8080/api/v1",
        api_key="your-api-key",
    )
    
    # Create sync client
    with SyncUDSClient(config) as client:
        print("=== Sync Client Example ===\n")
        
        # Check health
        try:
            health = client.health()
            print(f"API Status: {health.status}")
        except APIError as e:
            print(f"API Error: {e.message} ({e.status_code})")
        except Exception as e:
            print(f"Error: {e}")
        
        # List schemas
        try:
            schemas = client.discovery.list_schemas()
            print(f"\nFound {len(schemas.schemas)} schemas:")
            
            for schema in schemas.schemas[:5]:
                print(f"- {schema.name}: {schema.record_count:,} records")
        except Exception as e:
            print(f"Error listing schemas: {e}")
        
        # Get recommendations
        try:
            recommendations = client.discovery.get_recommendations()
            if recommendations.get("recommendations"):
                print("\nRecommendations:")
                for rec in recommendations["recommendations"][:3]:
                    print(f"- {rec['type']}: {rec['description']}")
        except Exception as e:
            print(f"Error getting recommendations: {e}")


if __name__ == "__main__":
    main()
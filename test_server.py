#!/usr/bin/env python3
"""
Test script for New Relic MCP Server
"""

import asyncio
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def test_basic_functionality():
    """Test basic server functionality"""
    from main import create_app
    
    print("=== New Relic MCP Server Test ===\n")
    
    try:
        # Create the application
        print("Creating MCP application...")
        app = await create_app()
        print(f"✓ Application created: {app.name} v{app.version}")
        
        # Test account info
        print("\n--- Testing Account Info ---")
        from features.common import CommonPlugin
        services = app._services  # Access internal services for testing
        
        # List available tools
        print(f"\n✓ Registered {len(app._tools)} tools:")
        for tool_name in sorted(app._tools.keys()):
            print(f"  - {tool_name}")
        
        # List available resources
        print(f"\n✓ Registered {len(app._resources)} resources:")
        for resource_uri in sorted(app._resources.keys()):
            print(f"  - {resource_uri}")
        
        # Test health check
        print("\n--- Testing Health Check ---")
        health_tool = app._tools.get("get_health_status")
        if health_tool:
            handler = health_tool["handler"]
            health_result = await handler()
            print(f"✓ Health Status: {health_result['status']}")
            print(f"  Uptime: {health_result['uptime_seconds']:.1f}s")
            for check in health_result['checks']:
                status_icon = "✓" if check['status'] == 'healthy' else "✗"
                print(f"  {status_icon} {check['name']}: {check['status']}")
        
        # Test session info
        print("\n--- Testing Session Info ---")
        session_tool = app._tools.get("get_session_info")
        if session_tool:
            handler = session_tool["handler"]
            session_result = await handler()
            print(f"✓ Active Sessions: {session_result['active_sessions']}")
            print(f"  Current Account: {session_result['current_account']}")
            print(f"  Account ID: {session_result['account_id']}")
        
        # Test NRQL query (if account configured)
        account_id = services.get("account_id")
        if account_id:
            print("\n--- Testing NRQL Query ---")
            nrql_tool = app._tools.get("run_nrql_query")
            if nrql_tool:
                handler = nrql_tool["handler"]
                nrql = "SELECT count(*) FROM Transaction SINCE 1 hour ago"
                print(f"  Query: {nrql}")
                try:
                    result = await handler(nrql=nrql)
                    result_data = json.loads(result)
                    if "actor" in result_data:
                        print("  ✓ Query executed successfully")
                    else:
                        print("  ✗ Query failed:", result_data.get("errors"))
                except Exception as e:
                    print(f"  ✗ Query error: {e}")
        else:
            print("\n⚠ No account configured - skipping API tests")
        
        # Show audit statistics
        print("\n--- Audit Statistics ---")
        audit_logger = services.get("audit_logger")
        if audit_logger:
            stats = audit_logger.get_statistics()
            print(f"✓ Total Events: {stats['total_events']}")
            print(f"  Active Sessions: {stats['active_sessions']}")
            print(f"  Events/minute: {stats['events_per_minute']}")
            if stats['events_by_type']:
                print("  Event Types:")
                for event_type, count in stats['events_by_type'].items():
                    print(f"    - {event_type}: {count}")
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


async def test_transport_modes():
    """Test different transport modes"""
    print("\n=== Testing Transport Modes ===\n")
    
    transports = ["stdio", "http", "multi"]
    
    for transport in transports:
        print(f"\n--- Testing {transport.upper()} Transport ---")
        
        # Set transport mode
        os.environ["MCP_TRANSPORT"] = transport
        
        if transport in ["http", "multi"]:
            os.environ["HTTP_HOST"] = "127.0.0.1"
            os.environ["HTTP_PORT"] = "3000"
        
        try:
            from main import create_app
            app = await create_app()
            print(f"✓ {transport.upper()} transport configured successfully")
            
            if transport in ["http", "multi"]:
                print(f"  HTTP endpoint: http://127.0.0.1:3000")
                print(f"  SSE endpoint: http://127.0.0.1:3000/mcp/v1/sse")
                print(f"  Health check: http://127.0.0.1:3000/health")
            
        except Exception as e:
            print(f"✗ {transport.upper()} transport failed: {e}")
    
    # Reset to default
    os.environ["MCP_TRANSPORT"] = "stdio"


async def main():
    """Run all tests"""
    # Test basic functionality
    success = await test_basic_functionality()
    
    if success:
        # Test transport modes
        await test_transport_modes()
    
    print("\n=== Test Complete ===")


if __name__ == "__main__":
    # Check if API key is configured
    if not os.getenv("NEW_RELIC_API_KEY"):
        print("⚠️  Warning: NEW_RELIC_API_KEY not set")
        print("   Some tests will be skipped")
        print("   Set it with: export NEW_RELIC_API_KEY=your-key-here\n")
    
    # Run tests
    asyncio.run(main())
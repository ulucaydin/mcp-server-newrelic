#!/usr/bin/env python3
"""
Legacy server.py - Compatibility wrapper that redirects to main.py

This file exists for backward compatibility. The main server implementation
is now in main.py with the new architecture.
"""

import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import create_app

# For fastmcp compatibility, expose the mcp instance
mcp = None

async def _init_mcp():
    global mcp
    mcp = await create_app()
    return mcp

# Create the MCP instance when imported
mcp = asyncio.run(_init_mcp())

if __name__ == "__main__":
    print("\n--- New Relic MCP Server ---")
    print("Note: server.py is now a compatibility wrapper.")
    print("The main implementation is in main.py")
    print("\nTo run the server, use one of:")
    print("  python main.py")
    print("  fastmcp run server.py:mcp")
    print("\nEnsure NEW_RELIC_API_KEY is set in your environment.")
    
    # Run the main server
    from main import main
    asyncio.run(main())
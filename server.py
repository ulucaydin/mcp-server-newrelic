# server.py
import os
from fastmcp import FastMCP

# Import feature modules
from features import common, entities, apm, synthetics, alerts

# --- FastMCP Server Initialization ---
# Dependencies are defined here, but execution relies on fastmcp CLI handling them
# unless run directly with `python server.py` (not recommended for this setup).
mcp = FastMCP(
    "New Relic NerdGraph MCP Server",
    description="Provides tools and resources to interact with the New Relic NerdGraph API via MCP.",
    dependencies=["requests"] # Core dependency needed by client.py
)

# --- Register Features ---
# Call the register function from each feature module
print("Registering common features...")
common.register(mcp)
print("Registering entity features...")
entities.register(mcp)
print("Registering APM features...")
apm.register(mcp)
print("Registering Synthetics features...")
synthetics.register(mcp)
print("Registering Alerts features...")
alerts.register(mcp)

print("Feature registration complete.")

# --- Main execution block (for info and potential direct run debugging) ---
if __name__ == "__main__":
    # This block is primarily for informational purposes when the script is run directly.
    # The recommended way to run is: `fastmcp run server.py:mcp`
    # Direct execution (`python server.py`) does not automatically handle dependencies
    # listed in the FastMCP constructor.
    print("\n--- New Relic MCP Server ---")
    # Check for required config (already checked in config.py, but good to double-check here)
    try:
        import config
        if not config.API_KEY:
             print("ERROR: NEW_RELIC_API_KEY environment variable is not set.")
        if not config.ACCOUNT_ID:
            print("WARNING: NEW_RELIC_ACCOUNT_ID environment variable is not set. Some features require it.")
    except ImportError:
         print("ERROR: Could not import config.py")
    except Exception as e:
         print(f"ERROR loading configuration: {e}")


    print("\nThis script defines the MCP server instance.")
    print("To run the server with dependency management, use the command:")
    print("  fastmcp run server.py:mcp")
    print("\nEnsure NEW_RELIC_API_KEY and NEW_RELIC_ACCOUNT_ID are set in your environment.")

    # You could potentially add code here to start the server directly using uvicorn
    # for development/debugging, but `fastmcp run` is the intended method.
    # Example (requires `pip install uvicorn`):
    # import uvicorn
    # print("\nAttempting to start server directly with uvicorn (for debugging)...")
    # try:
    #     uvicorn.run(mcp.app, host="127.0.0.1", port=8000) # mcp.app exposes the ASGI app
    # except Exception as e:
    #     print(f"Failed to start uvicorn: {e}") 
#!/usr/bin/env python3
"""
New Relic MCP Server - Main Application Entry Point

This server provides Model Context Protocol (MCP) access to New Relic's
observability platform, enabling AI assistants to query metrics, entities,
alerts, and more.
"""

import asyncio
import logging
import os
import sys
import time
from typing import Dict, Any, List, Optional

from fastmcp import FastMCP

# Core imports
from core.account_manager import AccountManager
from core.nerdgraph_client import NerdGraphClient
from core.entity_definitions import EntityDefinitionsCache
from core.session_manager import SessionManager
from core.plugin_loader import PluginLoader
from core.plugin_manager import EnhancedPluginManager
from core.health import initialize_health_monitor, get_health_monitor, HealthStatus
from core.cache import get_cache
from core.audit import initialize_audit_logger, get_audit_logger, AuditEventType, AuditEvent

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def create_app() -> FastMCP:
    """Create and configure the MCP application
    
    Returns:
        Configured FastMCP application instance
    """
    
    # Initialize FastMCP with metadata
    app = FastMCP(
        name="newrelic-mcp",
        version="1.0.0",
        description="Access New Relic platform data through Model Context Protocol"
    )
    
    # Add instructions for AI assistants
    app.instructions = """
    You have access to New Relic observability data through this MCP server.
    Available capabilities include:
    - Query application performance metrics (APM)
    - Search and inspect entities (services, hosts, etc.)
    - View alerts and incidents
    - Run NRQL queries for custom analysis
    - Explore entity relationships and dependencies
    
    Always specify clear time ranges when querying metrics. Default is last hour.
    Entity names are case-sensitive. Use search if unsure of exact name.
    """
    
    logger.info("Initializing New Relic MCP Server...")
    
    # Initialize core services
    logger.info("Loading account configuration...")
    account_manager = AccountManager()
    
    logger.info("Initializing session manager...")
    session_manager = SessionManager()
    
    logger.info("Loading entity definitions cache...")
    entity_defs = EntityDefinitionsCache()
    
    # Initialize cache
    cache = get_cache()
    
    # Get current account credentials
    try:
        creds = account_manager.get_current_credentials()
        logger.info(f"Using account: {account_manager.current_account or 'default'}")
    except ValueError as e:
        logger.error(f"Failed to load account credentials: {e}")
        logger.error("Please set NEW_RELIC_API_KEY environment variable or configure accounts")
        sys.exit(1)
    
    # Initialize NerdGraph client
    logger.info("Connecting to New Relic NerdGraph API...")
    nerdgraph = NerdGraphClient(
        api_key=creds["api_key"],
        endpoint=creds.get("nerdgraph_url", "https://api.newrelic.com/graphql")
    )
    
    # Verify connection
    try:
        test_result = await nerdgraph.query("{ actor { user { email } } }")
        if test_result and "actor" in test_result:
            logger.info("Successfully connected to New Relic API")
        else:
            logger.warning("Connected but could not verify user")
    except Exception as e:
        logger.error(f"Failed to connect to New Relic API: {e}")
        logger.error("Please check your API key and network connection")
        await nerdgraph.close()
        sys.exit(1)
    
    # Initialize health monitoring
    logger.info("Initializing health monitoring...")
    health_monitor = initialize_health_monitor(nerdgraph_client=nerdgraph, cache=cache)
    
    # Initialize audit logging
    logger.info("Initializing audit logging...")
    audit_logger = initialize_audit_logger()
    
    # Service registry for plugins
    services = {
        "account_manager": account_manager,
        "session_manager": session_manager,
        "nerdgraph": nerdgraph,
        "entity_definitions": entity_defs,
        "account_id": creds.get("account_id"),
        "cache": cache,
        "health_monitor": health_monitor,
        "audit_logger": audit_logger
    }
    
    # Register global tools
    await register_global_tools(app, services)
    
    # Load all feature plugins
    logger.info("Loading feature plugins...")
    
    # Use enhanced plugin manager if available
    use_enhanced = os.getenv("USE_ENHANCED_PLUGINS", "false").lower() == "true"
    
    if use_enhanced:
        logger.info("Using enhanced plugin manager with dependency resolution")
        plugin_manager = EnhancedPluginManager(app)
        plugin_manager.load_all(services)
        
        # Store plugin manager in services for access by tools
        services["plugin_manager"] = plugin_manager
    else:
        # Use legacy plugin loader
        PluginLoader.load_all(app, services)
    
    # Log server start event
    await audit_logger.log_event(AuditEvent(
        timestamp=time.time(),
        event_type=AuditEventType.SERVER_START,
        user_id=None,
        session_id=None,
        account_id=creds.get("account_id"),
        tool_name=None,
        resource_uri=None,
        details={
            "transport": os.getenv("MCP_TRANSPORT", "stdio"),
            "plugins_loaded": len(plugin_manager.plugins) if use_enhanced else len(PluginLoader.loaded_plugins)
        },
        success=True
    ))
    
    # Register cleanup handler
    async def cleanup():
        logger.info("Shutting down...")
        
        # Log server stop event
        await audit_logger.log_event(AuditEvent(
            timestamp=time.time(),
            event_type=AuditEventType.SERVER_STOP,
            user_id=None,
            session_id=None,
            account_id=creds.get("account_id"),
            tool_name=None,
            resource_uri=None,
            details={},
            success=True
        ))
        
        await nerdgraph.close()
    
    app.on_cleanup(cleanup)
    
    logger.info("New Relic MCP Server initialized successfully")
    return app


async def register_global_tools(app: FastMCP, services: Dict[str, Any]):
    """Register global/system tools
    
    Args:
        app: FastMCP application instance
        services: Service registry
    """
    account_manager = services["account_manager"]
    session_manager = services["session_manager"]
    
    @app.tool()
    async def switch_account(account_name: str) -> Dict[str, Any]:
        """Switch to a different New Relic account
        
        Args:
            account_name: Name of the account to switch to
            
        Returns:
            Status and new account information
        """
        try:
            creds = account_manager.switch_account(account_name)
            
            # Update NerdGraph client
            old_client = services["nerdgraph"]
            services["nerdgraph"] = NerdGraphClient(
                api_key=creds["api_key"],
                endpoint=creds["nerdgraph_url"]
            )
            services["account_id"] = creds.get("account_id")
            
            # Close old client
            await old_client.close()
            
            # Clear session caches since we switched accounts
            session_manager.clear_all_sessions()
            
            logger.info(f"Switched to account: {account_name}")
            
            return {
                "status": "success",
                "account": account_name,
                "account_id": creds.get("account_id"),
                "region": creds.get("region", "US")
            }
        except Exception as e:
            logger.error(f"Failed to switch account: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    @app.tool()
    async def list_accounts() -> List[Dict[str, Any]]:
        """List available New Relic accounts
        
        Returns:
            List of configured accounts
        """
        accounts = account_manager.list_accounts()
        return [
            {
                "name": name,
                "account_id": info.get("account_id"),
                "region": info.get("region", "US"),
                "is_current": info.get("is_current", False)
            }
            for name, info in accounts.items()
        ]
    
    @app.tool()
    async def get_session_info() -> Dict[str, Any]:
        """Get current session information
        
        Returns:
            Session context and statistics
        """
        # For now, return a simple status
        # In future, this could integrate with MCP session tracking
        return {
            "active_sessions": len(session_manager.sessions),
            "current_account": account_manager.current_account,
            "account_id": services.get("account_id")
        }
    
    @app.resource("newrelic://help/tools")
    async def list_available_tools() -> str:
        """List all available tools and their descriptions"""
        tools_info = []
        
        # This would ideally introspect registered tools
        # For now, return a helpful message
        return """
# Available New Relic MCP Tools

## Global Tools
- `switch_account(name)` - Switch between configured New Relic accounts
- `list_accounts()` - List all configured accounts
- `get_session_info()` - Get current session information

## Entity Tools
- `search_entities(query, types, tags)` - Search for entities
- `get_entity_details(guid)` - Get detailed entity information
- `get_entity_golden_signals(guid)` - Get key metrics for an entity

## Metrics Tools  
- `run_nrql_query(nrql, account_id)` - Execute NRQL queries
- `query_nerdgraph(query, variables)` - Run raw GraphQL queries

## APM Tools
- `list_apm_applications(account_id)` - List APM applications

## Alerts Tools
- `list_alert_policies(account_id)` - List alert policies
- `list_open_incidents(account_id, priority)` - List open incidents
- `acknowledge_alert_incident(incident_id)` - Acknowledge an incident

## Synthetics Tools
- `list_synthetics_monitors(account_id)` - List synthetic monitors
- `create_simple_browser_monitor(...)` - Create a browser monitor

Use any tool by name with appropriate parameters.
"""
    
    @app.tool()
    async def list_plugins() -> List[Dict[str, Any]]:
        """List all loaded plugins with their status
        
        Returns:
            List of plugin information
        """
        plugin_manager = services.get("plugin_manager")
        
        if plugin_manager:
            # Enhanced plugin manager
            return plugin_manager.get_plugin_info()
        else:
            # Legacy plugin loader
            plugins = []
            for plugin_cls in PluginLoader.loaded_plugins:
                plugins.append({
                    "name": plugin_cls.__name__,
                    "description": plugin_cls.__doc__ or "No description",
                    "state": "loaded",
                    "version": getattr(plugin_cls, "version", "unknown")
                })
            return plugins
    
    @app.tool()
    async def get_plugin_dependencies() -> Dict[str, List[str]]:
        """Get plugin dependency graph
        
        Returns:
            Dictionary mapping plugin names to their dependencies
        """
        plugin_manager = services.get("plugin_manager")
        
        if plugin_manager:
            return plugin_manager.get_dependency_graph()
        else:
            return {"message": "Enhanced plugin manager not enabled"}
    
    @app.tool()
    async def get_health_status() -> Dict[str, Any]:
        """Get server health status and metrics
        
        Returns:
            Health check results and server metrics
        """
        monitor = get_health_monitor()
        if not monitor:
            return {
                "status": "error",
                "message": "Health monitor not initialized"
            }
        
        return await monitor.run_checks()
    
    @app.resource("newrelic://health/metrics")
    async def get_prometheus_metrics() -> str:
        """Get Prometheus-formatted metrics"""
        monitor = get_health_monitor()
        if not monitor:
            return "# Health monitor not initialized\n"
        
        return monitor.get_metrics().decode('utf-8')


async def main():
    """Main entry point"""
    try:
        # Create the application
        app = await create_app()
        
        # Start server with appropriate transport
        transport = os.getenv("MCP_TRANSPORT", "stdio")
        
        if transport == "stdio":
            # Run in STDIO mode for Claude Desktop
            logger.info("Starting in STDIO mode...")
            # FastMCP's run() method handles the appropriate transport
            app.run()
        else:
            # Use multi-transport server for other modes
            from transports import create_transport_adapter
            adapted_app = create_transport_adapter(app)
            adapted_app.run()
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Handle Windows event loop policy
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Run the server
    asyncio.run(main())
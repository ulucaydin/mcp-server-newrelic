#!/usr/bin/env python3
"""
MCP Server for New Relic
Implements Model Context Protocol tools for New Relic operations
"""

import os
import sys
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import mcp.types as types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import our tools
from tools.nrql_query import NRQLQueryTool
from tools.dashboard_discovery import DashboardDiscoveryTool
from tools.alert_builder import AlertBuilderTool
from tools.template_generator import TemplateGeneratorTool
from tools.bulk_operations import BulkOperationsTool


class NewRelicMCPServer:
    """MCP Server for New Relic operations"""
    
    def __init__(self):
        self.server = Server("mcp-server-newrelic")
        
        # Initialize tools
        self.nrql_tool = NRQLQueryTool()
        self.dashboard_tool = DashboardDiscoveryTool()
        self.alert_tool = AlertBuilderTool()
        self.template_tool = TemplateGeneratorTool()
        self.bulk_tool = BulkOperationsTool()
        
        # Register handlers
        self._register_handlers()
        
    def _register_handlers(self):
        """Register all MCP handlers"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """List all available tools"""
            return [
                # NRQL Query Assistant
                types.Tool(
                    name="query_check",
                    description="Validate and analyze NRQL queries for correctness, performance, and cost",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The NRQL query to validate"
                            },
                            "estimate_cost": {
                                "type": "boolean",
                                "description": "Whether to estimate query cost",
                                "default": True
                            }
                        },
                        "required": ["query"]
                    }
                ),
                types.Tool(
                    name="query_nrdb",
                    description="Execute an NRQL query against New Relic",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The NRQL query to execute"
                            },
                            "timeout": {
                                "type": "integer",
                                "description": "Query timeout in seconds",
                                "default": 30
                            }
                        },
                        "required": ["query"]
                    }
                ),
                
                # Dashboard Discovery
                types.Tool(
                    name="find_usage",
                    description="Find dashboards that use specific metrics or attributes",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "metric": {
                                "type": "string",
                                "description": "The metric or attribute name to search for"
                            },
                            "refresh": {
                                "type": "boolean",
                                "description": "Whether to refresh the cache",
                                "default": False
                            },
                            "format": {
                                "type": "string",
                                "description": "Output format (json or csv)",
                                "default": "json",
                                "enum": ["json", "csv"]
                            }
                        },
                        "required": ["metric"]
                    }
                ),
                
                # Template Generator
                types.Tool(
                    name="generate_dashboard",
                    description="Generate a dashboard from a template",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "template": {
                                "type": "string",
                                "description": "Template name (golden-signals, sli-slo, infrastructure)",
                                "enum": ["golden-signals", "sli-slo", "infrastructure"]
                            },
                            "service": {
                                "type": "string",
                                "description": "Service name for the dashboard"
                            },
                            "time_range": {
                                "type": "string",
                                "description": "Default time range for queries",
                                "default": "1 hour ago"
                            },
                            "dry_run": {
                                "type": "boolean",
                                "description": "Preview without creating",
                                "default": False
                            }
                        },
                        "required": ["template", "service"]
                    }
                ),
                
                # Alert Builder
                types.Tool(
                    name="create_alert",
                    description="Create an intelligent alert condition",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "metric": {
                                "type": "string",
                                "description": "The metric to alert on"
                            },
                            "service": {
                                "type": "string",
                                "description": "The service name"
                            },
                            "sensitivity": {
                                "type": "string",
                                "description": "Alert sensitivity (low, medium, high)",
                                "enum": ["low", "medium", "high"],
                                "default": "medium"
                            },
                            "runbook_url": {
                                "type": "string",
                                "description": "Optional runbook URL"
                            },
                            "dry_run": {
                                "type": "boolean",
                                "description": "Preview without creating",
                                "default": False
                            }
                        },
                        "required": ["metric", "service"]
                    }
                ),
                
                # Bulk Operations
                types.Tool(
                    name="bulk_update",
                    description="Perform bulk updates on dashboards or alerts",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "description": "Operation type",
                                "enum": ["find_replace", "tag", "normalize_time", "delete"]
                            },
                            "target": {
                                "type": "string",
                                "description": "Target type (dashboards or alerts)",
                                "enum": ["dashboards", "alerts"]
                            },
                            "filter": {
                                "type": "object",
                                "description": "Filter criteria"
                            },
                            "updates": {
                                "type": "object",
                                "description": "Updates to apply"
                            },
                            "dry_run": {
                                "type": "boolean",
                                "description": "Preview without applying",
                                "default": True
                            }
                        },
                        "required": ["operation", "target"]
                    }
                )
            ]
            
        @self.server.call_tool()
        async def handle_call_tool(
            name: str, 
            arguments: Dict[str, Any]
        ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            """Handle tool calls"""
            
            try:
                logger.info(f"Tool called: {name} with args: {arguments}")
                
                if name == "query_check":
                    result = await self.nrql_tool.validate_query(
                        arguments["query"],
                        arguments.get("estimate_cost", True)
                    )
                elif name == "query_nrdb":
                    result = await self.nrql_tool.execute_query(
                        arguments["query"],
                        arguments.get("timeout", 30)
                    )
                elif name == "find_usage":
                    result = await self.dashboard_tool.find_usage(
                        arguments["metric"],
                        arguments.get("refresh", False),
                        arguments.get("format", "json")
                    )
                elif name == "generate_dashboard":
                    result = await self.template_tool.generate_dashboard(
                        arguments["template"],
                        arguments["service"],
                        arguments.get("time_range", "1 hour ago"),
                        arguments.get("dry_run", False)
                    )
                elif name == "create_alert":
                    result = await self.alert_tool.create_alert(
                        arguments["metric"],
                        arguments["service"],
                        arguments.get("sensitivity", "medium"),
                        arguments.get("runbook_url"),
                        arguments.get("dry_run", False)
                    )
                elif name == "bulk_update":
                    result = await self.bulk_tool.bulk_update(
                        arguments["operation"],
                        arguments["target"],
                        arguments.get("filter", {}),
                        arguments.get("updates", {}),
                        arguments.get("dry_run", True)
                    )
                else:
                    result = {"error": f"Unknown tool: {name}"}
                    
                # Format result
                if isinstance(result, str):
                    return [types.TextContent(type="text", text=result)]
                else:
                    return [types.TextContent(
                        type="text", 
                        text=json.dumps(result, indent=2)
                    )]
                    
            except Exception as e:
                logger.error(f"Error in tool {name}: {e}")
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "error": str(e),
                        "tool": name,
                        "arguments": arguments
                    }, indent=2)
                )]
                
    async def run(self):
        """Run the MCP server"""
        logger.info("Starting New Relic MCP Server...")
        
        # Run the server using stdio transport
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="mcp-server-newrelic",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(tools_changed=True),
                        experimental_capabilities={},
                    )
                )
            )


async def main():
    """Main entry point"""
    server = NewRelicMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
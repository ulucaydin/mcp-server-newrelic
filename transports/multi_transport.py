"""
Multi-transport server supporting STDIO, HTTP, and hybrid modes
"""

from fastmcp import FastMCP
import asyncio
import os
import logging
from typing import Optional

from .stdio_transport import create_stdio_server
from .http_transport import create_http_server

logger = logging.getLogger(__name__)


class MultiTransportServer:
    """Server that supports multiple transport protocols"""
    
    def __init__(self, app: FastMCP):
        """
        Initialize multi-transport server
        
        Args:
            app: FastMCP application instance
        """
        self.app = app
        self.stdio_server = None
        self.http_server = None
        self.servers = []
    
    async def start_stdio(self):
        """Start STDIO transport for Claude/Copilot"""
        logger.info("Starting STDIO transport...")
        try:
            self.stdio_server = create_stdio_server(self.app)
            stdio_task = asyncio.create_task(self.stdio_server.run())
            self.servers.append(stdio_task)
            logger.info("STDIO transport started")
        except Exception as e:
            logger.error(f"Failed to start STDIO transport: {e}")
            raise
    
    async def start_http(self, host: str = "127.0.0.1", port: int = 3000):
        """Start HTTP transport for web/automation
        
        Args:
            host: Host to bind to
            port: Port to listen on
        """
        logger.info(f"Starting HTTP transport on {host}:{port}...")
        try:
            self.http_server = create_http_server(self.app, host, port)
            http_task = asyncio.create_task(self.http_server.run())
            self.servers.append(http_task)
            logger.info(f"HTTP transport started on http://{host}:{port}")
        except Exception as e:
            logger.error(f"Failed to start HTTP transport: {e}")
            raise
    
    async def run(self, transport_mode: str = "stdio", **kwargs):
        """Run server with specified transport mode
        
        Args:
            transport_mode: Transport mode ('stdio', 'http', or 'multi')
            **kwargs: Additional arguments for transport configuration
        """
        logger.info(f"Starting server in {transport_mode} mode")
        
        try:
            if transport_mode == "stdio":
                await self.start_stdio()
            elif transport_mode == "http":
                host = kwargs.get('host', '127.0.0.1')
                port = kwargs.get('port', 3000)
                await self.start_http(host, port)
            elif transport_mode == "multi":
                # Start both transports
                await self.start_stdio()
                host = kwargs.get('host', '127.0.0.1')
                port = kwargs.get('port', 3000)
                await self.start_http(host, port)
            else:
                raise ValueError(f"Unknown transport mode: {transport_mode}")
            
            # Wait for all servers
            if self.servers:
                await asyncio.gather(*self.servers)
                
        except asyncio.CancelledError:
            logger.info("Server shutdown requested")
            # Cancel all server tasks
            for task in self.servers:
                task.cancel()
            await asyncio.gather(*self.servers, return_exceptions=True)
        except Exception as e:
            logger.error(f"Server error: {e}", exc_info=True)
            raise
    
    @classmethod
    async def from_env(cls, app: FastMCP):
        """Auto-detect transport from environment and run server
        
        Args:
            app: FastMCP application instance
        """
        transport = os.getenv("MCP_TRANSPORT", "stdio")
        server = cls(app)
        
        # Parse transport configuration
        if transport == "stdio":
            await server.run("stdio")
        elif transport == "http":
            host = os.getenv("HTTP_HOST", "127.0.0.1")
            port = int(os.getenv("HTTP_PORT", "3000"))
            await server.run("http", host=host, port=port)
        elif transport == "multi":
            host = os.getenv("HTTP_HOST", "127.0.0.1")
            port = int(os.getenv("HTTP_PORT", "3000"))
            await server.run("multi", host=host, port=port)
        else:
            raise ValueError(
                f"Unknown transport: {transport}. "
                "Set MCP_TRANSPORT to 'stdio', 'http', or 'multi'"
            )


def create_transport_adapter(app: FastMCP):
    """Create a transport adapter that makes FastMCP work with custom transports
    
    This is needed because FastMCP expects to handle its own server lifecycle,
    but we want to use custom transports.
    """
    
    class TransportAdapter:
        def __init__(self, app):
            self.app = app
            # Store original run method
            self._original_run = app.run
            
        def run(self):
            """Override FastMCP's run method to use our transports"""
            # Get transport mode from environment
            transport = os.getenv("MCP_TRANSPORT", "stdio")
            
            if transport == "stdio":
                # Use FastMCP's built-in STDIO support
                self._original_run()
            else:
                # Use our custom transports
                asyncio.run(MultiTransportServer.from_env(self.app))
    
    # Create adapter and replace app's run method
    adapter = TransportAdapter(app)
    app.run = adapter.run
    
    return app
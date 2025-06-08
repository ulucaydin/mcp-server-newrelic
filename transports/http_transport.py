"""
HTTP/SSE transport implementation for MCP
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable
from aiohttp import web
import aiohttp_cors
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class HttpTransport:
    """HTTP transport with Server-Sent Events (SSE) support"""
    
    def __init__(self, request_handler: Callable, host: str = "127.0.0.1", port: int = 3000):
        """
        Initialize HTTP transport
        
        Args:
            request_handler: Async function to handle incoming requests
            host: Host to bind to
            port: Port to listen on
        """
        self.request_handler = request_handler
        self.host = host
        self.port = port
        self.app = web.Application()
        self.sessions: Dict[str, web.StreamResponse] = {}
        self._setup_routes()
        self._setup_cors()
        self.runner = None
    
    def _setup_routes(self):
        """Setup HTTP routes"""
        self.app.router.add_post('/mcp/v1/message', self._handle_message)
        self.app.router.add_get('/mcp/v1/sse', self._handle_sse)
        self.app.router.add_get('/health', self._handle_health)
        self.app.router.add_get('/mcp/v1/info', self._handle_info)
    
    def _setup_cors(self):
        """Setup CORS for browser clients"""
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # Configure CORS on all routes
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    async def start(self):
        """Start the HTTP server"""
        logger.info(f"Starting HTTP transport on {self.host}:{self.port}")
        
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        site = web.TCPSite(self.runner, self.host, self.port)
        await site.start()
        
        logger.info(f"HTTP transport listening on http://{self.host}:{self.port}")
    
    async def stop(self):
        """Stop the HTTP server"""
        logger.info("Stopping HTTP transport")
        
        # Close all SSE connections
        for session_id, response in list(self.sessions.items()):
            await response.write_eof()
            del self.sessions[session_id]
        
        if self.runner:
            await self.runner.cleanup()
        
        logger.info("HTTP transport stopped")
    
    async def _handle_message(self, request: web.Request) -> web.Response:
        """Handle POST /mcp/v1/message - synchronous request/response"""
        try:
            # Parse JSON-RPC request
            data = await request.json()
            
            # Add session ID if provided
            session_id = request.headers.get('X-Session-ID')
            if session_id:
                data['_session_id'] = session_id
            
            # Handle request
            response = await self.request_handler(data)
            
            # Return response
            return web.json_response(response)
            
        except json.JSONDecodeError:
            return web.json_response({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": "Parse error"
                },
                "id": None
            }, status=400)
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            return web.json_response({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": str(e)
                },
                "id": data.get("id") if 'data' in locals() else None
            }, status=500)
    
    async def _handle_sse(self, request: web.Request) -> web.StreamResponse:
        """Handle GET /mcp/v1/sse - Server-Sent Events for async communication"""
        session_id = str(uuid.uuid4())
        
        # Create SSE response
        response = web.StreamResponse()
        response.headers['Content-Type'] = 'text/event-stream'
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['Connection'] = 'keep-alive'
        response.headers['X-Session-ID'] = session_id
        
        await response.prepare(request)
        
        # Store session
        self.sessions[session_id] = response
        
        # Send initial connection event
        await self._send_sse_event(response, "connected", {
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        try:
            # Keep connection alive
            while True:
                # Send heartbeat every 30 seconds
                await asyncio.sleep(30)
                await self._send_sse_event(response, "heartbeat", {
                    "timestamp": datetime.utcnow().isoformat()
                })
                
        except ConnectionResetError:
            logger.info(f"SSE client disconnected: {session_id}")
        finally:
            # Clean up session
            if session_id in self.sessions:
                del self.sessions[session_id]
        
        return response
    
    async def _handle_health(self, request: web.Request) -> web.Response:
        """Handle GET /health - health check endpoint"""
        from core.health import get_health_monitor
        
        monitor = get_health_monitor()
        if monitor:
            health_data = await monitor.run_checks()
            status_code = 200 if health_data["status"] == "healthy" else 503
            return web.json_response(health_data, status=status_code)
        else:
            return web.json_response({
                "status": "unknown",
                "message": "Health monitor not initialized"
            })
    
    async def _handle_info(self, request: web.Request) -> web.Response:
        """Handle GET /mcp/v1/info - server information"""
        return web.json_response({
            "name": "New Relic MCP Server",
            "version": "1.0.0",
            "transport": "http",
            "capabilities": {
                "tools": True,
                "resources": True,
                "prompts": True,
                "sse": True,
                "batch": True
            }
        })
    
    async def _send_sse_event(self, response: web.StreamResponse, 
                             event_type: str, data: Any):
        """Send an SSE event"""
        try:
            # Format SSE message
            message = f"event: {event_type}\n"
            message += f"data: {json.dumps(data)}\n\n"
            
            # Send to client
            await response.write(message.encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error sending SSE event: {e}")
    
    async def send_notification(self, session_id: str, method: str, 
                               params: Optional[Dict[str, Any]] = None):
        """Send a notification to a specific session via SSE"""
        if session_id in self.sessions:
            response = self.sessions[session_id]
            
            notification = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params or {}
            }
            
            await self._send_sse_event(response, "notification", notification)
    
    async def broadcast_notification(self, method: str, 
                                   params: Optional[Dict[str, Any]] = None):
        """Broadcast a notification to all connected SSE clients"""
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        
        # Send to all sessions
        for session_id, response in list(self.sessions.items()):
            try:
                await self._send_sse_event(response, "notification", notification)
            except Exception as e:
                logger.error(f"Error broadcasting to {session_id}: {e}")
                # Remove failed session
                del self.sessions[session_id]


class HttpServer:
    """MCP server using HTTP transport"""
    
    def __init__(self, mcp_app, host: str = "127.0.0.1", port: int = 3000):
        """
        Initialize HTTP server
        
        Args:
            mcp_app: FastMCP application instance
            host: Host to bind to
            port: Port to listen on
        """
        self.app = mcp_app
        self.transport = HttpTransport(self._handle_request, host, port)
        self.methods = {}
        self._setup_methods()
    
    def _setup_methods(self):
        """Setup JSON-RPC method handlers"""
        # Standard MCP methods
        self.methods["initialize"] = self._handle_initialize
        self.methods["tools/list"] = self._handle_list_tools
        self.methods["tools/call"] = self._handle_call_tool
        self.methods["resources/list"] = self._handle_list_resources
        self.methods["resources/read"] = self._handle_read_resource
        self.methods["prompts/list"] = self._handle_list_prompts
        self.methods["prompts/get"] = self._handle_get_prompt
        self.methods["batch"] = self._handle_batch
    
    async def _handle_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming JSON-RPC request"""
        # Extract session ID if present
        session_id = message.pop('_session_id', None)
        
        if "method" not in message:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32600,
                    "message": "Invalid request"
                },
                "id": message.get("id")
            }
        
        method = message["method"]
        params = message.get("params", {})
        msg_id = message.get("id")
        
        # Find handler
        handler = self.methods.get(method)
        
        if not handler:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                },
                "id": msg_id
            }
        
        try:
            # Add session context if available
            if session_id:
                params['_session_id'] = session_id
            
            # Call handler
            result = await handler(params)
            
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": msg_id
            }
            
        except Exception as e:
            logger.error(f"Error handling {method}: {e}", exc_info=True)
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": str(e)
                },
                "id": msg_id
            }
    
    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request"""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": True,
                "resources": True,
                "prompts": True,
                "logging": True
            },
            "serverInfo": {
                "name": self.app.name,
                "version": getattr(self.app, 'version', '1.0.0'),
                "transport": "http"
            }
        }
    
    async def _handle_list_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request"""
        tools = []
        
        # Get tools from FastMCP app
        for tool_name, tool_info in self.app._tools.items():
            tools.append({
                "name": tool_name,
                "description": tool_info.get("description", ""),
                "inputSchema": tool_info.get("inputSchema", {})
            })
        
        return {"tools": tools}
    
    async def _handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request"""
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        
        # Remove internal params
        tool_args.pop('_session_id', None)
        
        if not tool_name:
            raise ValueError("Tool name is required")
        
        # Get tool from app
        tool = self.app._tools.get(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")
        
        # Call tool function
        handler = tool.get("handler")
        if not handler:
            raise ValueError(f"Tool has no handler: {tool_name}")
        
        result = await handler(**tool_args)
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": str(result)
                }
            ]
        }
    
    async def _handle_list_resources(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/list request"""
        resources = []
        
        # Get resources from FastMCP app
        for uri_template, resource_info in self.app._resources.items():
            resources.append({
                "uri": uri_template,
                "name": resource_info.get("name", uri_template),
                "description": resource_info.get("description", ""),
                "mimeType": resource_info.get("mimeType", "application/json")
            })
        
        return {"resources": resources}
    
    async def _handle_read_resource(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/read request"""
        uri = params.get("uri")
        
        if not uri:
            raise ValueError("Resource URI is required")
        
        # Find matching resource
        for uri_template, resource_info in self.app._resources.items():
            # Simple template matching
            if self._match_uri_template(uri, uri_template):
                handler = resource_info.get("handler")
                if handler:
                    # Extract parameters from URI
                    uri_params = self._extract_uri_params(uri, uri_template)
                    result = await handler(**uri_params)
                    
                    return {
                        "contents": [
                            {
                                "uri": uri,
                                "mimeType": resource_info.get("mimeType", "application/json"),
                                "text": str(result)
                            }
                        ]
                    }
        
        raise ValueError(f"Resource not found: {uri}")
    
    async def _handle_list_prompts(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/list request"""
        prompts = []
        
        # Get prompts from FastMCP app
        for prompt_name, prompt_info in self.app._prompts.items():
            prompts.append({
                "name": prompt_name,
                "description": prompt_info.get("description", ""),
                "arguments": prompt_info.get("arguments", [])
            })
        
        return {"prompts": prompts}
    
    async def _handle_get_prompt(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/get request"""
        prompt_name = params.get("name")
        prompt_args = params.get("arguments", {})
        
        if not prompt_name:
            raise ValueError("Prompt name is required")
        
        # Get prompt from app
        prompt = self.app._prompts.get(prompt_name)
        if not prompt:
            raise ValueError(f"Prompt not found: {prompt_name}")
        
        # Generate prompt
        handler = prompt.get("handler")
        if not handler:
            raise ValueError(f"Prompt has no handler: {prompt_name}")
        
        result = await handler(**prompt_args)
        
        return {
            "description": prompt.get("description", ""),
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": str(result)
                    }
                }
            ]
        }
    
    async def _handle_batch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle batch requests"""
        requests = params.get("requests", [])
        
        if not isinstance(requests, list):
            raise ValueError("Batch requests must be a list")
        
        # Process each request
        responses = []
        for req in requests:
            response = await self._handle_request(req)
            responses.append(response)
        
        return {"responses": responses}
    
    def _match_uri_template(self, uri: str, template: str) -> bool:
        """Simple URI template matching"""
        import re
        pattern = template.replace("{", "(?P<").replace("}", ">[^/]+)")
        return bool(re.match(f"^{pattern}$", uri))
    
    def _extract_uri_params(self, uri: str, template: str) -> Dict[str, str]:
        """Extract parameters from URI based on template"""
        import re
        pattern = template.replace("{", "(?P<").replace("}", ">[^/]+)")
        match = re.match(f"^{pattern}$", uri)
        return match.groupdict() if match else {}
    
    async def run(self):
        """Run the HTTP server"""
        logger.info("Starting HTTP MCP server")
        
        await self.transport.start()
        
        try:
            # Keep server running
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            logger.info("Server shutdown requested")
        finally:
            await self.transport.stop()


def create_http_server(app, host: str = "127.0.0.1", port: int = 3000):
    """Create HTTP server for FastMCP app"""
    return HttpServer(app, host, port)
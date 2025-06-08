"""
STDIO transport implementation for MCP
"""

import asyncio
import json
import sys
import logging
from typing import Optional, Dict, Any, Callable
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class StdioTransport:
    """Standard Input/Output transport for MCP communication"""
    
    def __init__(self, request_handler: Callable):
        """
        Initialize STDIO transport
        
        Args:
            request_handler: Async function to handle incoming requests
        """
        self.request_handler = request_handler
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self._running = False
        self._read_task = None
    
    async def start(self):
        """Start the STDIO transport"""
        logger.info("Starting STDIO transport")
        
        # Get event loop
        loop = asyncio.get_event_loop()
        
        # Create reader for stdin
        self.reader = asyncio.StreamReader(loop=loop)
        reader_protocol = asyncio.StreamReaderProtocol(self.reader)
        
        # Connect stdin to reader
        await loop.connect_read_pipe(lambda: reader_protocol, sys.stdin)
        
        # For stdout, we'll use direct writes
        self._running = True
        
        # Start reading messages
        self._read_task = asyncio.create_task(self._read_loop())
        
        logger.info("STDIO transport started")
    
    async def stop(self):
        """Stop the STDIO transport"""
        logger.info("Stopping STDIO transport")
        self._running = False
        
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
        
        logger.info("STDIO transport stopped")
    
    async def _read_loop(self):
        """Read messages from stdin"""
        while self._running:
            try:
                # Read line from stdin
                line = await self.reader.readline()
                
                if not line:
                    logger.info("EOF received, stopping")
                    break
                
                # Decode and parse JSON-RPC message
                try:
                    message = json.loads(line.decode('utf-8').strip())
                    
                    # Handle the message
                    response = await self.request_handler(message)
                    
                    # Send response if any
                    if response:
                        await self.send_message(response)
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32700,
                            "message": "Parse error"
                        },
                        "id": None
                    }
                    await self.send_message(error_response)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in read loop: {e}", exc_info=True)
    
    async def send_message(self, message: Dict[str, Any]):
        """Send a message to stdout"""
        try:
            # Serialize to JSON and add newline
            data = json.dumps(message) + '\n'
            
            # Write to stdout
            sys.stdout.write(data)
            sys.stdout.flush()
            
        except Exception as e:
            logger.error(f"Error sending message: {e}", exc_info=True)
    
    async def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None):
        """Send a notification (no response expected)"""
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        await self.send_message(message)
    
    @asynccontextmanager
    async def connect(self):
        """Context manager for connection lifecycle"""
        try:
            await self.start()
            yield self
        finally:
            await self.stop()


class StdioServer:
    """MCP server using STDIO transport"""
    
    def __init__(self, mcp_app):
        """
        Initialize STDIO server
        
        Args:
            mcp_app: FastMCP application instance
        """
        self.app = mcp_app
        self.transport = StdioTransport(self._handle_request)
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
        self.methods["logging/setLevel"] = self._handle_set_log_level
    
    async def _handle_request(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle incoming JSON-RPC request"""
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
        
        # Check if it's a notification (no id)
        is_notification = msg_id is None
        
        # Find handler
        handler = self.methods.get(method)
        
        if not handler:
            if not is_notification:
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    },
                    "id": msg_id
                }
            return None
        
        try:
            # Call handler
            result = await handler(params)
            
            # Return response if not a notification
            if not is_notification:
                return {
                    "jsonrpc": "2.0",
                    "result": result,
                    "id": msg_id
                }
                
        except Exception as e:
            logger.error(f"Error handling {method}: {e}", exc_info=True)
            if not is_notification:
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    },
                    "id": msg_id
                }
        
        return None
    
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
                "version": getattr(self.app, 'version', '1.0.0')
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
            # Simple template matching (enhance as needed)
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
    
    async def _handle_set_log_level(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle logging/setLevel request"""
        level = params.get("level", "info").upper()
        
        # Map to Python logging levels
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR
        }
        
        if level in level_map:
            logging.getLogger().setLevel(level_map[level])
            return {}
        else:
            raise ValueError(f"Invalid log level: {level}")
    
    def _match_uri_template(self, uri: str, template: str) -> bool:
        """Simple URI template matching"""
        # Convert template to regex pattern
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
        """Run the STDIO server"""
        logger.info("Starting STDIO MCP server")
        
        async with self.transport.connect():
            # Keep server running
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                logger.info("Server shutdown requested")


def create_stdio_server(app):
    """Create STDIO server for FastMCP app"""
    return StdioServer(app)
"""
MCP Client Manager

This module manages MCP client connections, including connection pooling,
lifecycle management, and transport abstraction.
"""

import asyncio
import json
import subprocess
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging
from contextlib import asynccontextmanager

from .types import MCPClient, ConnectionPool, MCPRequest, MCPResponse, MCPCapabilities, MCPTool, ToolParameter, ToolParameterType
from .config import TransportType
from ..telemetry import LoggerMixin


class StdioTransport:
    """Standard I/O transport for MCP communication"""

    def __init__(self, command: str, env: Optional[Dict[str, str]] = None, args: Optional[List[str]] = None):
        self.command = command
        self.env = env or {}
        self.args = args or []
        self.process: Optional[asyncio.subprocess.Process] = None
        self.logger = logging.getLogger(self.__class__.__name__)

    async def connect(self) -> None:
        """Start the subprocess and establish stdio connection"""
        try:
            # Prepare environment
            import os
            env = os.environ.copy()
            env.update(self.env)

            # Start subprocess
            cmd = self.command.split() + self.args
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )

            self.logger.info(f"Started subprocess: {self.command}")

        except Exception as e:
            self.logger.error(f"Failed to start subprocess: {e}")
            raise

    async def send(self, message: Dict[str, Any]) -> None:
        """Send a message via stdin"""
        if not self.process or not self.process.stdin:
            raise RuntimeError("Transport not connected")

        data = json.dumps(message).encode() + b'\n'
        self.process.stdin.write(data)
        await self.process.stdin.drain()

    async def receive(self) -> Dict[str, Any]:
        """Receive a message via stdout"""
        if not self.process or not self.process.stdout:
            raise RuntimeError("Transport not connected")

        line = await self.process.stdout.readline()
        if not line:
            raise ConnectionError("Connection closed")

        return json.loads(line.decode())

    async def close(self) -> None:
        """Close the transport connection"""
        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()

            self.process = None

    @property
    def connected(self) -> bool:
        """Check if transport is connected"""
        return self.process is not None and self.process.returncode is None


class SSETransport:
    """Server-Sent Events transport for MCP communication"""

    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None):
        self.url = url
        self.headers = headers or {}
        self.session: Optional[Any] = None  # Will use aiohttp
        self.logger = logging.getLogger(self.__class__.__name__)

    async def connect(self) -> None:
        """Establish SSE connection"""
        # TODO: Implement SSE transport using aiohttp
        raise NotImplementedError("SSE transport not yet implemented")

    async def send(self, message: Dict[str, Any]) -> None:
        """Send a message via SSE"""
        raise NotImplementedError("SSE transport not yet implemented")

    async def receive(self) -> Dict[str, Any]:
        """Receive a message via SSE"""
        raise NotImplementedError("SSE transport not yet implemented")

    async def close(self) -> None:
        """Close the SSE connection"""
        if self.session:
            await self.session.close()
            self.session = None

    @property
    def connected(self) -> bool:
        """Check if transport is connected"""
        return self.session is not None


class WebSocketTransport:
    """WebSocket transport for MCP communication"""

    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None):
        self.url = url
        self.headers = headers or {}
        self.websocket: Optional[Any] = None  # Will use aiohttp
        self.logger = logging.getLogger(self.__class__.__name__)

    async def connect(self) -> None:
        """Establish WebSocket connection"""
        # TODO: Implement WebSocket transport using aiohttp
        raise NotImplementedError("WebSocket transport not yet implemented")

    async def send(self, message: Dict[str, Any]) -> None:
        """Send a message via WebSocket"""
        raise NotImplementedError("WebSocket transport not yet implemented")

    async def receive(self) -> Dict[str, Any]:
        """Receive a message via WebSocket"""
        raise NotImplementedError("WebSocket transport not yet implemented")

    async def close(self) -> None:
        """Close the WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None

    @property
    def connected(self) -> bool:
        """Check if transport is connected"""
        return self.websocket is not None


class RealMCPClient(MCPClient):
    """
    Real implementation of MCP client with transport abstraction.

    This replaces the placeholder MCPClient from types.py
    """

    def __init__(self, server_id: str, transport: Any):
        super().__init__(server_id=server_id, transport_type=type(transport).__name__)
        self.transport = transport
        self.logger = logging.getLogger(f"MCPClient[{server_id}]")
        self._request_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._receiver_task: Optional[asyncio.Task] = None

    async def connect(self) -> None:
        """Connect to the MCP server"""
        await self.transport.connect()
        self.connected = True

        # Start receiver task
        self._receiver_task = asyncio.create_task(self._receive_loop())

        # Send initialization
        await self._send_request("initialize", {
            "protocolVersion": "1.0.0",
            "clientCapabilities": {
                "tools": True,
                "resources": True,
                "prompts": True
            }
        })

        self.logger.info(f"Connected to MCP server: {self.server_id}")

    async def disconnect(self) -> None:
        """Disconnect from the MCP server"""
        if self._receiver_task:
            self._receiver_task.cancel()
            try:
                await self._receiver_task
            except asyncio.CancelledError:
                pass

        await self.transport.close()
        self.connected = False
        self.logger.info(f"Disconnected from MCP server: {self.server_id}")

    async def _receive_loop(self) -> None:
        """Continuously receive messages from the transport"""
        try:
            while self.connected:
                message = await self.transport.receive()
                await self._handle_message(message)
        except Exception as e:
            self.logger.error(f"Receiver loop error: {e}")
            self.connected = False

    async def _handle_message(self, message: Dict[str, Any]) -> None:
        """Handle incoming messages"""
        if "id" in message:
            # Response to a request
            request_id = message["id"]
            if request_id in self._pending_requests:
                future = self._pending_requests.pop(request_id)
                if "error" in message:
                    future.set_exception(Exception(message["error"]))
                else:
                    future.set_result(message.get("result"))
        elif "method" in message:
            # Notification
            await self._handle_notification(message)

    async def _handle_notification(self, notification: Dict[str, Any]) -> None:
        """Handle server notifications"""
        method = notification["method"]
        params = notification.get("params", {})
        self.logger.debug(f"Received notification: {method}")
        # TODO: Handle specific notifications

    async def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Send a request and wait for response"""
        self._request_id += 1
        request_id = self._request_id

        request = MCPRequest(
            id=request_id,
            method=method,
            params=params or {}
        )

        # Create future for response
        future = asyncio.Future()
        self._pending_requests[request_id] = future

        # Send request
        await self.transport.send({
            "jsonrpc": request.jsonrpc,
            "id": request.id,
            "method": request.method,
            "params": request.params
        })

        # Wait for response
        try:
            result = await asyncio.wait_for(future, timeout=30)
            return result
        except asyncio.TimeoutError:
            self._pending_requests.pop(request_id, None)
            raise TimeoutError(f"Request timeout: {method}")

    async def list_tools(self) -> List[MCPTool]:
        """List available tools from the server"""
        try:
            result = await self._send_request("tools/list")
            tools = []

            for tool_data in result.get("tools", []):
                # Parse parameters
                parameters = []
                for param_data in tool_data.get("parameters", []):
                    param = ToolParameter(
                        name=param_data["name"],
                        type=ToolParameterType(param_data.get("type", "string")),
                        description=param_data.get("description", ""),
                        required=param_data.get("required", True),
                        default=param_data.get("default")
                    )
                    parameters.append(param)

                tool = MCPTool(
                    name=tool_data["name"],
                    description=tool_data.get("description", ""),
                    parameters=parameters,
                    returns=tool_data.get("returns"),
                    examples=tool_data.get("examples", []),
                    tags=tool_data.get("tags", [])
                )
                tools.append(tool)

            return tools

        except Exception as e:
            self.logger.error(f"Failed to list tools: {e}")
            return []

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool on the server"""
        try:
            result = await self._send_request("tools/execute", {
                "name": tool_name,
                "arguments": arguments
            })
            return result

        except Exception as e:
            self.logger.error(f"Failed to execute tool {tool_name}: {e}")
            raise

    async def get_capabilities(self) -> MCPCapabilities:
        """Get server capabilities"""
        try:
            result = await self._send_request("capabilities")
            return MCPCapabilities(
                tools=result.get("tools", True),
                resources=result.get("resources", False),
                prompts=result.get("prompts", False),
                sampling=result.get("sampling", False),
                logging=result.get("logging", True),
                custom_features=result.get("customFeatures", {})
            )
        except Exception as e:
            self.logger.error(f"Failed to get capabilities: {e}")
            return MCPCapabilities()


class MCPClientManager(LoggerMixin):
    """
    Manages MCP client connections with connection pooling and lifecycle management.
    """

    def __init__(self, max_connections: int = 10):
        """
        Initialize the client manager.

        Args:
            max_connections: Maximum number of concurrent connections
        """
        super().__init__()
        self.pool = ConnectionPool(max_connections=max_connections)
        self.transports: Dict[str, Any] = {}

    async def create_client(
        self,
        server_id: str,
        transport_type: TransportType,
        transport_config: Dict[str, Any]
    ) -> RealMCPClient:
        """
        Create an MCP client with specified transport.

        Args:
            server_id: Unique identifier for the server
            transport_type: Type of transport to use
            transport_config: Transport-specific configuration

        Returns:
            Connected MCP client
        """
        # Check if client exists in pool
        existing = self.pool.acquire(server_id)
        if existing and isinstance(existing, RealMCPClient):
            if existing.connected:
                self.logger.info(f"Reusing existing client for: {server_id}")
                return existing

        # Create transport
        if transport_type == TransportType.STDIO:
            transport = StdioTransport(
                command=transport_config["command"],
                env=transport_config.get("env"),
                args=transport_config.get("args")
            )
        elif transport_type == TransportType.SSE:
            transport = SSETransport(
                url=transport_config["url"],
                headers=transport_config.get("headers")
            )
        elif transport_type == TransportType.WEBSOCKET:
            transport = WebSocketTransport(
                url=transport_config["url"],
                headers=transport_config.get("headers")
            )
        else:
            raise ValueError(f"Unsupported transport type: {transport_type}")

        # Create and connect client
        client = RealMCPClient(server_id, transport)
        await client.connect()

        # Store in pool
        self.pool.connections[server_id] = client
        self.pool.active_count += 1
        self.transports[server_id] = transport

        self.logger.info(f"Created new MCP client for: {server_id}")
        return client

    async def get_client(self, server_id: str) -> Optional[RealMCPClient]:
        """
        Get an existing client from the pool.

        Args:
            server_id: Server identifier

        Returns:
            MCP client if exists, None otherwise
        """
        client = self.pool.acquire(server_id)
        if isinstance(client, RealMCPClient):
            return client
        return None

    async def close_client(self, server_id: str) -> None:
        """
        Close and remove a client.

        Args:
            server_id: Server identifier
        """
        client = await self.get_client(server_id)
        if client:
            await client.disconnect()
            self.pool.remove(server_id)
            if server_id in self.transports:
                del self.transports[server_id]

            self.logger.info(f"Closed MCP client: {server_id}")

    @asynccontextmanager
    async def client_session(
        self,
        server_id: str,
        transport_type: TransportType,
        transport_config: Dict[str, Any]
    ):
        """
        Context manager for MCP client sessions.

        Args:
            server_id: Server identifier
            transport_type: Transport type
            transport_config: Transport configuration

        Yields:
            Connected MCP client
        """
        client = await self.create_client(server_id, transport_type, transport_config)
        try:
            yield client
        finally:
            # Keep connection in pool for reuse
            self.pool.release(server_id, client)

    def cleanup(self) -> None:
        """Cleanup all connections"""
        for server_id in list(self.pool.connections.keys()):
            asyncio.create_task(self.close_client(server_id))

        self.logger.info("Cleaned up all MCP client connections")
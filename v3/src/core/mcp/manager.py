"""
MCP Manager - Central orchestrator for Model Context Protocol operations

This module provides the main entry point for MCP functionality, managing
server lifecycle, client connections, and tool execution.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta
import logging

from .config import MCPConfig, MCPServerConfig, get_mcp_config
from .client import MCPClientManager
from .supervisor import MCPServerSupervisor
from .types import (
    MCPServer, MCPConnection, MCPTool, MCPResource,
    MCPCapabilities, HealthStatus, ToolExecutionResult
)
from ..telemetry import LoggerMixin, get_correlation_id
from ..errors import SuntoryError


class MCPOperationError(SuntoryError):
    """Error during MCP operation"""
    pass


class MCPManager(LoggerMixin):
    """
    Central orchestrator for all MCP operations.

    Manages the lifecycle of MCP servers, maintains client connections,
    and provides a unified interface for tool execution.
    """

    def __init__(self, config: Optional[MCPConfig] = None):
        """
        Initialize the MCP Manager.

        Args:
            config: Optional MCP configuration. Uses default if not provided.
        """
        super().__init__()
        self.config = config or get_mcp_config()
        self.client_manager = MCPClientManager(max_connections=self.config.max_connections)
        self.server_supervisor = MCPServerSupervisor()

        self.initialized = False
        self.connected_servers: Dict[str, MCPConnection] = {}
        self.available_tools: Dict[str, MCPTool] = {}
        self.tool_to_server: Dict[str, str] = {}
        self.resources: Dict[str, MCPResource] = {}

        self.cache_enabled = self.config.cache_enabled
        self.cache: Dict[str, Any] = {}
        self.cache_timestamps: Dict[str, datetime] = {}

        self.operation_counts: Dict[str, int] = {}
        self.operation_times: Dict[str, List[float]] = {}

        self.logger.info(f"MCP Manager created with {len(self.config.servers)} configured servers")

    async def initialize(self) -> None:
        """
        Initialize the MCP subsystem.

        Starts configured servers and establishes connections.
        """
        if self.initialized:
            self.logger.warning("MCP Manager already initialized")
            return

        self.logger.info("Initializing MCP subsystem...")

        try:
            for server_config in self.config.servers:
                if server_config.auto_start:
                    await self._start_and_connect_server(server_config)

            await self._discover_tools()

            self.initialized = True
            self.logger.info(
                f"MCP subsystem initialized: {len(self.connected_servers)} servers, "
                f"{len(self.available_tools)} tools available"
            )

        except Exception as e:
            self.logger.error(f"Failed to initialize MCP subsystem: {e}")
            raise MCPOperationError(
                f"MCP initialization failed: {e}",
                recovery_suggestions=["Check server configurations", "Verify server binaries are installed"]
            )

    async def _start_and_connect_server(self, config: MCPServerConfig) -> None:
        """Start a server and establish connection"""
        try:
            self.logger.info(f"Starting MCP server: {config.name}")

            server = await self.server_supervisor.start_server(config)

            client = await self.client_manager.create_client(
                server_id=config.name,
                transport_type=config.transport,
                transport_config={
                    "command": config.command,
                    "url": config.url,
                    "env": config.env,
                    "args": config.args
                }
            )

            connection = MCPConnection(
                server_id=config.name,
                server=server,
                client=client,
                connected_at=datetime.utcnow(),
                capabilities=await client.get_capabilities() if hasattr(client, 'get_capabilities') else MCPCapabilities()
            )

            self.connected_servers[config.name] = connection
            self.logger.info(f"Successfully connected to MCP server: {config.name}")

        except Exception as e:
            self.logger.error(f"Failed to start/connect to server {config.name}: {e}")
            if config.restart_policy != "never":
                self.logger.info(f"Will retry based on restart policy: {config.restart_policy}")

    async def discover_servers(self) -> List[MCPServer]:
        """
        Discover available MCP servers.

        Returns:
            List of discovered MCP servers
        """
        discovered = []

        for config in self.config.servers:
            server = MCPServer(
                id=config.name,
                type=config.type,
                transport=config.transport,
                status="configured",
                config=config
            )
            discovered.append(server)

        # TODO: Add dynamic discovery mechanisms (mDNS, registry, etc.)

        self.logger.info(f"Discovered {len(discovered)} MCP servers")
        return discovered

    async def connect_server(self, server_name: str) -> MCPConnection:
        """
        Establish connection to an MCP server.

        Args:
            server_name: Name of the server to connect to

        Returns:
            MCP connection object
        """
        if server_name in self.connected_servers:
            self.logger.info(f"Already connected to server: {server_name}")
            return self.connected_servers[server_name]

        config = self.config.get_server_config(server_name)
        if not config:
            raise MCPOperationError(f"No configuration found for server: {server_name}")

        await self._start_and_connect_server(config)

        # Re-discover tools after new connection
        await self._discover_tools()

        return self.connected_servers[server_name]

    async def disconnect_server(self, server_name: str) -> None:
        """
        Disconnect from an MCP server.

        Args:
            server_name: Name of the server to disconnect from
        """
        if server_name not in self.connected_servers:
            self.logger.warning(f"Server not connected: {server_name}")
            return

        try:
            connection = self.connected_servers[server_name]

            await self.client_manager.close_client(server_name)
            await self.server_supervisor.stop_server(server_name)

            tools_to_remove = [
                tool_name for tool_name, server in self.tool_to_server.items()
                if server == server_name
            ]
            for tool_name in tools_to_remove:
                del self.available_tools[tool_name]
                del self.tool_to_server[tool_name]

            del self.connected_servers[server_name]

            self.logger.info(f"Disconnected from server: {server_name}")

        except Exception as e:
            self.logger.error(f"Error disconnecting from server {server_name}: {e}")
            raise MCPOperationError(f"Failed to disconnect from server: {e}")

    async def _discover_tools(self) -> None:
        """Discover tools from all connected servers"""
        self.available_tools.clear()
        self.tool_to_server.clear()

        for server_name, connection in self.connected_servers.items():
            try:
                tools = await connection.client.list_tools() if hasattr(connection.client, 'list_tools') else []

                for tool in tools:
                    # Use fully qualified name if there are conflicts
                    tool_name = tool.name
                    if tool_name in self.available_tools:
                        tool_name = f"{server_name}.{tool.name}"

                    self.available_tools[tool_name] = tool
                    self.tool_to_server[tool_name] = server_name

                self.logger.info(f"Discovered {len(tools)} tools from server: {server_name}")

            except Exception as e:
                self.logger.error(f"Failed to discover tools from {server_name}: {e}")

    async def list_tools(self, agent_name: Optional[str] = None) -> List[MCPTool]:
        """
        Get all available tools, optionally filtered by agent permissions.

        Args:
            agent_name: Optional agent name to filter tools by permissions

        Returns:
            List of available MCP tools
        """
        if not self.initialized:
            await self.initialize()

        tools = list(self.available_tools.values())

        if agent_name:
            allowed_servers = self.config.get_allowed_servers_for_agent(agent_name)
            tools = [
                tool for tool in tools
                if self.tool_to_server.get(tool.name, "") in allowed_servers
            ]

            # Further filter by specific allowed tools if configured
            permissions = self.config.get_agent_permissions(agent_name)
            if permissions and permissions.allowed_tools:
                tools = [
                    tool for tool in tools
                    if tool.name in permissions.allowed_tools
                ]

        return tools

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        agent_name: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> ToolExecutionResult:
        """
        Execute an MCP tool and return results.

        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments to pass to the tool
            agent_name: Optional agent name for permission checking
            timeout: Optional timeout in seconds

        Returns:
            Tool execution result
        """
        start_time = datetime.utcnow()
        correlation_id = get_correlation_id()

        try:
            if tool_name not in self.available_tools:
                # Try with server prefix
                available = [name for name in self.available_tools.keys() if name.endswith(f".{tool_name}")]
                if available:
                    tool_name = available[0]
                else:
                    raise MCPOperationError(f"Tool not found: {tool_name}")

            if agent_name:
                allowed_tools = await self.list_tools(agent_name)
                allowed_names = [t.name for t in allowed_tools]
                if tool_name not in allowed_names:
                    raise MCPOperationError(
                        f"Agent {agent_name} is not authorized to use tool: {tool_name}"
                    )

            server_name = self.tool_to_server[tool_name]
            if server_name not in self.connected_servers:
                await self.connect_server(server_name)

            connection = self.connected_servers[server_name]

            if self.config.audit_logging:
                self.logger.info(
                    f"MCP Tool Execution | Agent: {agent_name} | Tool: {tool_name} | "
                    f"Server: {server_name} | Correlation: {correlation_id}"
                )

            timeout = timeout or self.config.operation_timeout
            result = await asyncio.wait_for(
                connection.client.execute_tool(tool_name, arguments),
                timeout=timeout
            )

            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self._track_operation(tool_name, execution_time)

            return ToolExecutionResult(
                tool_name=tool_name,
                success=True,
                result=result,
                execution_time=execution_time,
                server=server_name
            )

        except asyncio.TimeoutError:
            self.logger.error(f"Tool execution timeout: {tool_name}")
            raise MCPOperationError(
                f"Tool execution timed out after {timeout} seconds",
                recovery_suggestions=["Increase timeout", "Check server responsiveness"]
            )

        except Exception as e:
            self.logger.error(f"Tool execution failed: {tool_name} - {e}")
            raise MCPOperationError(f"Tool execution failed: {e}")

    async def handle_resource(self, resource: MCPResource) -> Any:
        """
        Handle MCP resource requests.

        Args:
            resource: MCP resource to handle

        Returns:
            Resource data or result
        """
        # TODO: Implement resource handling
        # This could include file resources, database schemas, etc.
        raise NotImplementedError("Resource handling not yet implemented")

    async def health_check(self, server_name: Optional[str] = None) -> Dict[str, HealthStatus]:
        """
        Check health of MCP servers.

        Args:
            server_name: Optional specific server to check

        Returns:
            Dictionary of server health statuses
        """
        health_statuses = {}

        servers_to_check = [server_name] if server_name else list(self.connected_servers.keys())

        for name in servers_to_check:
            if name in self.connected_servers:
                status = await self.server_supervisor.health_check(name)
                health_statuses[name] = status
            else:
                health_statuses[name] = HealthStatus(
                    healthy=False,
                    status="disconnected",
                    message="Server not connected"
                )

        return health_statuses

    def _track_operation(self, tool_name: str, execution_time: float) -> None:
        """Track operation metrics"""
        if tool_name not in self.operation_counts:
            self.operation_counts[tool_name] = 0
            self.operation_times[tool_name] = []

        self.operation_counts[tool_name] += 1
        self.operation_times[tool_name].append(execution_time)

        # Keep only last 100 times for memory efficiency
        if len(self.operation_times[tool_name]) > 100:
            self.operation_times[tool_name] = self.operation_times[tool_name][-100:]

    def get_metrics(self) -> Dict[str, Any]:
        """Get MCP operation metrics"""
        metrics = {
            "connected_servers": len(self.connected_servers),
            "available_tools": len(self.available_tools),
            "operation_counts": dict(self.operation_counts),
            "average_execution_times": {}
        }

        for tool_name, times in self.operation_times.items():
            if times:
                metrics["average_execution_times"][tool_name] = sum(times) / len(times)

        return metrics

    async def shutdown(self) -> None:
        """Shutdown MCP subsystem gracefully"""
        self.logger.info("Shutting down MCP subsystem...")

        # Disconnect all servers
        for server_name in list(self.connected_servers.keys()):
            await self.disconnect_server(server_name)

        # Cleanup
        self.client_manager.cleanup()
        await self.server_supervisor.shutdown()

        self.initialized = False
        self.logger.info("MCP subsystem shutdown complete")


# Singleton instance
_mcp_manager_instance: Optional[MCPManager] = None


def get_mcp_manager() -> MCPManager:
    """Get the MCP Manager singleton"""
    global _mcp_manager_instance
    if _mcp_manager_instance is None:
        _mcp_manager_instance = MCPManager()
    return _mcp_manager_instance


def reset_mcp_manager():
    """Reset the MCP Manager singleton (mainly for testing)"""
    global _mcp_manager_instance
    if _mcp_manager_instance:
        asyncio.create_task(_mcp_manager_instance.shutdown())
    _mcp_manager_instance = None
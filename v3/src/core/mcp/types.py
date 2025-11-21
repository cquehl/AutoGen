"""
MCP Type Definitions

This module defines the core types and data structures used throughout
the MCP integration.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum


class ToolParameterType(str, Enum):
    """Types of tool parameters"""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"


@dataclass
class ToolParameter:
    """Definition of a tool parameter"""
    name: str
    type: ToolParameterType
    description: str
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    pattern: Optional[str] = None  # Regex pattern for strings


@dataclass
class MCPTool:
    """Represents an MCP tool"""
    name: str
    description: str
    parameters: List[ToolParameter] = field(default_factory=list)
    returns: Optional[str] = None  # Description of return value
    examples: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    deprecated: bool = False


@dataclass
class MCPResource:
    """Represents an MCP resource"""
    uri: str
    type: str
    name: Optional[str] = None
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPCapabilities:
    """Capabilities of an MCP server"""
    tools: bool = True
    resources: bool = False
    prompts: bool = False
    sampling: bool = False
    logging: bool = True
    custom_features: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPServer:
    """Represents an MCP server"""
    id: str
    type: str
    transport: str
    status: str  # "configured", "starting", "running", "stopped", "error"
    config: Optional[Any] = None
    process_id: Optional[int] = None
    started_at: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class MCPClient:
    """Placeholder for MCP client - will be replaced with actual implementation"""
    server_id: str
    transport_type: str
    connected: bool = False

    async def list_tools(self) -> List[MCPTool]:
        """List available tools from the server"""
        # This is a placeholder - actual implementation will come from MCP SDK
        return []

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool on the server"""
        # This is a placeholder - actual implementation will come from MCP SDK
        return {"status": "not_implemented"}

    async def get_capabilities(self) -> MCPCapabilities:
        """Get server capabilities"""
        return MCPCapabilities()


@dataclass
class MCPConnection:
    """Represents a connection to an MCP server"""
    server_id: str
    server: MCPServer
    client: MCPClient
    connected_at: datetime
    capabilities: MCPCapabilities
    last_health_check: Optional[datetime] = None
    health_status: str = "unknown"


@dataclass
class HealthStatus:
    """Health status of an MCP server"""
    healthy: bool
    status: str  # "healthy", "degraded", "unhealthy", "disconnected"
    message: Optional[str] = None
    last_check: datetime = field(default_factory=datetime.utcnow)
    response_time_ms: Optional[float] = None
    error_count: int = 0


@dataclass
class ToolExecutionResult:
    """Result of tool execution"""
    tool_name: str
    success: bool
    result: Any
    execution_time: float  # seconds
    server: str
    error_message: Optional[str] = None
    retry_count: int = 0


@dataclass
class MCPMessage:
    """Base class for MCP protocol messages"""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None


@dataclass
class MCPRequest(MCPMessage):
    """MCP request message"""
    method: str
    params: Optional[Dict[str, Any]] = None


@dataclass
class MCPResponse(MCPMessage):
    """MCP response message"""
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


@dataclass
class MCPNotification(MCPMessage):
    """MCP notification message"""
    method: str
    params: Optional[Dict[str, Any]] = None


@dataclass
class ConnectionPool:
    """Connection pool for managing MCP client connections"""
    max_connections: int
    connections: Dict[str, MCPClient] = field(default_factory=dict)
    active_count: int = 0

    def acquire(self, server_id: str) -> Optional[MCPClient]:
        """Acquire a connection from the pool"""
        if server_id in self.connections:
            return self.connections[server_id]
        if self.active_count < self.max_connections:
            return None  # Signal to create new connection
        raise RuntimeError(f"Connection pool exhausted (max: {self.max_connections})")

    def release(self, server_id: str, client: MCPClient) -> None:
        """Release a connection back to the pool"""
        self.connections[server_id] = client

    def remove(self, server_id: str) -> None:
        """Remove a connection from the pool"""
        if server_id in self.connections:
            del self.connections[server_id]
            self.active_count = max(0, self.active_count - 1)
"""
MCP (Model Context Protocol) Integration Package

This package provides comprehensive MCP integration for the Suntory V3 system,
enabling agents to connect with external tools and services through a
standardized protocol.
"""

# Core components
from .config import (
    MCPConfig,
    MCPServerConfig,
    MCPAgentPermissions,
    TransportType,
    ServerType,
    RestartPolicy,
    get_mcp_config,
    reset_mcp_config,
    FILESYSTEM_SERVER,
    GITHUB_SERVER,
    DATABASE_SERVER
)

from .types import (
    MCPTool,
    MCPResource,
    MCPCapabilities,
    MCPServer,
    MCPClient,
    MCPConnection,
    HealthStatus,
    ToolExecutionResult,
    ToolParameter,
    ToolParameterType,
    ConnectionPool
)

from .manager import (
    MCPManager,
    MCPOperationError,
    get_mcp_manager,
    reset_mcp_manager
)

from .client import (
    MCPClientManager,
    RealMCPClient,
    StdioTransport,
    SSETransport,
    WebSocketTransport
)

from .supervisor import (
    MCPServerSupervisor,
    MCPServerProcess,
    ServerStatus
)

from .autogen_bridge import (
    MCPAutoGenBridge,
    AutoGenToolAdapter
)

# Version
__version__ = "1.0.0"

# Public API
__all__ = [
    # Config
    "MCPConfig",
    "MCPServerConfig",
    "MCPAgentPermissions",
    "TransportType",
    "ServerType",
    "RestartPolicy",
    "get_mcp_config",
    "reset_mcp_config",
    "FILESYSTEM_SERVER",
    "GITHUB_SERVER",
    "DATABASE_SERVER",

    # Types
    "MCPTool",
    "MCPResource",
    "MCPCapabilities",
    "MCPServer",
    "MCPClient",
    "MCPConnection",
    "HealthStatus",
    "ToolExecutionResult",
    "ToolParameter",
    "ToolParameterType",
    "ConnectionPool",

    # Manager
    "MCPManager",
    "MCPOperationError",
    "get_mcp_manager",
    "reset_mcp_manager",

    # Client
    "MCPClientManager",
    "RealMCPClient",
    "StdioTransport",
    "SSETransport",
    "WebSocketTransport",

    # Supervisor
    "MCPServerSupervisor",
    "MCPServerProcess",
    "ServerStatus",

    # Bridge
    "MCPAutoGenBridge",
    "AutoGenToolAdapter",

    # Version
    "__version__"
]
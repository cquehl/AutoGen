"""
MCP Configuration Management

This module provides configuration schemas and settings for the Model Context Protocol
integration, including server configurations, connection settings, and runtime parameters.
"""

from typing import Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings
import os


class TransportType(str, Enum):
    """Supported MCP transport mechanisms"""
    STDIO = "stdio"
    SSE = "sse"
    WEBSOCKET = "websocket"


class ServerType(str, Enum):
    """Known MCP server types"""
    FILESYSTEM = "filesystem"
    GITHUB = "github"
    DATABASE = "database"
    SLACK = "slack"
    WEB_SEARCH = "web_search"
    MEMORY = "memory"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    EMAIL = "email"
    DOCUMENTATION = "documentation"
    CUSTOM = "custom"


class RestartPolicy(str, Enum):
    """Server restart policies"""
    ALWAYS = "always"
    ON_FAILURE = "on-failure"
    UNLESS_STOPPED = "unless-stopped"
    NEVER = "never"


class MCPServerConfig(BaseModel):
    """Configuration for an individual MCP server"""

    name: str = Field(..., description="Unique name for the MCP server")
    type: ServerType = Field(..., description="Type of MCP server")
    transport: TransportType = Field(
        TransportType.STDIO,
        description="Transport mechanism to use"
    )

    # Transport-specific settings
    command: Optional[str] = Field(
        None,
        description="Command to start the server (for stdio transport)"
    )
    url: Optional[str] = Field(
        None,
        description="URL for SSE/WebSocket transport"
    )

    # Environment and configuration
    env: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables for the server"
    )
    args: List[str] = Field(
        default_factory=list,
        description="Command-line arguments for the server"
    )
    working_directory: Optional[str] = Field(
        None,
        description="Working directory for the server process"
    )

    # Lifecycle management
    auto_start: bool = Field(
        True,
        description="Automatically start this server on initialization"
    )
    restart_policy: RestartPolicy = Field(
        RestartPolicy.ON_FAILURE,
        description="Restart policy for the server"
    )
    max_retries: int = Field(
        3,
        description="Maximum number of restart attempts"
    )

    # Resource limits
    timeout: int = Field(
        30,
        description="Timeout for server operations in seconds"
    )
    max_memory_mb: Optional[int] = Field(
        None,
        description="Maximum memory usage in MB"
    )
    max_cpu_percent: Optional[float] = Field(
        None,
        description="Maximum CPU usage percentage"
    )

    # Security
    allowed_tools: Optional[List[str]] = Field(
        None,
        description="List of allowed tools (None = all allowed)"
    )
    authentication: Optional[Dict[str, str]] = Field(
        None,
        description="Authentication credentials"
    )

    @validator('command')
    def validate_stdio_command(cls, v, values):
        """Ensure command is provided for stdio transport"""
        if values.get('transport') == TransportType.STDIO and not v:
            raise ValueError("Command is required for stdio transport")
        return v

    @validator('url')
    def validate_network_url(cls, v, values):
        """Ensure URL is provided for network transports"""
        transport = values.get('transport')
        if transport in [TransportType.SSE, TransportType.WEBSOCKET] and not v:
            raise ValueError(f"URL is required for {transport} transport")
        return v


class MCPAgentPermissions(BaseModel):
    """Defines which MCP servers an agent can access"""

    agent_name: str = Field(..., description="Name of the agent")
    allowed_servers: List[str] = Field(
        default_factory=list,
        description="List of MCP server names this agent can access"
    )
    allowed_tools: Optional[List[str]] = Field(
        None,
        description="Specific tools this agent can use (None = all from allowed servers)"
    )
    rate_limit: Optional[int] = Field(
        None,
        description="Maximum MCP calls per minute for this agent"
    )


class MCPConfig(BaseSettings):
    """Main MCP configuration settings"""

    # Core settings
    enabled: bool = Field(
        True,
        description="Enable MCP integration"
    )

    # Server configurations
    servers: List[MCPServerConfig] = Field(
        default_factory=list,
        description="List of MCP server configurations"
    )

    # Connection settings
    max_connections: int = Field(
        10,
        description="Maximum concurrent MCP connections"
    )
    connection_timeout: int = Field(
        30,
        description="Connection timeout in seconds"
    )
    operation_timeout: int = Field(
        60,
        description="Default timeout for MCP operations in seconds"
    )

    # Health monitoring
    health_check_enabled: bool = Field(
        True,
        description="Enable health monitoring for MCP servers"
    )
    health_check_interval: int = Field(
        60,
        description="Health check interval in seconds"
    )
    health_check_timeout: int = Field(
        10,
        description="Health check timeout in seconds"
    )

    # Retry configuration
    retry_enabled: bool = Field(
        True,
        description="Enable automatic retry on failures"
    )
    retry_max_attempts: int = Field(
        3,
        description="Maximum retry attempts"
    )
    retry_backoff_base: float = Field(
        2.0,
        description="Base for exponential backoff"
    )
    retry_backoff_max: float = Field(
        30.0,
        description="Maximum backoff time in seconds"
    )

    # Caching
    cache_enabled: bool = Field(
        True,
        description="Enable caching of tool descriptions and schemas"
    )
    cache_ttl: int = Field(
        3600,
        description="Cache TTL in seconds"
    )

    # Security
    agent_permissions: List[MCPAgentPermissions] = Field(
        default_factory=list,
        description="Agent-specific MCP permissions"
    )
    audit_logging: bool = Field(
        True,
        description="Enable audit logging for MCP operations"
    )

    # Performance
    parallel_execution: bool = Field(
        True,
        description="Enable parallel tool execution"
    )
    max_parallel_operations: int = Field(
        5,
        description="Maximum parallel MCP operations"
    )

    # Logging
    log_level: str = Field(
        "INFO",
        description="Logging level for MCP operations"
    )
    log_protocol_messages: bool = Field(
        False,
        description="Log detailed protocol messages (debug mode)"
    )

    class Config:
        env_prefix = "MCP_"
        env_file = ".env"
        env_file_encoding = "utf-8"

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "MCPConfig":
        """Load configuration from YAML file"""
        import yaml
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def get_server_config(self, server_name: str) -> Optional[MCPServerConfig]:
        """Get configuration for a specific server"""
        for server in self.servers:
            if server.name == server_name:
                return server
        return None

    def get_agent_permissions(self, agent_name: str) -> Optional[MCPAgentPermissions]:
        """Get permissions for a specific agent"""
        for perm in self.agent_permissions:
            if perm.agent_name == agent_name:
                return perm
        return None

    def get_allowed_servers_for_agent(self, agent_name: str) -> List[str]:
        """Get list of allowed servers for an agent"""
        permissions = self.get_agent_permissions(agent_name)
        if permissions:
            return permissions.allowed_servers

        # Default permissions based on agent type
        default_permissions = {
            "ALFRED": ["filesystem", "github", "web_search", "memory"],
            "CODER": ["filesystem", "github", "documentation"],
            "DATA": ["database", "filesystem"],
            "WEB_SURFER": ["web_search"],
            "FILE_SURFER": ["filesystem"],
            "ENGINEER": ["filesystem", "github"],
            "OPS": ["docker", "kubernetes"],
            "SECURITY": ["filesystem", "github"],
            # Advisory agents have no MCP access by default
            "PRODUCT": [],
            "UX": [],
            "QA": []
        }

        return default_permissions.get(agent_name.upper(), [])


# Singleton instance
_mcp_config_instance: Optional[MCPConfig] = None


def get_mcp_config() -> MCPConfig:
    """Get the MCP configuration singleton"""
    global _mcp_config_instance
    if _mcp_config_instance is None:
        # Try to load from environment first, then defaults
        _mcp_config_instance = MCPConfig()

        # Load from YAML if specified
        yaml_path = os.getenv("MCP_CONFIG_FILE")
        if yaml_path and os.path.exists(yaml_path):
            _mcp_config_instance = MCPConfig.from_yaml(yaml_path)

    return _mcp_config_instance


def reset_mcp_config():
    """Reset the MCP configuration singleton (mainly for testing)"""
    global _mcp_config_instance
    _mcp_config_instance = None


# Pre-configured server templates
FILESYSTEM_SERVER = MCPServerConfig(
    name="filesystem",
    type=ServerType.FILESYSTEM,
    transport=TransportType.STDIO,
    command="npx @modelcontextprotocol/server-filesystem",
    env={
        "ALLOWED_DIRECTORIES": os.getenv(
            "MCP_FS_ALLOWED_DIRS",
            "/Users/cjq/Dev/MyProjects/AutoGen,/tmp"
        )
    }
)

GITHUB_SERVER = MCPServerConfig(
    name="github",
    type=ServerType.GITHUB,
    transport=TransportType.STDIO,
    command="npx @modelcontextprotocol/server-github",
    env={
        "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN", ""),
        "GITHUB_DEFAULT_OWNER": os.getenv("MCP_GITHUB_DEFAULT_OWNER", ""),
        "GITHUB_DEFAULT_REPO": os.getenv("MCP_GITHUB_DEFAULT_REPO", "")
    }
)

DATABASE_SERVER = MCPServerConfig(
    name="database",
    type=ServerType.DATABASE,
    transport=TransportType.STDIO,
    command="npx @modelcontextprotocol/server-postgres",
    env={
        "CONNECTION_STRING": os.getenv("DATABASE_URL", "")
    },
    auto_start=False  # Don't auto-start database server
)
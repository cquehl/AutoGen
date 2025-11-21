"""
Suntory v3 - Alfred with MCP Integration
Enhanced Alfred with Model Context Protocol capabilities
"""

import asyncio
import uuid
from datetime import datetime
from typing import AsyncIterator, List, Optional, Dict, Any

from ..core import (
    get_cost_tracker,
    get_db_manager,
    get_logger,
    get_settings,
    get_vector_manager,
    handle_exception,
    log_error,
    set_correlation_id,
    stream_completion,
    SuntoryError,
)
from ..core.mcp import (
    MCPManager,
    MCPConfig,
    MCPServerConfig,
    MCPAutoGenBridge,
    AutoGenToolAdapter,
    get_mcp_manager,
    FILESYSTEM_SERVER,
    GITHUB_SERVER,
    DATABASE_SERVER
)
from .modes import AlfredMode, get_direct_mode, get_team_mode
from .personality import get_alfred_personality
from .preference_errors import PreferenceStorageError
from .user_preferences import UserPreferencesManager, get_privacy_notice

logger = get_logger(__name__)


class AlfredMCP:
    """
    Alfred with MCP Integration - The AI Concierge with Extended Capabilities

    Features:
    - All original Alfred capabilities
    - MCP tool integration for extended functionality
    - Dynamic tool loading based on context
    - Agent-specific tool permissions
    - Real-time tool discovery and execution
    """

    def __init__(self, mcp_config: Optional[MCPConfig] = None):
        # Original Alfred initialization
        self.settings = get_settings()
        self.personality = get_alfred_personality()
        self.direct_mode = get_direct_mode()
        self.team_mode = get_team_mode()
        self.cost_tracker = get_cost_tracker()

        # Session management
        self.session_id = str(uuid.uuid4())
        self.conversation_history: List[dict] = []
        self.current_mode = AlfredMode.DIRECT

        # User preferences manager
        self.preferences_manager = UserPreferencesManager(self.session_id)

        # MCP Integration
        self.mcp_config = mcp_config or self._create_default_mcp_config()
        self.mcp_manager: Optional[MCPManager] = None
        self.mcp_bridge: Optional[MCPAutoGenBridge] = None
        self.mcp_adapter: Optional[AutoGenToolAdapter] = None
        self.available_tools: Dict[str, Any] = {}

        logger.info(
            "Alfred MCP initialized",
            session_id=self.session_id,
            model=self.settings.default_model,
            mcp_enabled=self.mcp_config.enabled
        )

    def _create_default_mcp_config(self) -> MCPConfig:
        """Create default MCP configuration for Alfred"""
        servers = []

        # Add filesystem server if enabled
        if self.settings.get("MCP_FS_ENABLED", True):
            fs_config = FILESYSTEM_SERVER
            fs_config.env["ALLOWED_DIRECTORIES"] = self.settings.get(
                "MCP_FS_ALLOWED_DIRS",
                f"{self.settings.workspace_dir},/tmp"
            )
            servers.append(fs_config)

        # Add GitHub server if token is available
        github_token = self.settings.get("GITHUB_TOKEN")
        if github_token and self.settings.get("MCP_GITHUB_ENABLED", True):
            gh_config = GITHUB_SERVER
            gh_config.env["GITHUB_TOKEN"] = github_token
            servers.append(gh_config)

        # Add database server if configured
        if self.settings.get("MCP_DB_ENABLED", False):
            db_config = DATABASE_SERVER
            db_config.env["CONNECTION_STRING"] = self.settings.database_url
            servers.append(db_config)

        return MCPConfig(
            enabled=self.settings.get("MCP_ENABLED", True),
            servers=servers,
            log_level=self.settings.log_level
        )

    async def initialize(self):
        """Initialize Alfred and MCP services"""
        logger.info("Initializing Alfred MCP and services...")

        try:
            # Initialize original Alfred services
            db = await get_db_manager()
            vector = get_vector_manager()
            self.preferences_manager.load_from_storage()

            # Initialize MCP if enabled
            if self.mcp_config.enabled:
                await self._initialize_mcp()

            # Log session start
            await db.add_conversation(
                session_id=self.session_id,
                role="system",
                content="Session started with MCP integration",
                metadata={
                    "model": self.settings.default_model,
                    "environment": self.settings.environment.value,
                    "mcp_enabled": self.mcp_config.enabled,
                    "mcp_servers": len(self.mcp_config.servers)
                }
            )

            logger.info(
                "Alfred MCP ready",
                session_id=self.session_id,
                user_preferences=self.preferences_manager.get_preferences(),
                mcp_tools=len(self.available_tools)
            )

        except Exception as e:
            error = handle_exception(e)
            log_error(error)
            raise error

    async def _initialize_mcp(self):
        """Initialize MCP subsystem"""
        logger.info("Initializing MCP subsystem...")

        # Create MCP manager
        self.mcp_manager = MCPManager(config=self.mcp_config)
        await self.mcp_manager.initialize()

        # Create bridge and adapter
        self.mcp_bridge = MCPAutoGenBridge(self.mcp_manager)
        self.mcp_adapter = AutoGenToolAdapter(self.mcp_bridge)

        # Get available tools for Alfred
        tools = await self.mcp_manager.list_tools("ALFRED")
        for tool in tools:
            # Convert to AutoGen-compatible function
            tool_func = self.mcp_bridge.convert_mcp_to_autogen_tool(tool, "ALFRED")
            self.available_tools[tool.name] = tool_func

        logger.info(f"MCP initialized with {len(tools)} tools available")

    async def greet(self) -> str:
        """Generate a greeting that includes MCP capabilities if enabled"""
        greeting = await self.personality.generate_greeting(self.preferences_manager.get_preferences())

        if self.mcp_config.enabled and self.available_tools:
            greeting += "\n\nI've been enhanced with extended capabilities through MCP integration."
            greeting += f" I have access to {len(self.available_tools)} specialized tools"
            greeting += " to better assist you with file operations, code management, and more."

        return greeting

    async def handle_message(self, user_message: str, force_mode: Optional[AlfredMode] = None) -> str:
        """Handle user message with MCP tool awareness"""
        set_correlation_id()

        try:
            # Check for MCP-specific commands
            if user_message.startswith("/mcp"):
                return await self._handle_mcp_command(user_message)

            # Extract and store user preferences
            await self._update_preferences(user_message)

            # Store user message
            db = await get_db_manager()
            await db.add_conversation(
                session_id=self.session_id,
                role="user",
                content=user_message
            )

            # Select mode with MCP awareness
            mode = await self._select_mode_with_mcp(user_message, force_mode)
            self.current_mode = mode

            # Process based on mode
            if mode == AlfredMode.DIRECT:
                response = await self._process_direct_with_mcp(user_message)
            else:
                response = await self._process_team_with_mcp(user_message)

            # Store assistant response
            await db.add_conversation(
                session_id=self.session_id,
                role="assistant",
                content=response
            )

            # Add cost information
            cost_info = self.cost_tracker.get_session_cost(self.session_id)
            response += f"\n\n💰 Session cost: ${cost_info['total_cost']:.4f}"

            return response

        except Exception as e:
            error = handle_exception(e)
            log_error(error)
            return error.format_for_user()

    async def _handle_mcp_command(self, command: str) -> str:
        """Handle MCP-specific commands"""
        parts = command.split()

        if len(parts) == 1 or parts[1] == "status":
            # Show MCP status
            if not self.mcp_manager:
                return "MCP is not initialized."

            metrics = self.mcp_manager.get_metrics()
            health = await self.mcp_manager.health_check()

            status = "📊 **MCP Status**\n\n"
            status += f"Connected servers: {metrics['connected_servers']}\n"
            status += f"Available tools: {metrics['available_tools']}\n\n"

            status += "**Server Health:**\n"
            for server, health_status in health.items():
                emoji = "✅" if health_status.healthy else "❌"
                status += f"  {emoji} {server}: {health_status.status}\n"

            if metrics.get('operation_counts'):
                status += "\n**Tool Usage:**\n"
                for tool, count in metrics['operation_counts'].items():
                    status += f"  • {tool}: {count} calls\n"

            return status

        elif parts[1] == "tools":
            # List available tools
            if not self.available_tools:
                return "No MCP tools available."

            response = "🛠️ **Available MCP Tools:**\n\n"
            for tool_name in sorted(self.available_tools.keys()):
                tool_func = self.available_tools[tool_name]
                doc = tool_func.__doc__ or "No description available"
                first_line = doc.strip().split('\n')[0]
                response += f"• **{tool_name}**: {first_line}\n"

            return response

        elif parts[1] == "servers":
            # List configured servers
            response = "🖥️ **MCP Servers:**\n\n"
            for server in self.mcp_config.servers:
                response += f"• **{server.name}** ({server.type.value})\n"
                response += f"  Transport: {server.transport.value}\n"
                response += f"  Auto-start: {server.auto_start}\n"
                response += f"  Status: {self.mcp_manager.get_server_status(server.name) if self.mcp_manager else 'Unknown'}\n\n"

            return response

        elif parts[1] == "reload":
            # Reload MCP configuration
            await self._initialize_mcp()
            return "✅ MCP configuration reloaded successfully."

        else:
            return "Unknown MCP command. Available: /mcp [status|tools|servers|reload]"

    async def _select_mode_with_mcp(self, user_message: str, force_mode: Optional[AlfredMode]) -> AlfredMode:
        """Select mode with MCP tool awareness"""
        if force_mode:
            return force_mode

        # Check if message requires MCP tools
        mcp_keywords = ["file", "filesystem", "github", "repository", "database", "query"]
        if any(keyword in user_message.lower() for keyword in mcp_keywords):
            # Check if tools are available
            if self.available_tools:
                # Prefer team mode for complex MCP operations
                if any(word in user_message.lower() for word in ["analyze", "refactor", "implement", "create"]):
                    return AlfredMode.TEAM

        # Original mode selection logic
        return await self.direct_mode.select_mode(user_message)

    async def _process_direct_with_mcp(self, message: str) -> str:
        """Process message in direct mode with MCP tool access"""
        # Check if MCP tools might be needed
        if self._should_use_mcp_tools(message):
            # Enhance the message with available tools information
            tools_context = self._get_tools_context()
            enhanced_message = f"{message}\n\n[Available MCP Tools: {tools_context}]"
        else:
            enhanced_message = message

        return await self.direct_mode.process(enhanced_message, self.preferences_manager.get_preferences())

    async def _process_team_with_mcp(self, message: str) -> str:
        """Process message in team mode with MCP tool access"""
        # Provide MCP tools to relevant agents
        if self.mcp_adapter:
            # Register tools with specific agents
            await self._register_mcp_tools_with_agents()

        return await self.team_mode.process(message, self.preferences_manager.get_preferences())

    async def _register_mcp_tools_with_agents(self):
        """Register MCP tools with appropriate agents"""
        if not self.mcp_adapter:
            return

        # Map of agents to register tools with
        agent_tool_mapping = {
            "CODER": ["filesystem", "github"],
            "DATA": ["database", "filesystem"],
            "ENGINEER": ["filesystem", "github"],
            "OPS": ["docker", "kubernetes"],
        }

        # This would integrate with the actual agent instances
        # For now, we log the intention
        for agent_name, tool_types in agent_tool_mapping.items():
            available = sum(1 for tool in self.available_tools if any(t in tool for t in tool_types))
            if available > 0:
                logger.info(f"Would register {available} MCP tools with {agent_name} agent")

    def _should_use_mcp_tools(self, message: str) -> bool:
        """Determine if MCP tools might be needed for the message"""
        if not self.available_tools:
            return False

        # Check for tool-related keywords
        tool_indicators = [
            "read", "write", "create", "delete", "list", "search",
            "file", "directory", "folder", "code", "repository",
            "github", "git", "commit", "pull request", "pr",
            "database", "query", "table", "sql"
        ]

        message_lower = message.lower()
        return any(indicator in message_lower for indicator in tool_indicators)

    def _get_tools_context(self) -> str:
        """Get a brief context of available tools"""
        if not self.available_tools:
            return "None"

        tool_names = list(self.available_tools.keys())[:5]  # First 5 tools
        context = ", ".join(tool_names)

        if len(self.available_tools) > 5:
            context += f", and {len(self.available_tools) - 5} more"

        return context

    async def _update_preferences(self, message: str):
        """Extract and update user preferences"""
        try:
            await self.preferences_manager.update_from_conversation(message)
        except PreferenceStorageError as e:
            logger.warning(f"Failed to update preferences: {e}")

    async def process_message_streaming(self, user_message: str) -> AsyncIterator[str]:
        """Process message with streaming response and MCP awareness"""
        set_correlation_id()

        try:
            # Check for MCP commands (non-streaming)
            if user_message.startswith("/mcp"):
                response = await self._handle_mcp_command(user_message)
                yield response
                return

            # Extract preferences
            await self._update_preferences(user_message)

            # Store user message
            db = await get_db_manager()
            await db.add_conversation(
                session_id=self.session_id,
                role="user",
                content=user_message
            )

            # Select mode with MCP awareness
            mode = await self._select_mode_with_mcp(user_message, None)
            self.current_mode = mode

            # Stream based on mode
            full_response = ""
            if mode == AlfredMode.DIRECT:
                async for token in self._process_direct_streaming_with_mcp(user_message):
                    full_response += token
                    yield token
            else:
                # Team mode doesn't stream
                response = await self._process_team_with_mcp(user_message)
                full_response = response
                yield response

            # Store response
            await db.add_conversation(
                session_id=self.session_id,
                role="assistant",
                content=full_response
            )

            # Add cost information
            cost_info = self.cost_tracker.get_session_cost(self.session_id)
            yield f"\n\n💰 Session cost: ${cost_info['total_cost']:.4f}"

        except Exception as e:
            error = handle_exception(e)
            log_error(error)
            yield error.format_for_user()

    async def _process_direct_streaming_with_mcp(self, message: str) -> AsyncIterator[str]:
        """Stream direct mode response with MCP awareness"""
        # Add tools context if needed
        if self._should_use_mcp_tools(message):
            tools_context = self._get_tools_context()
            enhanced_message = f"{message}\n\n[Available MCP Tools: {tools_context}]"
        else:
            enhanced_message = message

        async for token in self.direct_mode.stream_process(
            enhanced_message,
            self.preferences_manager.get_preferences()
        ):
            yield token

    async def execute_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute an MCP tool directly.

        This can be called by agents or used for direct tool execution.
        """
        if not self.mcp_manager:
            raise SuntoryError("MCP is not initialized")

        result = await self.mcp_manager.execute_tool(
            tool_name=tool_name,
            arguments=arguments,
            agent_name="ALFRED"
        )

        return result

    async def shutdown(self):
        """Shutdown Alfred and MCP services"""
        logger.info("Shutting down Alfred MCP...")

        try:
            # Save preferences
            self.preferences_manager.save_to_storage()

            # Shutdown MCP if initialized
            if self.mcp_manager:
                await self.mcp_manager.shutdown()

            # Log session end
            db = await get_db_manager()
            await db.add_conversation(
                session_id=self.session_id,
                role="system",
                content="Session ended",
                metadata={
                    "total_cost": self.cost_tracker.get_session_cost(self.session_id)["total_cost"]
                }
            )

            logger.info("Alfred MCP shutdown complete", session_id=self.session_id)

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Factory function to create Alfred with MCP
def create_alfred_mcp(mcp_config: Optional[MCPConfig] = None) -> AlfredMCP:
    """
    Create an instance of Alfred with MCP integration.

    Args:
        mcp_config: Optional MCP configuration

    Returns:
        AlfredMCP instance
    """
    return AlfredMCP(mcp_config=mcp_config)
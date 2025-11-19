"""
Yamazaki v2 - Tool Registry (Marketplace)

Central registry for tool discovery and management.
Provides plugin-based tool architecture.
"""

from typing import Dict, List, Optional, Type
from autogen_core.tools import FunctionTool

from ..core.base_tool import BaseTool, ToolCategory, ToolMetadata


class ToolRegistry:
    """
    Central registry for all tools (Tool Marketplace).

    Provides plugin-based tool discovery, loading, and management.
    """

    def __init__(self, security_middleware, connection_pool, capability_service=None, history_service=None, agent_factory=None):
        """
        Initialize tool registry.

        Args:
            security_middleware: Security middleware for validation
            connection_pool: Database connection pool manager
            capability_service: Optional CapabilityService for Alfred tools
            history_service: Optional HistoryService for Alfred tools
            agent_factory: Optional AgentFactory for Alfred tools
        """
        self.security_middleware = security_middleware
        self.connection_pool = connection_pool
        self.capability_service = capability_service
        self.history_service = history_service
        self.agent_factory = agent_factory
        self._tools: Dict[str, ToolMetadata] = {}
        self._tool_instances: Dict[str, BaseTool] = {}

    def register(
        self,
        name: str,
        tool_class: Type[BaseTool],
        description: Optional[str] = None,
        category: Optional[ToolCategory] = None,
        requires_security: Optional[bool] = None,
    ):
        """
        Register a tool type.

        Args:
            name: Tool name (unique identifier, e.g., "database.query")
            tool_class: Tool class (must inherit from BaseTool)
            description: Tool description
            category: Tool category
            requires_security: Whether tool requires security validation
        """
        if not issubclass(tool_class, BaseTool):
            raise TypeError(f"{tool_class} must inherit from BaseTool")

        metadata = ToolMetadata(
            name=name,
            description=description or tool_class.DESCRIPTION,
            category=category or tool_class.CATEGORY,
            version=tool_class.VERSION,
            tool_class=tool_class,
            requires_security=requires_security or tool_class.REQUIRES_SECURITY_VALIDATION,
        )

        self._tools[name] = metadata

    def register_decorator(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[ToolCategory] = None,
        requires_security: Optional[bool] = None,
    ):
        """
        Decorator for registering tools.

        Usage:
            @tool_registry.register_decorator(name="database.query")
            class QueryTool(BaseTool):
                ...

        Args:
            name: Tool name (defaults to class NAME)
            description: Tool description
            category: Tool category
            requires_security: Requires security validation
        """
        def decorator(tool_class: Type[BaseTool]):
            tool_name = name or tool_class.NAME
            self.register(
                name=tool_name,
                tool_class=tool_class,
                description=description,
                category=category,
                requires_security=requires_security,
            )
            return tool_class

        return decorator

    def create_tool(self, name: str, **kwargs) -> BaseTool:
        """
        Create a tool instance by name.

        Args:
            name: Tool name (registered name)
            **kwargs: Tool-specific configuration

        Returns:
            BaseTool instance

        Raises:
            ValueError: If tool not found
        """
        if name not in self._tools:
            raise ValueError(
                f"Tool '{name}' not found. Available: {list(self._tools.keys())}"
            )

        metadata = self._tools[name]

        # Inject dependencies based on tool requirements
        tool_kwargs = kwargs.copy()

        # Inject security middleware if needed
        if metadata.requires_security:
            tool_kwargs["security_middleware"] = self.security_middleware

        # Inject connection pool for database tools
        if metadata.category == ToolCategory.DATABASE:
            tool_kwargs["connection_pool"] = self.connection_pool

        # Inject services for META tools (introspection and system capabilities)
        # Use introspection to only inject what the tool accepts
        if metadata.category == ToolCategory.META:
            import inspect
            sig = inspect.signature(metadata.tool_class.__init__)
            params = sig.parameters

            # Only inject services that the tool actually accepts
            if "capability_service" in params and self.capability_service:
                tool_kwargs["capability_service"] = self.capability_service

            if "history_service" in params and self.history_service:
                tool_kwargs["history_service"] = self.history_service

            if "agent_factory" in params and self.agent_factory:
                tool_kwargs["agent_factory"] = self.agent_factory

        # Create tool instance
        tool = metadata.tool_class(**tool_kwargs)

        return tool

    def get_tool(self, name: str, **kwargs) -> Optional[FunctionTool]:
        """
        Get AutoGen FunctionTool by name (cached).

        Args:
            name: Tool name
            **kwargs: Tool configuration

        Returns:
            FunctionTool instance or None if not found
        """
        if name not in self._tools:
            return None

        # Create fresh tool instance with provided kwargs
        # Note: We don't cache tool instances since they may have different configurations
        tool_instance = self.create_tool(name, **kwargs)

        # Create FunctionTool directly from tool's execute method
        # AutoGen will automatically wrap it and extract the signature
        # Note: AutoGen requires names with only letters, numbers, _ and -
        safe_name = name.replace(".", "_")
        function_tool = FunctionTool(
            tool_instance.execute,
            name=safe_name,
            description=tool_instance.DESCRIPTION,
        )

        return function_tool

    def list_tools(
        self,
        category: Optional[ToolCategory] = None,
        requires_security: Optional[bool] = None,
    ) -> List[Dict]:
        """
        List all registered tools.

        Args:
            category: Filter by category (optional)
            requires_security: Filter by security requirement (optional)

        Returns:
            List of tool metadata dicts
        """
        tools = []
        for metadata in self._tools.values():
            # Apply filters
            if category is not None and metadata.category != category:
                continue
            if requires_security is not None and metadata.requires_security != requires_security:
                continue

            tools.append(metadata.to_dict())

        return tools

    def get_tools_by_category(self, category: ToolCategory) -> List[str]:
        """
        Get all tool names in a category.

        Args:
            category: Tool category

        Returns:
            List of tool names
        """
        return [
            name
            for name, metadata in self._tools.items()
            if metadata.category == category
        ]

    def get_tools_for_agent(self, agent_type: str) -> List[str]:
        """
        Get recommended tools for an agent type.

        Args:
            agent_type: Agent type (e.g., "data_analyst", "web_surfer")

        Returns:
            List of recommended tool names
        """
        # Define tool mappings for common agent types
        # Only includes currently implemented tools
        AGENT_TOOL_MAPPINGS = {
            "data_analyst": [
                "database.query",    # ✓ SQL query execution
                "file.read",        # ✓ File reading
            ],
            "web_surfer": [
                # No web tools implemented yet
            ],
            "weather": [
                "weather.forecast",  # ✓ Weather forecasts from weather.gov
            ],
            "alfred": [
                "alfred.list_capabilities",  # ✓ System capability discovery
                "alfred.show_history",       # ✓ Conversation history
                "alfred.delegate_to_team",   # ✓ Multi-agent delegation
            ],
        }

        return AGENT_TOOL_MAPPINGS.get(agent_type, [])

    def get_categories(self) -> List[str]:
        """
        Get all tool categories.

        Returns:
            List of unique categories
        """
        return list(set(m.category.value for m in self._tools.values()))

    def set_alfred_services(self, capability_service, history_service, agent_factory):
        """
        Set services needed for Alfred's tools.

        This is called after services are initialized to inject dependencies.

        Args:
            capability_service: CapabilityService instance
            history_service: HistoryService instance
            agent_factory: AgentFactory instance
        """
        self.capability_service = capability_service
        self.history_service = history_service
        self.agent_factory = agent_factory

        # Clear cached Alfred tool instances so they get recreated with new services
        for tool_name in list(self._tool_instances.keys()):
            if tool_name.startswith("alfred."):
                del self._tool_instances[tool_name]

    def discover_tools(self):
        """
        Auto-discover and register tools from the tools/ directory.

        This scans for all tool modules and registers them.
        """
        # Import tool modules to trigger registration
        try:
            from .database import query_tool
            from .file import read_tool
            from .weather import forecast_tool
            from .alfred import (
                list_capabilities_tool,
                show_history_tool,
                delegate_to_team_tool
            )
        except ImportError as e:
            # Some tools may not exist yet - log but don't fail
            pass

    def __repr__(self) -> str:
        return f"ToolRegistry(tools={len(self._tools)})"

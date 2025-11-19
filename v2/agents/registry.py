"""
Yamazaki v2 - Agent Registry

Central registry for agent discovery and creation.
Eliminates code duplication through plugin architecture.
"""

from typing import Dict, List, Optional, Type
from autogen_agentchat.agents import AssistantAgent
from autogen_core.models import ChatCompletionClient

from ..core.base_agent import BaseAgent, AgentMetadata
from ..config.models import AppSettings, AgentConfig


class AgentRegistry:
    """
    Central registry for all agents.

    Provides plugin-based agent discovery and creation.
    """

    def __init__(self, settings: AppSettings, tool_registry):
        """
        Initialize agent registry.

        Args:
            settings: Application settings
            tool_registry: Tool registry for loading agent tools
        """
        self.settings = settings
        self.tool_registry = tool_registry
        self._agents: Dict[str, AgentMetadata] = {}

    def register(
        self,
        name: str,
        agent_class: Type[BaseAgent],
        description: Optional[str] = None,
        category: Optional[str] = None,
        version: Optional[str] = None,
        default_tools: Optional[List[str]] = None,
    ):
        """
        Register an agent type.

        Args:
            name: Agent name (unique identifier)
            agent_class: Agent class (must inherit from BaseAgent)
            description: Agent description
            category: Agent category
            version: Agent version
            default_tools: Default tools for this agent
        """
        if not issubclass(agent_class, BaseAgent):
            raise TypeError(f"{agent_class} must inherit from BaseAgent")

        metadata = AgentMetadata(
            name=name,
            description=description or agent_class.DESCRIPTION,
            category=category or agent_class.CATEGORY,
            version=version or agent_class.VERSION,
            agent_class=agent_class,
            default_tools=default_tools or [],
        )

        self._agents[name] = metadata

    def register_decorator(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        default_tools: Optional[List[str]] = None,
    ):
        """
        Decorator for registering agents.

        Usage:
            @agent_registry.register_decorator(name="my_agent")
            class MyAgent(BaseAgent):
                ...

        Args:
            name: Agent name (defaults to class NAME)
            description: Agent description
            category: Agent category
            default_tools: Default tools
        """
        def decorator(agent_class: Type[BaseAgent]):
            agent_name = name or agent_class.NAME
            self.register(
                name=agent_name,
                agent_class=agent_class,
                description=description,
                category=category,
                default_tools=default_tools,
            )
            return agent_class

        return decorator

    def create_agent(
        self,
        name: str,
        config: Optional[AgentConfig] = None,
        model_client: Optional[ChatCompletionClient] = None,
    ) -> BaseAgent:
        """
        Create an agent instance by name.

        Args:
            name: Agent name (registered name)
            config: Agent configuration (uses settings if not provided)
            model_client: Model client (creates from settings if not provided)

        Returns:
            BaseAgent instance

        Raises:
            ValueError: If agent not found
        """
        if name not in self._agents:
            raise ValueError(
                f"Agent '{name}' not found. Available: {list(self._agents.keys())}"
            )

        metadata = self._agents[name]

        # Use config from settings if not provided
        if config is None:
            if name in self.settings.agents:
                config = self.settings.agents[name]
            else:
                # Create default config
                config = AgentConfig(name=name)

        # Create model client if not provided
        if model_client is None:
            model_client = self.settings.get_model_client(config.model_provider)

        # Load tools for agent
        tool_names = config.tools or metadata.default_tools
        tools = []
        for tool_name in tool_names:
            tool = self.tool_registry.get_tool(tool_name)
            if tool:
                tools.append(tool)

        # Create agent instance
        agent = metadata.agent_class(
            config=config,
            model_client=model_client,
            tools=tools,
        )

        return agent

    def get_agent(
        self,
        name: str,
        config: Optional[AgentConfig] = None,
        model_client: Optional[ChatCompletionClient] = None,
    ) -> AssistantAgent:
        """
        Get AutoGen AssistantAgent by name.

        Args:
            name: Agent name
            config: Agent configuration
            model_client: Model client

        Returns:
            AssistantAgent instance
        """
        base_agent = self.create_agent(name, config, model_client)
        return base_agent.get_agent()

    def list_agents(self, category: Optional[str] = None) -> List[Dict]:
        """
        List all registered agents.

        Args:
            category: Filter by category (optional)

        Returns:
            List of agent metadata dicts
        """
        agents = []
        for metadata in self._agents.values():
            if category is None or metadata.category == category:
                agents.append(metadata.to_dict())
        return agents

    def get_categories(self) -> List[str]:
        """
        Get all agent categories.

        Returns:
            List of unique categories
        """
        return list(set(m.category for m in self._agents.values()))

    def discover_agents(self):
        """
        Auto-discover and register agents from the agents/ directory.

        This scans for all agent modules and registers them.
        """
        # Import agent modules and register them
        try:
            from .weather_agent import WeatherAgent
            self.register(
                name=WeatherAgent.NAME,
                agent_class=WeatherAgent,
                default_tools=["weather.forecast"]
            )
        except ImportError:
            pass

        try:
            from .data_analyst_agent import DataAnalystAgent
            self.register(
                name=DataAnalystAgent.NAME,
                agent_class=DataAnalystAgent,
                default_tools=["database.query", "database.list_tables"]
            )
        except ImportError:
            pass

        try:
            from .orchestrator_agent import OrchestratorAgent
            self.register(
                name=OrchestratorAgent.NAME,
                agent_class=OrchestratorAgent,
                default_tools=[]
            )
        except ImportError:
            pass

        try:
            from .alfred_agent import AlfredAgent
            self.register(
                name=AlfredAgent.NAME,
                agent_class=AlfredAgent,
                default_tools=[
                    "alfred.list_capabilities",
                    "alfred.show_history",
                    "alfred.delegate_to_team"
                ]
            )
        except ImportError:
            pass

    def __repr__(self) -> str:
        return f"AgentRegistry(agents={len(self._agents)})"


# Global registry instance (for decorator usage)
_global_registry: Optional[AgentRegistry] = None


def get_global_registry() -> Optional[AgentRegistry]:
    """Get global registry (if set)"""
    return _global_registry


def set_global_registry(registry: AgentRegistry):
    """Set global registry"""
    global _global_registry
    _global_registry = registry

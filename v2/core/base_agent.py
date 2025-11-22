"""
Yamazaki v2 - Base Agent Class

Abstract base class for all agents in the system.
Provides common functionality and interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from autogen_agentchat.agents import AssistantAgent
from autogen_core.models import ChatCompletionClient
from autogen_core.tools import FunctionTool

from ..config.models import AgentConfig


class BaseAgent(ABC):
    """
    Base class for all Yamazaki agents.

    Provides common functionality and enforces interface contracts.
    """

    # Class-level metadata
    NAME: str = "BaseAgent"
    DESCRIPTION: str = "Base agent class"
    CATEGORY: str = "general"  # Categories: general, data, web, orchestrator, etc.
    VERSION: str = "1.0.0"

    def __init__(
        self,
        config: AgentConfig,
        model_client: ChatCompletionClient,
        tools: Optional[List[FunctionTool]] = None,
    ):
        """Initialize base agent."""
        self.config = config
        self.model_client = model_client
        self.tools = tools or []
        self._agent: Optional[AssistantAgent] = None

    @property
    @abstractmethod
    def system_message(self) -> str:
        """System message for the agent. Must be implemented by subclasses."""
        pass

    def create_agent(self) -> AssistantAgent:
        """Create the underlying AssistantAgent."""
        if self._agent is None:
            self._agent = AssistantAgent(
                name=self.config.name,
                model_client=self.model_client,
                tools=self.tools,
                system_message=self.system_message,
                reflect_on_tool_use=self.config.reflect_on_tool_use,
            )
        return self._agent

    def get_agent(self) -> AssistantAgent:
        """Get the agent (creates if not exists)."""
        return self.create_agent()

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Get agent metadata."""
        return {
            "name": cls.NAME,
            "description": cls.DESCRIPTION,
            "category": cls.CATEGORY,
            "version": cls.VERSION,
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.config.name}, category={self.CATEGORY})"


class AgentMetadata:
    """Metadata for agent registration"""

    def __init__(
        self,
        name: str,
        description: str,
        category: str,
        version: str,
        agent_class: type,
        default_tools: Optional[List[str]] = None,
    ):
        self.name = name
        self.description = description
        self.category = category
        self.version = version
        self.agent_class = agent_class
        self.default_tools = default_tools or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "version": self.version,
            "default_tools": self.default_tools,
        }

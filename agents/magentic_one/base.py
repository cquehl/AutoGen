"""
Base Magnetic Agent - Reusable foundation for all Magentic-One agents

Provides common functionality and easy tool registration.
"""

from autogen_agentchat.agents import AssistantAgent
from autogen_core.tools import FunctionTool
from autogen_core.models import ChatCompletionClient
from typing import List, Callable, Optional, Any
import asyncio


class BaseMagneticAgent(AssistantAgent):
    """
    Base class for all Magentic-One agents.

    Provides:
    - Easy tool registration
    - Common configuration
    - Extensibility for specialized agents

    Example:
        agent = BaseMagneticAgent(
            name="MyAgent",
            model_client=client,
            system_message="You are a helpful agent"
        )
        agent.add_tool(my_function, "Description of what it does")
    """

    def __init__(
        self,
        name: str,
        model_client: ChatCompletionClient,
        system_message: str,
        tools: Optional[List[FunctionTool]] = None,
        **kwargs
    ):
        """
        Initialize a Magnetic Agent.

        Args:
            name: Agent name
            model_client: ChatCompletionClient instance
            system_message: System prompt for the agent
            tools: Optional list of pre-configured tools
            **kwargs: Additional arguments passed to AssistantAgent
        """
        self._custom_tools = tools or []

        # Call parent constructor
        super().__init__(
            name=name,
            model_client=model_client,
            system_message=system_message,
            tools=self._custom_tools,
            reflect_on_tool_use=True,  # Enable self-correction
            **kwargs
        )

    def add_tool(self, func: Callable, description: str) -> None:
        """
        Add a tool to this agent.

        Args:
            func: The async function to add as a tool
            description: Description of what the tool does (for LLM)

        Example:
            async def my_tool(param: str) -> dict:
                return {"result": "value"}

            agent.add_tool(my_tool, "Does something useful")
        """
        tool = FunctionTool(func, description=description)
        self._custom_tools.append(tool)

        # Update the agent's tools
        # Note: In AutoGen 0.6, tools are set at initialization
        # For dynamic tool addition, we'd need to recreate the agent
        # For now, add tools before using the agent

    def get_tools(self) -> List[FunctionTool]:
        """Get all tools registered with this agent."""
        return self._custom_tools.copy()

    @property
    def tool_count(self) -> int:
        """Number of tools available to this agent."""
        return len(self._custom_tools)


class AgentResult:
    """
    Structured result from agent execution.

    Makes it easy to check success/failure and extract results.
    """

    def __init__(
        self,
        success: bool,
        result: Any = None,
        error: Optional[str] = None,
        metadata: Optional[dict] = None
    ):
        self.success = success
        self.result = result
        self.error = error
        self.metadata = metadata or {}

    def __repr__(self) -> str:
        if self.success:
            return f"AgentResult(success=True, result={self.result})"
        else:
            return f"AgentResult(success=False, error={self.error})"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata
        }

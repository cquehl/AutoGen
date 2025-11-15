"""
Yamazaki v2 - Agent Factory

High-level factory for creating agents and teams.
"""

from typing import Optional, List
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_core.models import ChatCompletionClient

from ..config.models import AppSettings, TeamConfig
from .registry import AgentRegistry
from ..tools.registry import ToolRegistry


class AgentFactory:
    """
    Factory for creating agents and teams.

    Simplifies agent/team creation with automatic configuration.
    """

    def __init__(
        self,
        settings: AppSettings,
        agent_registry: AgentRegistry,
        tool_registry: ToolRegistry,
    ):
        """
        Initialize factory.

        Args:
            settings: Application settings
            agent_registry: Agent registry
            tool_registry: Tool registry
        """
        self.settings = settings
        self.agent_registry = agent_registry
        self.tool_registry = tool_registry

    def create(
        self,
        agent_name: str,
        model_client: Optional[ChatCompletionClient] = None,
    ) -> AssistantAgent:
        """
        Create an agent by name.

        Args:
            agent_name: Name of agent to create
            model_client: Optional model client

        Returns:
            AssistantAgent instance
        """
        return self.agent_registry.get_agent(
            name=agent_name,
            model_client=model_client,
        )

    def create_team(
        self,
        team_name: str,
        model_client: Optional[ChatCompletionClient] = None,
        include_user_proxy: bool = True,
    ) -> SelectorGroupChat:
        """
        Create a team by name.

        Args:
            team_name: Name of team (from settings.teams)
            model_client: Optional model client
            include_user_proxy: Include user proxy agent

        Returns:
            SelectorGroupChat team

        Raises:
            ValueError: If team not found in settings
        """
        if team_name not in self.settings.teams:
            raise ValueError(
                f"Team '{team_name}' not found in settings. "
                f"Available: {list(self.settings.teams.keys())}"
            )

        team_config = self.settings.teams[team_name]

        # Get model client
        if model_client is None:
            model_client = self.settings.get_model_client()

        # Create agents
        agents = []
        for agent_name in team_config.agents:
            agent = self.create(agent_name, model_client)
            agents.append(agent)

        # Add user proxy if requested
        if include_user_proxy:
            user_proxy = UserProxyAgent(
                name="Human",
                description="Human user who provides tasks and feedback",
            )
            agents.append(user_proxy)

        # Create team
        team = SelectorGroupChat(
            participants=agents,
            model_client=model_client,
            termination_condition=TextMentionTermination("TERMINATE"),
            selector_prompt=team_config.selector_prompt or self._default_selector_prompt(team_config),
            max_turns=team_config.max_turns,
            allow_repeated_speaker=team_config.allow_repeated_speaker,
        )

        return team

    def create_custom_team(
        self,
        agent_names: List[str],
        max_turns: int = 15,
        allow_repeated_speaker: bool = False,
        selector_prompt: Optional[str] = None,
        model_client: Optional[ChatCompletionClient] = None,
        include_user_proxy: bool = True,
    ) -> SelectorGroupChat:
        """
        Create a custom team with specified agents.

        Args:
            agent_names: List of agent names
            max_turns: Maximum conversation turns
            allow_repeated_speaker: Allow same agent consecutively
            selector_prompt: Custom selector prompt
            model_client: Optional model client
            include_user_proxy: Include user proxy

        Returns:
            SelectorGroupChat team
        """
        # Get model client
        if model_client is None:
            model_client = self.settings.get_model_client()

        # Create agents
        agents = []
        for agent_name in agent_names:
            agent = self.create(agent_name, model_client)
            agents.append(agent)

        # Add user proxy
        if include_user_proxy:
            user_proxy = UserProxyAgent(
                name="Human",
                description="Human user who provides tasks and feedback",
            )
            agents.append(user_proxy)

        # Use default selector prompt if not provided
        if selector_prompt is None:
            selector_prompt = self._default_selector_prompt_from_names(agent_names)

        # Create team
        team = SelectorGroupChat(
            participants=agents,
            model_client=model_client,
            termination_condition=TextMentionTermination("TERMINATE"),
            selector_prompt=selector_prompt,
            max_turns=max_turns,
            allow_repeated_speaker=allow_repeated_speaker,
        )

        return team

    def _default_selector_prompt(self, team_config: TeamConfig) -> str:
        """Generate default selector prompt from team config"""
        return f"""
        You are orchestrating a conversation between: {{participants}}.

        Team: {team_config.name}
        Agents: {', '.join(team_config.agents)}

        Select the most appropriate agent to respond next based on:
        - The user's request
        - The current context
        - Each agent's specialization

        Reply with just the agent name and nothing else.
        """

    def _default_selector_prompt_from_names(self, agent_names: List[str]) -> str:
        """Generate default selector prompt from agent names"""
        return f"""
        You are orchestrating a conversation between: {{participants}}.

        Agents: {', '.join(agent_names)}

        Select the most appropriate agent to respond next based on:
        - The user's request
        - The current context
        - Each agent's specialization

        Reply with just the agent name and nothing else.
        """

    def list_available_agents(self, category: Optional[str] = None) -> List[str]:
        """
        List available agents.

        Args:
            category: Filter by category

        Returns:
            List of agent names
        """
        agents = self.agent_registry.list_agents(category)
        return [a["name"] for a in agents]

    def list_available_teams(self) -> List[str]:
        """
        List available teams from settings.

        Returns:
            List of team names
        """
        return list(self.settings.teams.keys())

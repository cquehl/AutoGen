"""
Yamazaki v2 - Capability Service

Provides auto-discovery and caching of system capabilities for Alfred.
Introspects agents, tools, and teams to provide conversational capability descriptions.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import json


class CapabilityService:
    """
    Service for discovering and caching system capabilities.

    Alfred uses this to answer "What can you do?" questions and to provide
    intelligent delegation decisions.
    """

    def __init__(self, agent_registry, tool_registry, settings):
        """
        Initialize capability service.

        Args:
            agent_registry: AgentRegistry instance for agent discovery
            tool_registry: ToolRegistry instance for tool discovery
            settings: AppSettings for team configurations
        """
        self.agent_registry = agent_registry
        self.tool_registry = tool_registry
        self.settings = settings

        # Cache for capabilities
        self._cache: Dict[str, Any] = {}
        self._last_refresh: Optional[datetime] = None
        self._cache_ttl_seconds = 300  # 5 minutes cache

    def refresh_cache(self) -> None:
        """
        Refresh the capabilities cache by introspecting all registries.
        """
        self._cache = {
            "agents": self._discover_agents(),
            "tools": self._discover_tools(),
            "teams": self._discover_teams(),
            "categories": self._discover_categories(),
        }
        self._last_refresh = datetime.now()

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self._last_refresh:
            return False

        elapsed = (datetime.now() - self._last_refresh).total_seconds()
        return elapsed < self._cache_ttl_seconds

    def _ensure_cache(self) -> None:
        """Ensure cache is valid, refresh if needed."""
        if not self._is_cache_valid():
            self.refresh_cache()

    def _discover_agents(self) -> List[Dict[str, Any]]:
        """
        Discover all registered agents.

        Returns:
            List of agent capability dictionaries
        """
        agents = self.agent_registry.list_agents()

        # Enrich with additional info from settings
        enriched_agents = []
        for agent in agents:
            agent_data = agent.copy()

            # Add configuration from settings if available
            agent_name = agent["name"]
            if hasattr(self.settings, 'agents') and agent_name in self.settings.agents:
                config = self.settings.agents[agent_name]
                agent_data["configured"] = True
                agent_data["model_provider"] = getattr(config, 'model_provider', 'unknown')
                agent_data["temperature"] = getattr(config, 'temperature', 0.7)
                agent_data["tools"] = getattr(config, 'tools', None) or []
            else:
                agent_data["configured"] = False
                agent_data["tools"] = []

            enriched_agents.append(agent_data)

        return enriched_agents

    def _discover_tools(self) -> List[Dict[str, Any]]:
        """
        Discover all registered tools.

        Returns:
            List of tool capability dictionaries
        """
        return self.tool_registry.list_tools()

    def _discover_teams(self) -> List[Dict[str, Any]]:
        """
        Discover all configured teams.

        Returns:
            List of team configuration dictionaries
        """
        teams = []

        if hasattr(self.settings, 'teams'):
            for team_name, team_config in self.settings.teams.items():
                team_data = {
                    "name": team_name,
                    "agents": team_config.agents,
                    "max_turns": team_config.max_turns,
                    "type": getattr(team_config, 'type', 'sequential'),
                }
                teams.append(team_data)

        return teams

    def _discover_categories(self) -> Dict[str, List[str]]:
        """
        Discover all categories of agents and tools.

        Returns:
            Dictionary mapping category types to lists of categories
        """
        return {
            "agent_categories": self.agent_registry.get_categories(),
            "tool_categories": self.tool_registry.get_categories(),
        }

    def get_all_capabilities(self) -> Dict[str, Any]:
        """
        Get all system capabilities.

        Returns:
            Complete capability dictionary with agents, tools, teams
        """
        self._ensure_cache()
        return self._cache

    def get_agents(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all agents, optionally filtered by category.

        Args:
            category: Optional category filter

        Returns:
            List of agent dictionaries
        """
        self._ensure_cache()
        agents = self._cache["agents"]

        if category:
            return [a for a in agents if a.get("category") == category]

        return agents

    def get_tools(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all tools, optionally filtered by category.

        Args:
            category: Optional category filter

        Returns:
            List of tool dictionaries
        """
        self._ensure_cache()
        tools = self._cache["tools"]

        if category:
            return [t for t in tools if t.get("category") == category]

        return tools

    def get_teams(self) -> List[Dict[str, Any]]:
        """
        Get all configured teams.

        Returns:
            List of team dictionaries
        """
        self._ensure_cache()
        return self._cache["teams"]

    def get_agent_details(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Agent details dictionary or None if not found
        """
        agents = self.get_agents()
        for agent in agents:
            if agent["name"] == agent_name:
                return agent
        return None

    def get_tool_details(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool details dictionary or None if not found
        """
        tools = self.get_tools()
        for tool in tools:
            if tool["name"] == tool_name:
                return tool
        return None

    def get_team_details(self, team_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific team.

        Args:
            team_name: Name of the team

        Returns:
            Team details dictionary or None if not found
        """
        teams = self.get_teams()
        for team in teams:
            if team["name"] == team_name:
                return team
        return None

    def format_capabilities_for_display(self) -> str:
        """
        Format capabilities in a conversational, user-friendly format for Alfred.

        Returns:
            Formatted string suitable for conversational display
        """
        self._ensure_cache()

        output = []

        # Format agents
        agents = self._cache["agents"]
        if agents:
            output.append("**Agents:**")
            for agent in agents:
                name = agent.get("name", "Unknown")
                description = agent.get("description", "No description")
                output.append(f"- {name}: {description}")

        # Format teams
        teams = self._cache["teams"]
        if teams:
            output.append("\n**Teams:**")
            for team in teams:
                name = team.get("name", "Unknown")
                agents_list = ", ".join(team.get("agents", []))
                output.append(f"- {name}: {agents_list}")

        # Format tools by category
        tools = self._cache["tools"]
        if tools:
            # Group tools by category
            tools_by_category = {}
            for tool in tools:
                category = tool.get("category", "general")
                if category not in tools_by_category:
                    tools_by_category[category] = []
                tools_by_category[category].append(tool)

            output.append("\n**Tools:**")
            for category, category_tools in tools_by_category.items():
                tool_names = [t.get("name", "Unknown") for t in category_tools]
                output.append(f"- {category.title()}: {', '.join(tool_names)}")

        return "\n".join(output)

    def get_recommended_team_for_task(self, task_description: str) -> Optional[str]:
        """
        Recommend a team based on task description (simple keyword matching).

        Args:
            task_description: User's task description

        Returns:
            Recommended team name or None
        """
        task_lower = task_description.lower()

        # Simple keyword-based routing
        if any(word in task_lower for word in ["weather", "forecast", "temperature", "rain"]):
            return "weather_team"

        if any(word in task_lower for word in ["database", "query", "sql", "data", "analyze", "file"]):
            return "data_team"

        if any(word in task_lower for word in ["web", "search", "browse", "research"]):
            return "magentic_one"

        # Default to orchestrator for complex multi-step tasks
        if any(word in task_lower for word in ["complex", "multiple", "steps", "plan"]):
            return "magentic_one"

        return None

    def to_json(self) -> str:
        """
        Export capabilities to JSON string.

        Returns:
            JSON string of all capabilities
        """
        self._ensure_cache()
        return json.dumps(self._cache, indent=2, default=str)

    def __repr__(self) -> str:
        self._ensure_cache()
        return (
            f"CapabilityService("
            f"agents={len(self._cache['agents'])}, "
            f"tools={len(self._cache['tools'])}, "
            f"teams={len(self._cache['teams'])})"
        )

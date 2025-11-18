"""
Yamazaki v2 - Capability Service

Service for managing and querying system capabilities.
Provides information about agents, tools, teams, and system features.
"""

from typing import Dict, List, Any, Optional


class CapabilityService:
    """
    Service for managing system capabilities.

    Provides access to:
    - Available agents
    - Available tools
    - Configured teams
    - System features and capabilities
    """

    def __init__(self, agent_registry, tool_registry):
        """
        Initialize capability service.

        Args:
            agent_registry: AgentRegistry instance
            tool_registry: ToolRegistry instance
        """
        self.agent_registry = agent_registry
        self.tool_registry = tool_registry

    def list_all_capabilities(self) -> Dict[str, Any]:
        """
        List all system capabilities.

        Returns:
            Dict with agents, tools, and teams information
        """
        return {
            "agents": self.list_agents(),
            "tools": self.list_tools(),
            "teams": self.list_teams(),
            "system_info": self.get_system_info()
        }

    def list_agents(self) -> List[Dict[str, Any]]:
        """
        List all available agents.

        Returns:
            List of agent metadata dicts
        """
        return self.agent_registry.list_agents()

    def list_tools(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all available tools.

        Args:
            category: Optional category filter

        Returns:
            List of tool metadata dicts
        """
        return self.tool_registry.list_tools(category=category)

    def list_teams(self) -> List[Dict[str, str]]:
        """
        List all configured teams.

        Returns:
            List of team information
        """
        # For now, return hardcoded teams
        # TODO: Make this dynamic based on team registry
        return [
            {
                "name": "weather_team",
                "description": "Multi-agent team for weather queries with specialized agents",
                "agents": ["weather", "orchestrator"]
            },
            {
                "name": "data_team",
                "description": "Team for data analysis with database and file tools",
                "agents": ["data_analyst"]
            },
            {
                "name": "magentic_one",
                "description": "Web research team with Orchestrator, WebSurfer, and FileWriter",
                "agents": ["orchestrator", "web_surfer", "file_writer"]
            }
        ]

    def get_system_info(self) -> Dict[str, Any]:
        """
        Get system information and stats.

        Returns:
            System information dict
        """
        return {
            "version": "2.0.0",
            "name": "Yamazaki V2",
            "total_agents": len(self.agent_registry.list_agents()),
            "total_tools": len(self.tool_registry.list_tools()),
            "total_teams": len(self.list_teams())
        }

    def get_agent_info(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Agent information or None if not found
        """
        agents = self.agent_registry.list_agents()
        for agent in agents:
            if agent["name"] == agent_name:
                return agent
        return None

    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool information or None if not found
        """
        tools = self.tool_registry.list_tools()
        for tool in tools:
            if tool["name"] == tool_name:
                return tool
        return None

    def search_capabilities(self, query: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search for capabilities matching a query.

        Args:
            query: Search query

        Returns:
            Dict with matching agents, tools, and teams
        """
        query_lower = query.lower()

        matching_agents = [
            agent for agent in self.list_agents()
            if query_lower in agent["name"].lower() or query_lower in agent["description"].lower()
        ]

        matching_tools = [
            tool for tool in self.list_tools()
            if query_lower in tool["name"].lower() or query_lower in tool["description"].lower()
        ]

        matching_teams = [
            team for team in self.list_teams()
            if query_lower in team["name"].lower() or query_lower in team["description"].lower()
        ]

        return {
            "agents": matching_agents,
            "tools": matching_tools,
            "teams": matching_teams
        }

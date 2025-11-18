"""
Yamazaki v2 - Alfred List Capabilities Tool

Allows Alfred to list and explain system capabilities (agents, teams, tools).
"""

from typing import Optional

from ...core.base_tool import BaseTool, ToolResult, ToolCategory


class ListCapabilitiesTool(BaseTool):
    """
    Tool for listing system capabilities.

    Alfred uses this to answer "What can you do?" questions.
    """

    NAME = "alfred.list_capabilities"
    DESCRIPTION = "List available agents, teams, and tools in the Yamazaki system. Use category parameter to filter (agents, tools, teams, or all)."
    CATEGORY = ToolCategory.GENERAL
    VERSION = "1.0.0"
    REQUIRES_SECURITY_VALIDATION = False

    def __init__(self, capability_service):
        """
        Initialize tool with capability service.

        Args:
            capability_service: CapabilityService instance
        """
        super().__init__()
        self.capability_service = capability_service

    async def execute(self, category: str = "all") -> ToolResult:
        """
        List capabilities.

        Args:
            category: Category to list (all, agents, tools, teams)

        Returns:
            ToolResult with formatted capabilities
        """
        try:
            category_lower = category.lower()

            if category_lower == "all":
                # Get all capabilities formatted for display
                formatted = self.capability_service.format_capabilities_for_display()
                return ToolResult.ok({
                    "category": "all",
                    "formatted": formatted,
                    "capabilities": self.capability_service.get_all_capabilities(),
                })

            elif category_lower == "agents":
                agents = self.capability_service.get_agents()
                formatted_agents = self._format_agents(agents)
                return ToolResult.ok({
                    "category": "agents",
                    "formatted": formatted_agents,
                    "agents": agents,
                })

            elif category_lower == "tools":
                tools = self.capability_service.get_tools()
                formatted_tools = self._format_tools(tools)
                return ToolResult.ok({
                    "category": "tools",
                    "formatted": formatted_tools,
                    "tools": tools,
                })

            elif category_lower == "teams":
                teams = self.capability_service.get_teams()
                formatted_teams = self._format_teams(teams)
                return ToolResult.ok({
                    "category": "teams",
                    "formatted": formatted_teams,
                    "teams": teams,
                })

            else:
                return ToolResult.error(
                    f"I'm afraid '{category}' is not a valid category, sir. "
                    f"Please choose from: all, agents, tools, or teams."
                )

        except Exception as e:
            return ToolResult.error(
                f"My apologies, sir. I encountered an issue while retrieving capabilities: {str(e)}"
            )

    def _format_agents(self, agents: list) -> str:
        """Format agents for display."""
        if not agents:
            return "No agents available."

        output = ["**Agents:**"]
        for agent in agents:
            name = agent.get("name", "Unknown")
            description = agent.get("description", "No description")
            tools = agent.get("tools", [])
            tools_str = f" (Tools: {', '.join(tools)})" if tools else ""
            output.append(f"- {name}: {description}{tools_str}")

        return "\n".join(output)

    def _format_tools(self, tools: list) -> str:
        """Format tools for display."""
        if not tools:
            return "No tools available."

        # Group by category
        by_category = {}
        for tool in tools:
            category = tool.get("category", "general")
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(tool)

        output = ["**Tools:**"]
        for category, category_tools in by_category.items():
            output.append(f"\n{category.title()}:")
            for tool in category_tools:
                name = tool.get("name", "Unknown")
                description = tool.get("description", "No description")
                output.append(f"- {name}: {description}")

        return "\n".join(output)

    def _format_teams(self, teams: list) -> str:
        """Format teams for display."""
        if not teams:
            return "No teams configured."

        output = ["**Teams:**"]
        for team in teams:
            name = team.get("name", "Unknown")
            agents = ", ".join(team.get("agents", []))
            max_turns = team.get("max_turns", "N/A")
            output.append(f"- {name}: {agents} (max turns: {max_turns})")

        return "\n".join(output)

    def validate_params(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters."""
        category = kwargs.get("category", "all")

        if not isinstance(category, str):
            return False, "category must be a string"

        valid_categories = ["all", "agents", "tools", "teams"]
        if category.lower() not in valid_categories:
            return False, f"category must be one of: {', '.join(valid_categories)}"

        return True, None

    def _get_parameters_schema(self) -> dict:
        """Get parameters schema."""
        return {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Category to list: all, agents, tools, or teams",
                    "enum": ["all", "agents", "tools", "teams"],
                    "default": "all",
                },
            },
            "required": [],
        }

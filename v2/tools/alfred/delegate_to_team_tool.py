"""
Yamazaki v2 - Alfred Delegate to Team Tool

Allows Alfred to delegate tasks to specific teams with full context hand-off.
"""

from typing import Optional, TYPE_CHECKING

from ...core.base_tool import BaseTool, ToolResult, ToolCategory

if TYPE_CHECKING:
    from ...agents.factory import AgentFactory
    from ...services.capability_service import CapabilityService


class DelegateToTeamTool(BaseTool):
    """
    Tool for delegating tasks to teams.

    Alfred uses this for pure delegation (step aside pattern).
    """

    NAME = "alfred.delegate_to_team"
    DESCRIPTION = "Delegate a task to a specific team (weather_team, data_team, magentic_one). Provide the task description and any relevant context."
    CATEGORY = ToolCategory.GENERAL
    VERSION = "1.0.0"
    REQUIRES_SECURITY_VALIDATION = False

    def __init__(
        self,
        agent_factory: "AgentFactory",
        capability_service: "CapabilityService"
    ) -> None:
        """
        Initialize tool with agent factory and capability service.

        Args:
            agent_factory: AgentFactory instance for creating teams
            capability_service: CapabilityService for team recommendations
        """
        super().__init__()
        self.agent_factory = agent_factory
        self.capability_service = capability_service

    async def execute(
        self,
        team_name: str,
        task: str,
        context: Optional[str] = None,
    ) -> ToolResult:
        """
        Delegate task to a team.

        Args:
            team_name: Name of the team to delegate to
            task: Task description
            context: Optional additional context

        Returns:
            ToolResult with delegation information
        """
        try:
            # Validate services are available
            if not self.agent_factory:
                return ToolResult.error(
                    "My apologies, sir. The agent factory is not currently available."
                )
            if not self.capability_service:
                return ToolResult.error(
                    "My apologies, sir. The capability service is not currently available."
                )

            # Validate team exists
            available_teams = self.agent_factory.list_available_teams()
            if team_name not in available_teams:
                return ToolResult.error(
                    f"I'm afraid the '{team_name}' team is not available, sir. "
                    f"Available teams: {', '.join(available_teams)}"
                )

            # Get team details
            team_details = self.capability_service.get_team_details(team_name)
            if not team_details:
                return ToolResult.error(
                    f"My apologies, sir. I could not retrieve details for the '{team_name}' team."
                )

            # Prepare delegation message
            delegation_message = self._format_delegation_message(
                team_name,
                task,
                context,
                team_details,
            )

            # Return delegation info (actual team execution happens in the CLI/workflow)
            return ToolResult.ok({
                "delegated": True,
                "team_name": team_name,
                "task": task,
                "context": context,
                "team_details": team_details,
                "delegation_message": delegation_message,
                "next_steps": f"Initiating hand-off to {team_name}. You will now interact directly with the team.",
            })

        except Exception as e:
            return ToolResult.error(
                f"My apologies, sir. I encountered an issue while delegating to the team: {str(e)}"
            )

    def _format_delegation_message(
        self,
        team_name: str,
        task: str,
        context: Optional[str],
        team_details: dict,
    ) -> str:
        """
        Format a professional delegation message in Alfred's voice.

        Args:
            team_name: Team name
            task: Task description
            context: Additional context
            team_details: Team details

        Returns:
            Formatted delegation message
        """
        agents = ", ".join(team_details.get("agents", []))

        message_parts = [
            f"Very good. I'll hand this over to the {team_name.replace('_', ' ').title()}.",
            f"They consist of: {agents}.",
            f"\nTask: {task}",
        ]

        if context:
            message_parts.append(f"Context: {context}")

        message_parts.append(
            f"\nI've taken the liberty of preparing all necessary context for the team."
        )
        message_parts.append("They are excellently suited for this task.")

        return "\n".join(message_parts)

    def get_recommended_team(self, task_description: str) -> Optional[str]:
        """
        Get recommended team for a task.

        Args:
            task_description: Task description

        Returns:
            Recommended team name or None
        """
        return self.capability_service.get_recommended_team_for_task(task_description)

    def validate_params(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters."""
        team_name = kwargs.get("team_name")
        task = kwargs.get("task")

        if not team_name:
            return False, "team_name is required"

        if not isinstance(team_name, str):
            return False, "team_name must be a string"

        if not task:
            return False, "task is required"

        if not isinstance(task, str):
            return False, "task must be a string"

        context = kwargs.get("context")
        if context is not None and not isinstance(context, str):
            return False, "context must be a string"

        return True, None

    def _get_parameters_schema(self) -> dict:
        """Get parameters schema."""
        return {
            "type": "object",
            "properties": {
                "team_name": {
                    "type": "string",
                    "description": "Name of the team to delegate to (e.g., weather_team, data_team, magentic_one)",
                },
                "task": {
                    "type": "string",
                    "description": "Clear description of the task to be performed",
                },
                "context": {
                    "type": "string",
                    "description": "Additional context or background information for the team",
                },
            },
            "required": ["team_name", "task"],
        }

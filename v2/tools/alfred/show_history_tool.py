"""
Yamazaki v2 - Alfred Show History Tool

Allows Alfred to show recent actions, conversation history, and tool executions.
"""

from typing import Optional
from datetime import datetime, timedelta

from ...core.base_tool import BaseTool, ToolResult, ToolCategory


class ShowHistoryTool(BaseTool):
    """
    Tool for showing conversation and action history.

    Alfred uses this to answer "What were my last actions?" questions.
    """

    NAME = "alfred.show_history"
    DESCRIPTION = "Show recent actions, conversations, and tool executions. Use scope='session' for current session or scope='recent' for last N actions. Set limit to control number of items."
    CATEGORY = ToolCategory.GENERAL
    VERSION = "1.0.0"
    REQUIRES_SECURITY_VALIDATION = False

    def __init__(self, history_service):
        """
        Initialize tool with history service.

        Args:
            history_service: HistoryService instance
        """
        super().__init__()
        self.history_service = history_service

    async def execute(
        self,
        scope: str = "recent",
        limit: int = 5,
        include_details: bool = False,
    ) -> ToolResult:
        """
        Show history.

        Args:
            scope: Scope of history (recent, session, all)
            limit: Maximum number of items to show
            include_details: Include detailed information

        Returns:
            ToolResult with formatted history
        """
        try:
            scope_lower = scope.lower()

            if scope_lower == "recent":
                # Get recent actions
                history = self.history_service.get_recent_actions(limit=limit)
                formatted = self.history_service.format_history_for_display(
                    history,
                    include_details=include_details,
                )

                return ToolResult.ok({
                    "scope": "recent",
                    "count": len(history),
                    "formatted": formatted,
                    "history": history,
                })

            elif scope_lower == "session":
                # Get current session history
                session = self.history_service.get_session_history(
                    session_duration_minutes=60
                )
                formatted = self.history_service.format_session_history(session)

                return ToolResult.ok({
                    "scope": "session",
                    "formatted": formatted,
                    "session": session,
                })

            elif scope_lower == "all":
                # Get all recent history (larger limit)
                history = self.history_service.get_recent_actions(limit=limit * 2)
                formatted = self.history_service.format_history_for_display(
                    history,
                    include_details=include_details,
                )

                return ToolResult.ok({
                    "scope": "all",
                    "count": len(history),
                    "formatted": formatted,
                    "history": history,
                })

            else:
                return ToolResult.error(
                    f"Invalid scope '{scope}'. Must be: recent, session, or all"
                )

        except Exception as e:
            return ToolResult.error(f"Failed to show history: {str(e)}")

    def validate_params(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters."""
        scope = kwargs.get("scope", "recent")
        limit = kwargs.get("limit", 5)
        include_details = kwargs.get("include_details", False)

        if not isinstance(scope, str):
            return False, "scope must be a string"

        valid_scopes = ["recent", "session", "all"]
        if scope.lower() not in valid_scopes:
            return False, f"scope must be one of: {', '.join(valid_scopes)}"

        if not isinstance(limit, int):
            return False, "limit must be an integer"

        if limit < 1 or limit > 100:
            return False, "limit must be between 1 and 100"

        if not isinstance(include_details, bool):
            return False, "include_details must be a boolean"

        return True, None

    def _get_parameters_schema(self) -> dict:
        """Get parameters schema."""
        return {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "description": "Scope of history: recent (last N actions), session (current session), or all",
                    "enum": ["recent", "session", "all"],
                    "default": "recent",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of items to show (1-100)",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 5,
                },
                "include_details": {
                    "type": "boolean",
                    "description": "Include detailed information about each item",
                    "default": False,
                },
            },
            "required": [],
        }

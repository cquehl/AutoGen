"""
MCP Error Hierarchy

Defines comprehensive error types for MCP operations.
All MCP errors inherit from MCPError base class.
"""

from typing import Optional, List
from ..errors import SuntoryError


class MCPError(SuntoryError):
    """
    Base class for all MCP-related errors.

    Attributes:
        message: Error message
        recovery_suggestions: List of suggestions for resolving the error
        original_error: Original exception if this wraps another error
    """

    def __init__(
        self,
        message: str,
        recovery_suggestions: Optional[List[str]] = None,
        original_error: Optional[Exception] = None
    ):
        self.message = message
        self.recovery_suggestions = recovery_suggestions or []
        self.original_error = original_error
        super().__init__(message)

    def __str__(self) -> str:
        msg = self.message
        if self.recovery_suggestions:
            suggestions = "\n  ".join(self.recovery_suggestions)
            msg += f"\n\nRecovery suggestions:\n  {suggestions}"
        return msg


class MCPConnectionError(MCPError):
    """
    Errors related to MCP server connections.

    Examples:
        - Failed to connect to server
        - Connection timeout
        - Connection lost during operation
    """

    def __init__(self, message: str, server_id: Optional[str] = None, **kwargs):
        self.server_id = server_id
        if server_id:
            message = f"[{server_id}] {message}"
        super().__init__(message, **kwargs)


class MCPTimeoutError(MCPError):
    """
    Errors related to operation timeouts.

    Examples:
        - Tool execution timeout
        - Connection timeout
        - Health check timeout
    """

    def __init__(
        self,
        message: str,
        timeout_seconds: Optional[float] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        self.timeout_seconds = timeout_seconds
        self.operation = operation

        if timeout_seconds and operation:
            message = f"{operation} timed out after {timeout_seconds}s: {message}"
        elif timeout_seconds:
            message = f"Timeout after {timeout_seconds}s: {message}"

        super().__init__(message, **kwargs)


class MCPSecurityError(MCPError):
    """
    Security-related errors.

    Examples:
        - Command injection attempt detected
        - Path traversal attempt
        - Forbidden directory access
        - Dangerous environment variable
    """

    def __init__(self, message: str, recovery_suggestion: Optional[str] = None, **kwargs):
        suggestions = kwargs.pop("recovery_suggestions", [])
        if recovery_suggestion:
            suggestions.insert(0, recovery_suggestion)
        super().__init__(message, recovery_suggestions=suggestions, **kwargs)


class MCPValidationError(MCPError):
    """
    Input validation errors.

    Examples:
        - Missing required parameter
        - Invalid parameter type
        - Parameter value out of range
        - Unknown tool name
    """

    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        expected_type: Optional[type] = None,
        actual_value: Optional[any] = None,
        **kwargs
    ):
        self.field_name = field_name
        self.expected_type = expected_type
        self.actual_value = actual_value

        if field_name and expected_type:
            message = f"Validation failed for '{field_name}': {message} (expected {expected_type.__name__})"

        super().__init__(message, **kwargs)


class MCPServerError(MCPError):
    """
    Server lifecycle errors.

    Examples:
        - Failed to start server
        - Server crashed
        - Failed to restart server
        - Server process not responding
    """

    def __init__(
        self,
        message: str,
        server_id: Optional[str] = None,
        process_id: Optional[int] = None,
        **kwargs
    ):
        self.server_id = server_id
        self.process_id = process_id

        if server_id:
            message = f"[{server_id}] {message}"
        if process_id:
            message += f" (PID: {process_id})"

        super().__init__(message, **kwargs)


class MCPConfigurationError(MCPError):
    """
    Configuration-related errors.

    Examples:
        - Invalid server configuration
        - Missing required configuration
        - Conflicting configuration settings
    """

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        **kwargs
    ):
        self.config_key = config_key

        if config_key:
            message = f"Configuration error for '{config_key}': {message}"

        super().__init__(message, **kwargs)


class MCPOperationError(MCPError):
    """
    Errors during MCP operations.

    Examples:
        - Tool execution failed
        - Tool discovery failed
        - Resource operation failed
    """

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        tool_name: Optional[str] = None,
        **kwargs
    ):
        self.operation = operation
        self.tool_name = tool_name

        if tool_name:
            message = f"Tool '{tool_name}': {message}"
        if operation:
            message = f"{operation} failed - {message}"

        super().__init__(message, **kwargs)


class MCPRateLimitError(MCPError):
    """
    Rate limiting errors.

    Examples:
        - Agent exceeded rate limit
        - Server rate limit reached
        - Too many concurrent requests
    """

    def __init__(
        self,
        message: str,
        agent_name: Optional[str] = None,
        limit: Optional[int] = None,
        window_seconds: Optional[int] = None,
        **kwargs
    ):
        self.agent_name = agent_name
        self.limit = limit
        self.window_seconds = window_seconds

        if agent_name and limit and window_seconds:
            message = (
                f"Rate limit exceeded for {agent_name}: "
                f"{limit} requests per {window_seconds}s"
            )

        super().__init__(
            message,
            recovery_suggestions=kwargs.pop("recovery_suggestions", [
                "Wait before retrying",
                "Reduce request rate",
                "Check rate limit configuration"
            ]),
            **kwargs
        )


class MCPToolNotFoundError(MCPError):
    """
    Tool not found errors.

    Examples:
        - Requested tool doesn't exist
        - Tool not available on any connected server
    """

    def __init__(self, tool_name: str, available_tools: Optional[List[str]] = None, **kwargs):
        self.tool_name = tool_name
        self.available_tools = available_tools or []

        message = f"Tool not found: {tool_name}"

        suggestions = kwargs.pop("recovery_suggestions", [])
        if available_tools:
            suggestions.append(f"Available tools: {', '.join(available_tools[:10])}")
        if not suggestions:
            suggestions.append("Check tool name spelling")
            suggestions.append("Ensure server providing this tool is connected")

        super().__init__(message, recovery_suggestions=suggestions, **kwargs)


class MCPPermissionError(MCPError):
    """
    Permission and authorization errors.

    Examples:
        - Agent not authorized to use tool
        - Agent not authorized to access server
        - Operation requires elevated permissions
    """

    def __init__(
        self,
        message: str,
        agent_name: Optional[str] = None,
        resource: Optional[str] = None,
        **kwargs
    ):
        self.agent_name = agent_name
        self.resource = resource

        if agent_name and resource:
            message = f"Agent '{agent_name}' not authorized to access '{resource}'"

        super().__init__(
            message,
            recovery_suggestions=kwargs.pop("recovery_suggestions", [
                "Check agent permissions configuration",
                "Contact administrator for access"
            ]),
            **kwargs
        )

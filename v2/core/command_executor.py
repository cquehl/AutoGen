"""
Command Executor - Abstraction for executing system commands

This provides a clean abstraction for command execution, allowing tools
to execute commands without tight coupling to BashTool.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict
from dataclasses import dataclass


@dataclass
class CommandResult:
    """Result of command execution"""
    success: bool
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0
    execution_time_ms: float = 0.0
    error: Optional[str] = None


class CommandExecutor(ABC):
    """
    Abstract interface for executing system commands.

    This abstraction allows tools to execute commands without
    depending directly on BashTool, enabling:
    - Better testability (mock implementations)
    - Alternative implementations (SSH, Docker, etc.)
    - Cleaner separation of concerns
    """

    @abstractmethod
    async def execute(
        self,
        command: str,
        timeout: Optional[int] = None,
        working_dir: Optional[str] = None,
        capture_output: bool = True,
        **kwargs
    ) -> CommandResult:
        """
        Execute a command.

        Args:
            command: Command to execute
            timeout: Timeout in seconds
            working_dir: Working directory for execution
            capture_output: Whether to capture stdout/stderr
            **kwargs: Additional executor-specific parameters

        Returns:
            CommandResult with execution details
        """
        pass

    @abstractmethod
    def validate_command(self, command: str) -> tuple[bool, Optional[str]]:
        """
        Validate a command before execution.

        Args:
            command: Command to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        pass


class BashCommandExecutor(CommandExecutor):
    """
    Execute commands via bash/shell using BashTool.

    This is a bridge that allows BashTool to implement the
    CommandExecutor interface.
    """

    def __init__(self, bash_tool):
        """
        Initialize with a BashTool instance.

        Args:
            bash_tool: BashTool instance for execution
        """
        self.bash_tool = bash_tool

    async def execute(
        self,
        command: str,
        timeout: Optional[int] = None,
        working_dir: Optional[str] = None,
        capture_output: bool = True,
        **kwargs
    ) -> CommandResult:
        """Execute command via BashTool"""
        # Execute via BashTool
        result = await self.bash_tool.execute(
            command=command,
            timeout=timeout,
            working_dir=working_dir,
            capture_output=capture_output,
        )

        if not result.success:
            return CommandResult(
                success=False,
                error=result.error,
            )

        # Convert ToolResult to CommandResult
        data = result.data or {}
        return CommandResult(
            success=data.get('success', False),
            stdout=data.get('stdout', ''),
            stderr=data.get('stderr', ''),
            return_code=data.get('return_code', -1),
            execution_time_ms=result.metadata.get('execution_time_ms', 0.0) if result.metadata else 0.0,
        )

    def validate_command(self, command: str) -> tuple[bool, Optional[str]]:
        """Validate command via BashTool"""
        return self.bash_tool.validate_params(command=command)


class MockCommandExecutor(CommandExecutor):
    """
    Mock command executor for testing.

    Allows tests to simulate command execution without
    actually running commands.
    """

    def __init__(self, mock_responses: Optional[Dict[str, CommandResult]] = None):
        """
        Initialize with mock responses.

        Args:
            mock_responses: Dict mapping commands to CommandResults
        """
        self.mock_responses = mock_responses or {}
        self.executed_commands = []

    async def execute(
        self,
        command: str,
        timeout: Optional[int] = None,
        working_dir: Optional[str] = None,
        capture_output: bool = True,
        **kwargs
    ) -> CommandResult:
        """Return mock response"""
        self.executed_commands.append(command)

        # Return mock response if configured
        if command in self.mock_responses:
            return self.mock_responses[command]

        # Default successful response
        return CommandResult(
            success=True,
            stdout=f"Mock output for: {command}",
            stderr="",
            return_code=0,
        )

    def validate_command(self, command: str) -> tuple[bool, Optional[str]]:
        """Mock validation - always succeeds"""
        return True, None

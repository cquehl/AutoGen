"""
Bash Tool - Execute shell commands with security controls
"""

import asyncio
import subprocess
from typing import Optional, Dict, Any
from ...core.base_tool import BaseTool, ToolResult, ToolCategory
from ...security.middleware import Operation, OperationType


class BashTool(BaseTool):
    """
    Execute bash commands with security controls.

    Features:
    - Command execution with timeout
    - Security validation via middleware
    - Audit logging
    - Output capture (stdout + stderr)
    - Working directory support
    """

    NAME = "shell.bash"
    DESCRIPTION = "Execute bash commands with security controls and timeout"
    CATEGORY = ToolCategory.SHELL
    VERSION = "1.0.0"
    REQUIRES_SECURITY_VALIDATION = True

    def __init__(self, security_middleware, **kwargs):
        """
        Initialize bash tool.

        Args:
            security_middleware: Security middleware for validation
            **kwargs: Additional configuration
        """
        super().__init__(**kwargs)
        self.security_middleware = security_middleware
        self.default_timeout = kwargs.get('default_timeout', 120)
        self.max_timeout = kwargs.get('max_timeout', 600)  # 10 minutes max

    async def execute(
        self,
        command: str,
        timeout: Optional[int] = None,
        working_dir: Optional[str] = None,
        capture_output: bool = True,
    ) -> ToolResult:
        """
        Execute bash command.

        Args:
            command: Shell command to execute
            timeout: Timeout in seconds (default: 120, max: 600)
            working_dir: Working directory for command execution
            capture_output: Capture stdout/stderr (default: True)

        Returns:
            ToolResult with command output
        """
        # Determine timeout
        timeout = timeout or self.default_timeout
        timeout = min(timeout, self.max_timeout)

        # Create operation for security middleware
        operation = Operation(
            type=OperationType.SHELL_COMMAND,
            params={
                "command": command,
                "allow_pipes": True,
                "allow_chaining": True,
            },
            executor=self._execute_command,
            timeout=timeout,
        )

        # Add execution params
        operation.params.update({
            "working_dir": working_dir,
            "capture_output": capture_output,
            "actual_timeout": timeout,
        })

        # Execute via security middleware
        result = await self.security_middleware.validate_and_execute(operation)

        if result.blocked:
            return ToolResult.error(
                f"Command blocked by security policy: {result.error}"
            )

        if not result.success:
            return ToolResult.error(result.error)

        return ToolResult.ok(
            data=result.data,
            metadata={"execution_time_ms": result.execution_time_ms}
        )

    async def _execute_command(
        self,
        command: str,
        working_dir: Optional[str],
        capture_output: bool,
        actual_timeout: int,
        **kwargs  # Ignore validation params
    ) -> Dict[str, Any]:
        """
        Internal command execution.

        Args:
            command: Command to execute
            working_dir: Working directory
            capture_output: Whether to capture output
            actual_timeout: Timeout in seconds

        Returns:
            Dict with stdout, stderr, return_code
        """
        try:
            # Create subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=subprocess.PIPE if capture_output else None,
                stderr=subprocess.PIPE if capture_output else None,
                cwd=working_dir,
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=actual_timeout
                )
            except asyncio.TimeoutError:
                # Kill process on timeout
                process.kill()
                await process.wait()
                raise TimeoutError(f"Command timed out after {actual_timeout}s")

            # Decode output
            stdout_str = stdout.decode('utf-8', errors='replace') if stdout else ""
            stderr_str = stderr.decode('utf-8', errors='replace') if stderr else ""

            return {
                "stdout": stdout_str,
                "stderr": stderr_str,
                "return_code": process.returncode,
                "success": process.returncode == 0,
            }

        except Exception as e:
            raise Exception(f"Command execution failed: {str(e)}")

    def validate_params(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters"""
        command = kwargs.get("command")

        if not command:
            return False, "command is required"

        if not isinstance(command, str):
            return False, "command must be a string"

        timeout = kwargs.get("timeout")
        if timeout is not None:
            if not isinstance(timeout, (int, float)):
                return False, "timeout must be a number"
            if timeout <= 0:
                return False, "timeout must be positive"
            if timeout > self.max_timeout:
                return False, f"timeout cannot exceed {self.max_timeout} seconds"

        working_dir = kwargs.get("working_dir")
        if working_dir is not None:
            if not isinstance(working_dir, str):
                return False, "working_dir must be a string"

        return True, None

    def _get_parameters_schema(self) -> Dict[str, Any]:
        """Get parameters schema"""
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute",
                },
                "timeout": {
                    "type": "integer",
                    "description": f"Timeout in seconds (max: {self.max_timeout})",
                    "minimum": 1,
                    "maximum": self.max_timeout,
                    "default": self.default_timeout,
                },
                "working_dir": {
                    "type": "string",
                    "description": "Working directory for command execution (optional)",
                },
                "capture_output": {
                    "type": "boolean",
                    "description": "Capture stdout and stderr (default: true)",
                    "default": True,
                },
            },
            "required": ["command"],
        }

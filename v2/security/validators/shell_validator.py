"""
Shell Command Validator

Validates shell commands for security issues.
"""

from typing import Optional, List
from dataclasses import dataclass


@dataclass
class ShellValidationResult:
    """Result of shell command validation"""
    is_valid: bool
    error: Optional[str] = None
    warning: Optional[str] = None
    query_type: Optional[str] = None


class ShellValidator:
    """
    Validates shell commands for security issues.

    Prevents:
    - Destructive commands without confirmation
    - Command injection patterns
    - Resource exhaustion attacks
    """

    # Commands that are always blocked
    BLOCKED_COMMANDS = [
        "rm -rf /",
        "mkfs",
        "dd if=/dev/zero",
        ":(){ :|:& };:",  # Fork bomb
        "chmod -R 777 /",
    ]

    # Commands that require extra validation
    DANGEROUS_COMMANDS = [
        "rm", "rmdir", "dd", "mkfs",
        "fdisk", "parted", "format",
        "shutdown", "reboot", "halt",
    ]

    # Patterns that suggest injection attempts
    INJECTION_PATTERNS = [
        ";", "&&", "||", "|", "`", "$(",
        "\n", "\r", "$(", "${",
    ]

    def __init__(self, config):
        """
        Initialize validator.

        Args:
            config: SecurityConfig with shell settings
        """
        self.config = config
        self.enable_dangerous_commands = getattr(
            config, 'allow_dangerous_shell_commands', False
        )

    def validate(
        self,
        command: str,
        allow_pipes: bool = True,
        allow_chaining: bool = True,
    ) -> ShellValidationResult:
        """
        Validate shell command.

        Args:
            command: Shell command to validate
            allow_pipes: Allow pipe operators (|)
            allow_chaining: Allow command chaining (&&, ||, ;)

        Returns:
            ShellValidationResult
        """
        if not command or not command.strip():
            return ShellValidationResult(
                is_valid=False,
                error="Command cannot be empty"
            )

        command_lower = command.lower().strip()

        # Check for blocked commands
        for blocked in self.BLOCKED_COMMANDS:
            if blocked in command_lower:
                return ShellValidationResult(
                    is_valid=False,
                    error=f"Blocked command pattern detected: {blocked}"
                )

        # Check config-based blocked commands
        config_blocked = getattr(self.config, 'blocked_shell_commands', [])
        for blocked in config_blocked:
            if blocked.lower() in command_lower:
                return ShellValidationResult(
                    is_valid=False,
                    error=f"Blocked command pattern detected: {blocked}"
                )

        # Check for dangerous commands
        if not self.enable_dangerous_commands:
            for dangerous in self.DANGEROUS_COMMANDS:
                if command_lower.startswith(dangerous + " ") or command_lower == dangerous:
                    return ShellValidationResult(
                        is_valid=False,
                        error=f"Dangerous command '{dangerous}' is not allowed. "
                               f"Enable dangerous commands in config if needed."
                    )

        # Check for command injection patterns
        has_injection_risk = False
        injection_chars = []

        for pattern in self.INJECTION_PATTERNS:
            if pattern in command:
                # Allow pipes if explicitly allowed
                if pattern == "|" and allow_pipes:
                    continue
                # Allow chaining if explicitly allowed
                if pattern in ["&&", "||", ";"] and allow_chaining:
                    continue

                has_injection_risk = True
                injection_chars.append(pattern)

        if has_injection_risk:
            return ShellValidationResult(
                is_valid=False,
                error=f"Potential command injection detected. "
                      f"Unsafe characters: {', '.join(repr(c) for c in injection_chars)}"
            )

        # Command looks safe
        return ShellValidationResult(
            is_valid=True,
            query_type=self._detect_command_type(command)
        )

    def _detect_command_type(self, command: str) -> str:
        """Detect the type of command (read, write, execute)"""
        command_lower = command.lower().strip()

        # Read operations
        if any(command_lower.startswith(cmd) for cmd in ["ls", "cat", "grep", "find", "head", "tail"]):
            return "read"

        # Write operations
        if any(command_lower.startswith(cmd) for cmd in ["mkdir", "touch", "cp", "mv", "echo >"]):
            return "write"

        # Package management
        if any(cmd in command_lower for cmd in ["pip install", "npm install", "apt install", "brew install"]):
            return "package_install"

        # Build operations
        if any(command_lower.startswith(cmd) for cmd in ["make", "cargo build", "npm run", "pytest"]):
            return "build"

        # Git operations
        if command_lower.startswith("git "):
            return "git"

        return "execute"

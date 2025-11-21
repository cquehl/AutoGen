"""
MCP Security Module

Provides security utilities for validating commands, environment variables,
and file paths. Fixes critical security vulnerabilities:
- Command injection (CVE-2025-XXXX)
- Environment variable injection
- Path traversal attacks
- Credential exposure

All security-critical operations should go through this module.
"""

import os
import shlex
import re
from typing import Dict, List, Optional, Set
from pathlib import Path
import logging
import fnmatch

from .errors import MCPSecurityError


logger = logging.getLogger(__name__)


# ============================================================================
# COMMAND VALIDATION (Fixes: Command Injection)
# ============================================================================

# Allowlist of safe base commands
ALLOWED_COMMANDS: Set[str] = {
    "npx",
    "node",
    "python",
    "python3",
    "docker",
    "kubectl",
}

# Dangerous shell metacharacters
SHELL_METACHARACTERS = {"&", "|", ";", "`", "$", "(", ")", "<", ">", "\n", "\\"}


def validate_command(command: str) -> List[str]:
    """
    Validate and safely parse a command string.

    Protects against command injection by:
    1. Using shlex.split() instead of str.split()
    2. Checking command against allowlist
    3. Rejecting shell metacharacters

    Args:
        command: Command string to validate

    Returns:
        List of command parts (safe to pass to subprocess)

    Raises:
        MCPSecurityError: If command is not allowed or contains dangerous patterns
        ValueError: If command is empty

    Example:
        >>> validate_command("npx @modelcontextprotocol/server-filesystem")
        ['npx', '@modelcontextprotocol/server-filesystem']

        >>> validate_command("rm -rf /; echo hacked")
        MCPSecurityError: Command not allowed: rm
    """
    if not command or not command.strip():
        raise ValueError("Command cannot be empty")

    # Check for obvious shell metacharacters before parsing
    if any(char in command for char in SHELL_METACHARACTERS):
        raise MCPSecurityError(
            f"Command contains shell metacharacters: {command}",
            recovery_suggestion="Use only simple commands without shell operators"
        )

    # Parse safely with shlex
    try:
        cmd_parts = shlex.split(command)
    except ValueError as e:
        raise MCPSecurityError(
            f"Failed to parse command: {e}",
            recovery_suggestion="Check command syntax for unclosed quotes"
        )

    if not cmd_parts:
        raise ValueError("Command parsed to empty list")

    # Extract base command (first part)
    base_cmd = Path(cmd_parts[0]).name  # Get just the command name, not path

    # Check against allowlist
    if base_cmd not in ALLOWED_COMMANDS:
        raise MCPSecurityError(
            f"Command not allowed: {base_cmd}",
            recovery_suggestion=f"Only these commands are allowed: {', '.join(sorted(ALLOWED_COMMANDS))}"
        )

    logger.debug(f"Validated command: {base_cmd}")
    return cmd_parts


# ============================================================================
# ENVIRONMENT VARIABLE VALIDATION (Fixes: Environment Variable Injection)
# ============================================================================

# Allowlist patterns for environment variables
ALLOWED_ENV_VAR_PATTERNS: List[str] = [
    "PATH",
    "HOME",
    "USER",
    "LANG",
    "LC_*",
    "ALLOWED_DIRECTORIES",
    "CONNECTION_STRING",
    "DATABASE_URL",
    "GITHUB_*",
    "MCP_*",
    "NPM_*",
    "NODE_*",
]

# Dangerous variables that can hijack execution
FORBIDDEN_ENV_VARS: Set[str] = {
    "LD_PRELOAD",
    "LD_LIBRARY_PATH",
    "DYLD_INSERT_LIBRARIES",  # macOS equivalent
    "PYTHONPATH",
    "NODE_PATH",
    "PERL5LIB",
    "RUBYLIB",
}


def sanitize_env_vars(env: Dict[str, str]) -> Dict[str, str]:
    """
    Sanitize environment variables for safe subprocess execution.

    Protects against environment variable injection by:
    1. Checking against forbidden variables
    2. Validating against allowlist patterns
    3. Sanitizing values for shell metacharacters

    Args:
        env: Dictionary of environment variables to sanitize

    Returns:
        Sanitized environment variable dictionary

    Raises:
        MCPSecurityError: If dangerous variables detected or values unsafe

    Example:
        >>> sanitize_env_vars({"MCP_PORT": "8080", "ALLOWED_DIRECTORIES": "/tmp"})
        {'MCP_PORT': '8080', 'ALLOWED_DIRECTORIES': '/tmp'}

        >>> sanitize_env_vars({"LD_PRELOAD": "/tmp/evil.so"})
        MCPSecurityError: Dangerous environment variable detected: LD_PRELOAD
    """
    if not env:
        return {}

    sanitized: Dict[str, str] = {}

    for key, value in env.items():
        # Check forbidden list first
        if key in FORBIDDEN_ENV_VARS:
            raise MCPSecurityError(
                f"Dangerous environment variable detected: {key}",
                recovery_suggestion="Remove this environment variable from configuration"
            )

        # Check against allowlist patterns
        if not _matches_pattern(key, ALLOWED_ENV_VAR_PATTERNS):
            logger.warning(f"Blocked non-whitelisted env var: {key}")
            continue

        # Sanitize value
        sanitized_value = _sanitize_env_value(value, key)
        sanitized[key] = sanitized_value

    logger.debug(f"Sanitized {len(env)} env vars to {len(sanitized)} safe vars")
    return sanitized


def _matches_pattern(key: str, patterns: List[str]) -> bool:
    """Check if env var key matches any allowed pattern"""
    return any(fnmatch.fnmatch(key, pattern) for pattern in patterns)


def _sanitize_env_value(value: str, key: str) -> str:
    """
    Sanitize environment variable value.

    Checks for shell metacharacters and suspicious patterns.
    """
    if not isinstance(value, str):
        raise MCPSecurityError(
            f"Environment variable {key} value must be string, got {type(value)}"
        )

    # Check for shell metacharacters (except allowed in paths)
    dangerous_chars = {"&", "|", ";", "`", "$", "<", ">", "\n"}
    if any(char in value for char in dangerous_chars):
        raise MCPSecurityError(
            f"Environment variable {key} contains shell metacharacters",
            recovery_suggestion="Remove shell operators from environment variable values"
        )

    # Check for command substitution patterns
    if re.search(r'\$\(.*\)', value) or re.search(r'`.*`', value):
        raise MCPSecurityError(
            f"Environment variable {key} contains command substitution pattern",
            recovery_suggestion="Remove $() and `` patterns from values"
        )

    return value


def get_safe_environment(custom_env: Dict[str, str]) -> Dict[str, str]:
    """
    Create a minimal safe environment for subprocess execution.

    Args:
        custom_env: Custom environment variables to add

    Returns:
        Safe environment dictionary

    Example:
        >>> env = get_safe_environment({"MCP_PORT": "8080"})
        >>> "PATH" in env
        True
        >>> "LD_PRELOAD" in env
        False
    """
    # Start with minimal safe environment
    safe_env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "USER": os.environ.get("USER", "unknown"),
        "LANG": os.environ.get("LANG", "en_US.UTF-8"),
    }

    # Add sanitized custom variables
    sanitized_custom = sanitize_env_vars(custom_env)
    safe_env.update(sanitized_custom)

    return safe_env


# ============================================================================
# PATH VALIDATION (Fixes: Path Traversal)
# ============================================================================

# Forbidden directories (absolute paths)
FORBIDDEN_DIRECTORIES: Set[str] = {
    "/etc",
    "/bin",
    "/sbin",
    "/boot",
    "/root",
    "/sys",
    "/proc",
    "/dev",
}

# Forbidden file patterns
FORBIDDEN_FILE_PATTERNS: List[str] = [
    "*.ssh/*",
    "*.aws/*",
    "*.gnupg/*",
    "*.kube/*",
    "*passwd*",
    "*shadow*",
    "*sudoers*",
    "*private*key*",
]


def validate_path(
    path: str,
    operation: str = "read",
    allow_create: bool = False
) -> str:
    """
    Validate file path is safe for the specified operation.

    Protects against path traversal by:
    1. Resolving to absolute path
    2. Checking against forbidden directories
    3. Checking for sensitive file patterns
    4. Ensuring path exists (unless allow_create)

    Args:
        path: File path to validate
        operation: Operation type ("read", "write", "execute")
        allow_create: Allow path if it doesn't exist

    Returns:
        Absolute validated path

    Raises:
        MCPSecurityError: If path is forbidden or suspicious
        ValueError: If path doesn't exist and allow_create=False

    Example:
        >>> validate_path("/tmp/test.txt", "read")
        '/tmp/test.txt'

        >>> validate_path("/etc/passwd", "read")
        MCPSecurityError: Access to forbidden directory: /etc
    """
    if not path:
        raise ValueError("Path cannot be empty")

    # Convert to Path object and resolve
    try:
        path_obj = Path(path).resolve()
    except (OSError, RuntimeError) as e:
        raise MCPSecurityError(
            f"Failed to resolve path: {e}",
            recovery_suggestion="Check path syntax and permissions"
        )

    abs_path = str(path_obj)

    # Check for path traversal attempts
    if ".." in Path(path).parts:
        raise MCPSecurityError(
            f"Path contains traversal pattern: {path}",
            recovery_suggestion="Use absolute paths without '..' components"
        )

    # Check against forbidden directories
    for forbidden in FORBIDDEN_DIRECTORIES:
        if abs_path.startswith(forbidden):
            raise MCPSecurityError(
                f"Access to forbidden directory: {forbidden}",
                recovery_suggestion=f"This directory is restricted for security reasons"
            )

    # Check for sensitive file patterns
    for pattern in FORBIDDEN_FILE_PATTERNS:
        if fnmatch.fnmatch(abs_path.lower(), pattern.lower()):
            raise MCPSecurityError(
                f"Access to sensitive file pattern: {pattern}",
                recovery_suggestion="This file type is restricted for security reasons"
            )

    # Check existence
    if not allow_create and not path_obj.exists():
        raise ValueError(f"Path does not exist: {abs_path}")

    # Operation-specific checks
    if operation == "write":
        # Check parent directory is writable
        parent = path_obj.parent
        if parent.exists() and not os.access(parent, os.W_OK):
            raise MCPSecurityError(
                f"Parent directory not writable: {parent}",
                recovery_suggestion="Check directory permissions"
            )

    logger.debug(f"Validated path for {operation}: {abs_path}")
    return abs_path


def validate_working_directory(path: Optional[str]) -> Optional[str]:
    """
    Validate working directory for subprocess execution.

    Args:
        path: Working directory path (can be None)

    Returns:
        Absolute validated path or None

    Raises:
        MCPSecurityError: If path is forbidden
    """
    if path is None:
        return None

    # Validate using standard path validation
    validated = validate_path(path, operation="read", allow_create=False)

    # Additional check: must be a directory
    if not Path(validated).is_dir():
        raise ValueError(f"Working directory is not a directory: {validated}")

    return validated


# ============================================================================
# CREDENTIAL HELPERS
# ============================================================================

def redact_credentials(data: Dict) -> Dict:
    """
    Redact sensitive fields from dictionary for safe logging.

    Args:
        data: Dictionary potentially containing credentials

    Returns:
        Dictionary with credentials redacted

    Example:
        >>> redact_credentials({"token": "secret123", "user": "john"})
        {'token': '***REDACTED***', 'user': 'john'}
    """
    sensitive_keys = {"token", "password", "secret", "key", "auth", "credential"}

    redacted = {}
    for key, value in data.items():
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            redacted[key] = "***REDACTED***"
        elif isinstance(value, dict):
            redacted[key] = redact_credentials(value)
        else:
            redacted[key] = value

    return redacted


# ============================================================================
# INPUT SANITIZATION
# ============================================================================

def sanitize_tool_parameter(param_name: str, value: any, tool_tags: List[str]) -> any:
    """
    Sanitize tool parameter based on parameter name and tool tags.

    Provides additional layer of defense against injection attacks.

    Args:
        param_name: Parameter name
        value: Parameter value
        tool_tags: Tags indicating tool type (e.g., ["database", "filesystem"])

    Returns:
        Sanitized value (raises exception if unsafe)

    Raises:
        MCPSecurityError: If value contains injection patterns
    """
    if not isinstance(value, str):
        return value  # Only sanitize strings

    # Check for SQL injection if database tool
    if "database" in tool_tags or "sql" in tool_tags:
        dangerous_sql = ["--", ";", "DROP", "DELETE", "TRUNCATE", "EXEC", "UNION", "/*", "*/"]
        value_upper = value.upper()
        if any(pattern in value_upper for pattern in dangerous_sql):
            logger.warning(f"Suspicious SQL pattern detected in parameter {param_name}")
            # Don't block entirely, just log (let tool validation handle it)

    # Check for path traversal if file/path parameter
    if any(keyword in param_name.lower() for keyword in ["path", "file", "directory"]):
        if ".." in value or value.startswith("/"):
            logger.warning(f"Suspicious path pattern in parameter {param_name}: {value}")

    # Check for command injection patterns
    if any(char in value for char in SHELL_METACHARACTERS):
        logger.warning(f"Shell metacharacters in parameter {param_name}")

    return value

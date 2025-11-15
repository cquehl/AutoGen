"""
Yamazaki v2 - Path Validator

File path validation and path traversal protection.
"""

import re
from pathlib import Path
from typing import Optional, Tuple


class PathValidator:
    """
    File path validator with path traversal protection.

    Ensures file operations stay within allowed directories.
    """

    def __init__(self, config):
        """
        Initialize path validator.

        Args:
            config: SecurityConfig with allowed directories and blocked patterns
        """
        self.allowed_directories = [
            Path(d).resolve() for d in config.allowed_directories
        ]
        self.blocked_patterns = config.blocked_file_patterns

    def validate(
        self,
        file_path: str,
        operation: str = "read"
    ) -> Tuple[bool, Optional[str], Optional[Path]]:
        """
        Validate file path for security.

        Args:
            file_path: Path to validate
            operation: Operation type ("read" or "write")

        Returns:
            (is_valid, error_message, resolved_path) tuple
        """
        try:
            # Resolve path (handles ~, .., symlinks, etc.)
            path = Path(file_path).expanduser().resolve()

            # Check if path is within allowed directories
            allowed = False
            for allowed_dir in self.allowed_directories:
                try:
                    path.relative_to(allowed_dir)
                    allowed = True
                    break
                except ValueError:
                    continue

            if not allowed:
                allowed_str = ", ".join(str(d) for d in self.allowed_directories)
                return (
                    False,
                    f"Access denied. File must be within: {allowed_str}",
                    None
                )

            # Check for blocked patterns
            path_str = str(path).lower()
            for pattern in self.blocked_patterns:
                if re.search(pattern, path_str):
                    return (
                        False,
                        f"Access to sensitive files blocked: {pattern}",
                        None
                    )

            # Additional checks for read operations
            if operation == "read":
                if not path.exists():
                    return False, f"File not found: {file_path}", None

                if not path.is_file():
                    return False, f"Not a file: {file_path}", None

            return True, None, path

        except Exception as e:
            return False, f"Invalid file path: {str(e)}", None

    def is_safe(self, file_path: str, operation: str = "read") -> bool:
        """
        Check if path is safe (simple boolean check).

        Args:
            file_path: Path to check
            operation: Operation type

        Returns:
            True if safe, False otherwise
        """
        is_valid, _, _ = self.validate(file_path, operation)
        return is_valid

    def __repr__(self) -> str:
        return f"PathValidator(allowed_dirs={len(self.allowed_directories)})"

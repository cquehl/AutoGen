"""
Yamazaki v2 - File Write Tool

Provides file writing capabilities with security validation.
"""

import os
from pathlib import Path
from typing import Optional

from ...core.base_tool import BaseTool, ToolResult, ToolCategory


class WriteFileTool(BaseTool):
    """
    File write tool with security validation.

    Creates or overwrites files with content.
    """

    NAME = "file.write"
    DESCRIPTION = "Write content to a file (creates new file or overwrites existing)"
    CATEGORY = ToolCategory.FILE
    VERSION = "1.0.0"
    REQUIRES_SECURITY_VALIDATION = True  # Use path validator

    def __init__(self, security_middleware=None, **kwargs):
        super().__init__(**kwargs)
        self.security_middleware = security_middleware

    async def execute(self, file_path: str, content: str, create_dirs: bool = False) -> ToolResult:
        """
        Write content to a file.

        Args:
            file_path: Path to file to write
            content: Content to write
            create_dirs: Create parent directories if they don't exist (default: False)

        Returns:
            ToolResult with write confirmation
        """
        try:
            # Security validation
            if self.security_middleware:
                path_validator = self.security_middleware.get_path_validator()
                is_valid, error, _ = path_validator.validate(file_path, operation="write")
                if not is_valid:
                    return ToolResult.error(f"Security validation failed: {error}")

            path = Path(file_path)

            # Check if parent directory exists
            if not path.parent.exists():
                if create_dirs:
                    path.parent.mkdir(parents=True, exist_ok=True)
                else:
                    return ToolResult.error(
                        f"Parent directory does not exist: {path.parent}. "
                        "Set create_dirs=true to create it."
                    )

            # Write file
            path.write_text(content, encoding='utf-8')

            return ToolResult.ok({
                "file_path": str(path.absolute()),
                "bytes_written": len(content.encode('utf-8')),
                "lines_written": len(content.splitlines()),
                "message": f"Successfully wrote to {path.name}"
            })

        except PermissionError:
            return ToolResult.error(f"Permission denied: {file_path}")
        except OSError as e:
            return ToolResult.error(f"OS error writing file: {str(e)}")
        except Exception as e:
            return ToolResult.error(f"Failed to write file: {str(e)}")

    def validate_params(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters"""
        file_path = kwargs.get("file_path")
        content = kwargs.get("content")

        if not file_path:
            return False, "file_path is required"

        if not isinstance(file_path, str):
            return False, "file_path must be a string"

        if content is None:
            return False, "content is required"

        if not isinstance(content, str):
            return False, "content must be a string"

        # Check for reasonable file size (10MB limit)
        content_size = len(content.encode('utf-8'))
        if content_size > 10 * 1024 * 1024:
            return False, f"content is too large ({content_size} bytes, max 10MB)"

        create_dirs = kwargs.get("create_dirs", False)
        if not isinstance(create_dirs, bool):
            return False, "create_dirs must be a boolean"

        return True, None

    def _get_parameters_schema(self) -> dict:
        """Get parameters schema"""
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to file to write (absolute or relative)",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
                "create_dirs": {
                    "type": "boolean",
                    "description": "Create parent directories if they don't exist (default: false)",
                    "default": False,
                },
            },
            "required": ["file_path", "content"],
        }

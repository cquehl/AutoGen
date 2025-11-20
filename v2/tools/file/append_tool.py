"""
Yamazaki v2 - File Append Tool

Provides file appending capabilities with security validation.
"""

from pathlib import Path
from typing import Optional

from ...core.base_tool import BaseTool, ToolResult, ToolCategory


class AppendFileTool(BaseTool):
    """
    File append tool with security validation.

    Appends content to existing files.
    """

    NAME = "file.append"
    DESCRIPTION = "Append content to an existing file"
    CATEGORY = ToolCategory.FILE
    VERSION = "1.0.0"
    REQUIRES_SECURITY_VALIDATION = True

    def __init__(self, security_middleware=None, **kwargs):
        super().__init__(**kwargs)
        self.security_middleware = security_middleware

    async def execute(self, file_path: str, content: str) -> ToolResult:
        """
        Append content to a file.

        Args:
            file_path: Path to file to append to
            content: Content to append

        Returns:
            ToolResult with append confirmation
        """
        try:
            # Security validation
            if self.security_middleware:
                path_validator = self.security_middleware.get_path_validator()
                is_valid, error, _ = path_validator.validate(file_path, operation="write")
                if not is_valid:
                    return ToolResult.error(f"Security validation failed: {error}")

            path = Path(file_path)

            # Check if file exists
            if not path.exists():
                return ToolResult.error(f"File does not exist: {file_path}")

            if not path.is_file():
                return ToolResult.error(f"Path is not a file: {file_path}")

            # Get original size
            original_size = path.stat().st_size

            # Append content
            with open(path, 'a', encoding='utf-8') as f:
                f.write(content)

            new_size = path.stat().st_size
            bytes_added = new_size - original_size

            return ToolResult.ok({
                "file_path": str(path.absolute()),
                "bytes_appended": bytes_added,
                "lines_appended": len(content.splitlines()),
                "new_size": new_size,
                "message": f"Successfully appended to {path.name}"
            })

        except PermissionError:
            return ToolResult.error(f"Permission denied: {file_path}")
        except OSError as e:
            return ToolResult.error(f"OS error appending to file: {str(e)}")
        except Exception as e:
            return ToolResult.error(f"Failed to append to file: {str(e)}")

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

        # Check for reasonable content size (10MB limit)
        content_size = len(content.encode('utf-8'))
        if content_size > 10 * 1024 * 1024:
            return False, f"content is too large ({content_size} bytes, max 10MB)"

        return True, None

    def _get_parameters_schema(self) -> dict:
        """Get parameters schema"""
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to file to append to",
                },
                "content": {
                    "type": "string",
                    "description": "Content to append to the file",
                },
            },
            "required": ["file_path", "content"],
        }

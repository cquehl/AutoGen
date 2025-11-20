"""
Yamazaki v2 - File Read Tool

Secure file reading with path validation.
"""

from typing import Optional

from ...core.base_tool import BaseTool, ToolResult, ToolCategory


class FileReadTool(BaseTool):
    """
    File read tool with path traversal protection.
    """

    NAME = "file.read"
    DESCRIPTION = "Read contents of a text file with security validation"
    CATEGORY = ToolCategory.FILE
    VERSION = "1.0.0"
    REQUIRES_SECURITY_VALIDATION = True

    def __init__(self, security_middleware=None, **kwargs):
        """
        Initialize file read tool.

        Args:
            security_middleware: Security middleware
        """
        super().__init__(**kwargs)
        self.security = security_middleware

    async def execute(
        self,
        file_path: str,
        encoding: str = "utf-8"
    ) -> ToolResult:
        """
        Read file contents.

        Args:
            file_path: Path to file
            encoding: File encoding

        Returns:
            ToolResult with file contents
        """
        # Validate path
        validator = self.security.get_path_validator()
        is_valid, error, path = validator.validate(file_path, operation="read")

        if not is_valid:
            return ToolResult.error(error)

        try:
            content = path.read_text(encoding=encoding)

            return ToolResult.ok({
                "file_path": str(path),
                "content": content,
                "size_bytes": path.stat().st_size,
                "lines": len(content.splitlines()),
            })

        except Exception as e:
            return ToolResult.error(f"Failed to read file: {str(e)}")

    def validate_params(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters"""
        file_path = kwargs.get("file_path")

        if not file_path:
            return False, "file_path parameter is required"

        if not isinstance(file_path, str):
            return False, "file_path must be a string"

        return True, None

    def _get_parameters_schema(self) -> dict:
        """Get parameters schema"""
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to read",
                },
                "encoding": {
                    "type": "string",
                    "description": "File encoding (default: utf-8)",
                    "default": "utf-8",
                },
            },
            "required": ["file_path"],
        }

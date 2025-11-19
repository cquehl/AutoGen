"""
Yamazaki v2 - Base Tool Class

Abstract base class for all tools in the system.
Provides validation, security, and observability hooks.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class ToolCategory(str, Enum):
    """Tool categories for organization and discovery"""
    DATABASE = "database"
    FILE = "file"
    WEB = "web"
    WEATHER = "weather"
    META = "meta"  # Introspection and system capability tools
    GENERAL = "general"


@dataclass
class ToolResult:
    """Standardized tool execution result"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def ok(cls, data: Any, metadata: Optional[Dict[str, Any]] = None) -> "ToolResult":
        """Create success result"""
        return cls(success=True, data=data, metadata=metadata)

    @classmethod
    def error(cls, error: str, metadata: Optional[Dict[str, Any]] = None) -> "ToolResult":
        """Create error result"""
        return cls(success=False, error=error, metadata=metadata)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for agent consumption"""
        result = {"success": self.success}
        if self.data is not None:
            result["data"] = self.data
        if self.error is not None:
            result["error"] = self.error
        if self.metadata is not None:
            result["metadata"] = self.metadata
        return result


class BaseTool(ABC):
    """
    Base class for all Yamazaki tools.

    Provides common interface, validation, and observability hooks.
    """

    # Class-level metadata
    NAME: str = "base_tool"
    DESCRIPTION: str = "Base tool class"
    CATEGORY: ToolCategory = ToolCategory.GENERAL
    VERSION: str = "1.0.0"
    REQUIRES_SECURITY_VALIDATION: bool = False

    def __init__(self, **kwargs):
        """
        Initialize tool with optional configuration.

        Args:
            **kwargs: Tool-specific configuration
        """
        self.config = kwargs

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool.

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            ToolResult with outcome
        """
        pass

    @abstractmethod
    def validate_params(self, **kwargs) -> tuple[bool, Optional[str]]:
        """
        Validate parameters before execution.

        Args:
            **kwargs: Parameters to validate

        Returns:
            (is_valid, error_message) tuple
        """
        pass

    def get_function_schema(self) -> Dict[str, Any]:
        """
        Get OpenAI function schema for this tool.

        Returns:
            Function schema dict
        """
        return {
            "name": self.NAME,
            "description": self.DESCRIPTION,
            "parameters": self._get_parameters_schema(),
        }

    @abstractmethod
    def _get_parameters_schema(self) -> Dict[str, Any]:
        """
        Get JSON schema for tool parameters.

        Returns:
            Parameters schema dict
        """
        pass

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """
        Get tool metadata.

        Returns:
            Metadata dictionary
        """
        return {
            "name": cls.NAME,
            "description": cls.DESCRIPTION,
            "category": cls.CATEGORY.value,
            "version": cls.VERSION,
            "requires_security_validation": cls.REQUIRES_SECURITY_VALIDATION,
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.NAME}, category={self.CATEGORY.value})"


class ToolMetadata:
    """Metadata for tool registration"""

    def __init__(
        self,
        name: str,
        description: str,
        category: ToolCategory,
        version: str,
        tool_class: type,
        requires_security: bool = False,
    ):
        self.name = name
        self.description = description
        self.category = category
        self.version = version
        self.tool_class = tool_class
        self.requires_security = requires_security

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "version": self.version,
            "requires_security": self.requires_security,
        }

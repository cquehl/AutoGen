"""
Yamazaki v2 - Core Module

Core abstractions and dependency injection.
"""

from .base_agent import BaseAgent, AgentMetadata
from .base_tool import BaseTool, ToolResult, ToolCategory, ToolMetadata
from .container import Container, get_container, reset_container

__all__ = [
    "BaseAgent",
    "AgentMetadata",
    "BaseTool",
    "ToolResult",
    "ToolCategory",
    "ToolMetadata",
    "Container",
    "get_container",
    "reset_container",
]

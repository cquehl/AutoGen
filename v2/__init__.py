"""
Yamazaki v2 - Modern AutoGen Framework

A production-ready AutoGen implementation with:
- Plugin-based agent and tool registries
- Dependency injection for modularity
- Centralized security middleware
- Structured logging and observability
- Type-safe configuration with Pydantic

Architecture inspired by modern software engineering practices:
smooth, refined, and carefully crafted - like Yamazaki whiskey.
"""

from .core import Container, get_container
from .config import get_settings
from .agents import AgentRegistry, AgentFactory
from .tools import ToolRegistry

__version__ = "2.0.0"
__all__ = [
    "Container",
    "get_container",
    "get_settings",
    "AgentRegistry",
    "AgentFactory",
    "ToolRegistry",
]

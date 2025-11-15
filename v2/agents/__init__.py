"""
Yamazaki v2 - Agents Module

Plugin-based agent system with registry and factory.
"""

from .registry import AgentRegistry, get_global_registry, set_global_registry
from .factory import AgentFactory

__all__ = [
    "AgentRegistry",
    "AgentFactory",
    "get_global_registry",
    "set_global_registry",
]

"""
Yamazaki v2 - Agents Module

Plugin-based agent system with registry and factory.
"""

from .registry import AgentRegistry
from .factory import AgentFactory

__all__ = [
    "AgentRegistry",
    "AgentFactory",
]

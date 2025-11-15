"""
Magentic-One Multi-Agent System

A powerful orchestrator-driven agent system for complex web research,
data gathering, and automated workflows.
"""

from .base import BaseMagneticAgent
from .web_surfer import WebSurferAgent
from .orchestrator import OrchestratorAgent
from .team import create_magentic_team

__all__ = [
    'BaseMagneticAgent',
    'WebSurferAgent',
    'OrchestratorAgent',
    'create_magentic_team'
]

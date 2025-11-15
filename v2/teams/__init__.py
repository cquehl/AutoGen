"""
Enhanced team patterns for AutoGen V2.

Provides multiple team orchestration patterns inspired by AutoGen 0.7.x:
- GraphFlowTeam: DiGraph-based workflow teams
- SequentialTeam: Sequential chained conversations
- SwarmTeam: Dynamic agent selection based on task
- RoundRobinTeam: Simple round-robin agent selection
"""

from .base_team import BaseTeam, TeamResult
from .graph_flow_team import GraphFlowTeam
from .sequential_team import SequentialTeam
from .swarm_team import SwarmTeam

__all__ = [
    "BaseTeam",
    "TeamResult",
    "GraphFlowTeam",
    "SequentialTeam",
    "SwarmTeam",
]

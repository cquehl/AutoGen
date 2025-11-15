"""
Base team abstraction for multi-agent orchestration.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, AsyncIterator
from datetime import datetime
from enum import Enum


class TeamStatus(Enum):
    """Status of team execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TeamResult:
    """Result of team execution."""
    task: str
    status: TeamStatus
    messages: List[Dict[str, Any]] = field(default_factory=list)
    final_answer: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error: Optional[str] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        """Get execution duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task": self.task,
            "status": self.status.value,
            "messages": self.messages,
            "final_answer": self.final_answer,
            "metadata": self.metadata,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
        }


class BaseTeam(ABC):
    """
    Base class for all team orchestration patterns.

    A team coordinates multiple agents to accomplish a task using
    a specific orchestration strategy.
    """

    def __init__(
        self,
        name: str,
        agents: List[Any],
        max_rounds: int = 10,
        timeout: int = 600,
    ):
        """
        Initialize the team.

        Args:
            name: Team name
            agents: List of agents in the team
            max_rounds: Maximum number of conversation rounds
            timeout: Maximum execution time in seconds
        """
        self.name = name
        self.agents = agents
        self.max_rounds = max_rounds
        self.timeout = timeout

    @abstractmethod
    async def run(self, task: str, **kwargs) -> TeamResult:
        """
        Run the team on a task.

        Args:
            task: Task description
            **kwargs: Additional task parameters

        Returns:
            TeamResult with execution results
        """
        pass

    async def run_stream(self, task: str, **kwargs) -> AsyncIterator[Dict[str, Any]]:
        """
        Run the team with streaming results.

        Args:
            task: Task description
            **kwargs: Additional task parameters

        Yields:
            Event dictionaries with intermediate results
        """
        # Default implementation: run normally and yield final result
        result = await self.run(task, **kwargs)
        yield {
            "type": "final_result",
            "result": result.to_dict(),
        }

    def get_agent_by_name(self, name: str) -> Optional[Any]:
        """Get an agent by name."""
        for agent in self.agents:
            if hasattr(agent, "name") and agent.name == name:
                return agent
            if hasattr(agent, "NAME") and agent.NAME == name:
                return agent
        return None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, agents={len(self.agents)})"

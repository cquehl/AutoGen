"""
State management for agents and workflows.
"""

import json
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum

from ..observability.logger import get_logger

logger = get_logger(__name__)


class AgentStatus(Enum):
    """Agent status states."""
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentState:
    """State snapshot for an agent."""
    agent_id: str
    status: AgentStatus
    current_task: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "status": self.status.value,
            "current_task": self.current_task,
            "context": self.context,
            "variables": self.variables,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentState":
        """Create from dictionary."""
        return cls(
            agent_id=data["agent_id"],
            status=AgentStatus(data["status"]),
            current_task=data.get("current_task"),
            context=data.get("context", {}),
            variables=data.get("variables", {}),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            metadata=data.get("metadata", {}),
        )


class StateManager:
    """
    Manages state for agents and workflows.

    Provides state persistence, versioning, and rollback capabilities.

    Example:
        >>> manager = StateManager()
        >>>
        >>> # Create initial state
        >>> state = AgentState(
        ...     agent_id="agent1",
        ...     status=AgentStatus.IDLE,
        ...     variables={"count": 0}
        ... )
        >>>
        >>> # Save state
        >>> await manager.save_state(state)
        >>>
        >>> # Update state
        >>> state.status = AgentStatus.RUNNING
        >>> state.variables["count"] = 1
        >>> await manager.save_state(state)
        >>>
        >>> # Load state
        >>> loaded = await manager.load_state("agent1")
    """

    def __init__(
        self,
        storage_path: str = ".autogen_state",
        enable_versioning: bool = True,
        max_versions: int = 10,
    ):
        """
        Initialize state manager.

        Args:
            storage_path: Directory for state files
            enable_versioning: Keep version history
            max_versions: Maximum versions to keep per agent
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.enable_versioning = enable_versioning
        self.max_versions = max_versions

        # In-memory cache
        self._cache: Dict[str, AgentState] = {}

        # Version history: agent_id -> [states]
        self._versions: Dict[str, list[AgentState]] = {}

    async def save_state(self, state: AgentState, version_name: Optional[str] = None):
        """
        Save agent state.

        Args:
            state: Agent state to save
            version_name: Optional version name (for tagging)
        """
        agent_id = state.agent_id

        # Update cache
        self._cache[agent_id] = state

        # Add to version history
        if self.enable_versioning:
            if agent_id not in self._versions:
                self._versions[agent_id] = []

            # Create versioned copy
            version = AgentState(
                agent_id=state.agent_id,
                status=state.status,
                current_task=state.current_task,
                context=state.context.copy(),
                variables=state.variables.copy(),
                timestamp=datetime.now(),
                metadata={
                    **state.metadata,
                    "version_name": version_name,
                },
            )

            self._versions[agent_id].append(version)

            # Trim old versions
            if len(self._versions[agent_id]) > self.max_versions:
                self._versions[agent_id] = self._versions[agent_id][-self.max_versions:]

        # Persist to file
        await self._save_to_file(state)

        logger.debug(f"Saved state for {agent_id}")

    async def load_state(self, agent_id: str) -> Optional[AgentState]:
        """
        Load agent state.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent state or None
        """
        # Check cache first
        if agent_id in self._cache:
            return self._cache[agent_id]

        # Load from file
        state = await self._load_from_file(agent_id)
        if state:
            self._cache[agent_id] = state

        return state

    async def delete_state(self, agent_id: str):
        """
        Delete agent state.

        Args:
            agent_id: Agent identifier
        """
        # Remove from cache
        self._cache.pop(agent_id, None)
        self._versions.pop(agent_id, None)

        # Delete file
        file_path = self._get_state_file(agent_id)
        if file_path.exists():
            file_path.unlink()
            logger.debug(f"Deleted state for {agent_id}")

    async def update_status(self, agent_id: str, status: AgentStatus):
        """
        Update agent status.

        Args:
            agent_id: Agent identifier
            status: New status
        """
        state = await self.load_state(agent_id)
        if state:
            state.status = status
            state.timestamp = datetime.now()
            await self.save_state(state)

    async def update_variable(self, agent_id: str, key: str, value: Any):
        """
        Update a state variable.

        Args:
            agent_id: Agent identifier
            key: Variable key
            value: Variable value
        """
        state = await self.load_state(agent_id)
        if state:
            state.variables[key] = value
            state.timestamp = datetime.now()
            await self.save_state(state)

    async def get_variable(self, agent_id: str, key: str, default: Any = None) -> Any:
        """
        Get a state variable.

        Args:
            agent_id: Agent identifier
            key: Variable key
            default: Default value

        Returns:
            Variable value or default
        """
        state = await self.load_state(agent_id)
        if state:
            return state.variables.get(key, default)
        return default

    def get_versions(self, agent_id: str) -> list[AgentState]:
        """
        Get version history for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            List of state versions
        """
        return self._versions.get(agent_id, []).copy()

    async def rollback(self, agent_id: str, version_index: int = -2):
        """
        Rollback to a previous state version.

        Args:
            agent_id: Agent identifier
            version_index: Index in version history (-2 = previous version)
        """
        if agent_id not in self._versions:
            logger.warning(f"No version history for {agent_id}")
            return

        versions = self._versions[agent_id]
        if not versions or len(versions) < abs(version_index):
            logger.warning(f"Invalid version index {version_index}")
            return

        # Get target version
        target_state = versions[version_index]

        # Create new state from target
        rollback_state = AgentState(
            agent_id=agent_id,
            status=target_state.status,
            current_task=target_state.current_task,
            context=target_state.context.copy(),
            variables=target_state.variables.copy(),
            timestamp=datetime.now(),
            metadata={
                **target_state.metadata,
                "rolled_back_from": versions[-1].timestamp.isoformat(),
            },
        )

        await self.save_state(rollback_state, version_name="rollback")
        logger.info(f"Rolled back state for {agent_id}")

    def get_all_agents(self) -> Set[str]:
        """Get all agent IDs with saved state."""
        # From cache
        agents = set(self._cache.keys())

        # From files
        for file_path in self.storage_path.glob("*.json"):
            agent_id = file_path.stem
            agents.add(agent_id)

        return agents

    async def _save_to_file(self, state: AgentState):
        """Save state to file."""
        file_path = self._get_state_file(state.agent_id)

        try:
            with open(file_path, "w") as f:
                json.dump(state.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Error saving state to file: {e}")
            raise

    async def _load_from_file(self, agent_id: str) -> Optional[AgentState]:
        """Load state from file."""
        file_path = self._get_state_file(agent_id)

        if not file_path.exists():
            return None

        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            return AgentState.from_dict(data)
        except Exception as e:
            logger.error(f"Error loading state from file: {e}")
            return None

    def _get_state_file(self, agent_id: str) -> Path:
        """Get file path for agent state."""
        safe_id = agent_id.replace("/", "_").replace("\\", "_")
        return self.storage_path / f"{safe_id}.json"

    def __repr__(self) -> str:
        return f"StateManager(agents={len(self._cache)}, versioning={self.enable_versioning})"

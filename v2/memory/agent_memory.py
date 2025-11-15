"""
Agent memory system for maintaining context and state.
"""

import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

from ..observability.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MemoryEntry:
    """Single memory entry."""
    key: str
    value: Any
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "key": self.key,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        """Create from dictionary."""
        return cls(
            key=data["key"],
            value=data["value"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )


class MemoryStore(ABC):
    """Abstract base class for memory storage backends."""

    @abstractmethod
    async def save(self, agent_id: str, key: str, value: Any, metadata: Optional[Dict] = None):
        """Save a memory entry."""
        pass

    @abstractmethod
    async def load(self, agent_id: str, key: str) -> Optional[Any]:
        """Load a memory entry."""
        pass

    @abstractmethod
    async def load_all(self, agent_id: str) -> Dict[str, Any]:
        """Load all memory entries for an agent."""
        pass

    @abstractmethod
    async def delete(self, agent_id: str, key: str):
        """Delete a memory entry."""
        pass

    @abstractmethod
    async def clear(self, agent_id: str):
        """Clear all memory for an agent."""
        pass


class InMemoryStore(MemoryStore):
    """In-memory storage (not persistent)."""

    def __init__(self):
        """Initialize in-memory store."""
        self._data: Dict[str, Dict[str, MemoryEntry]] = {}

    async def save(self, agent_id: str, key: str, value: Any, metadata: Optional[Dict] = None):
        """Save to memory."""
        if agent_id not in self._data:
            self._data[agent_id] = {}

        entry = MemoryEntry(
            key=key,
            value=value,
            metadata=metadata or {},
        )
        self._data[agent_id][key] = entry

    async def load(self, agent_id: str, key: str) -> Optional[Any]:
        """Load from memory."""
        if agent_id in self._data and key in self._data[agent_id]:
            return self._data[agent_id][key].value
        return None

    async def load_all(self, agent_id: str) -> Dict[str, Any]:
        """Load all entries."""
        if agent_id not in self._data:
            return {}
        return {key: entry.value for key, entry in self._data[agent_id].items()}

    async def delete(self, agent_id: str, key: str):
        """Delete entry."""
        if agent_id in self._data:
            self._data[agent_id].pop(key, None)

    async def clear(self, agent_id: str):
        """Clear all entries."""
        self._data.pop(agent_id, None)


class FileStore(MemoryStore):
    """File-based persistent storage."""

    def __init__(self, base_path: str = ".autogen_memory"):
        """
        Initialize file store.

        Args:
            base_path: Base directory for storing memory files
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_agent_file(self, agent_id: str) -> Path:
        """Get file path for agent memory."""
        safe_agent_id = agent_id.replace("/", "_").replace("\\", "_")
        return self.base_path / f"{safe_agent_id}.json"

    async def save(self, agent_id: str, key: str, value: Any, metadata: Optional[Dict] = None):
        """Save to file."""
        file_path = self._get_agent_file(agent_id)

        # Load existing data
        data = {}
        if file_path.exists():
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Corrupted memory file for {agent_id}, resetting")

        # Add new entry
        entry = MemoryEntry(key=key, value=value, metadata=metadata or {})
        data[key] = entry.to_dict()

        # Save
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

        logger.debug(f"Saved memory for {agent_id}: {key}")

    async def load(self, agent_id: str, key: str) -> Optional[Any]:
        """Load from file."""
        file_path = self._get_agent_file(agent_id)

        if not file_path.exists():
            return None

        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            if key in data:
                entry = MemoryEntry.from_dict(data[key])
                return entry.value

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error loading memory for {agent_id}: {e}")

        return None

    async def load_all(self, agent_id: str) -> Dict[str, Any]:
        """Load all from file."""
        file_path = self._get_agent_file(agent_id)

        if not file_path.exists():
            return {}

        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            return {key: MemoryEntry.from_dict(entry_data).value for key, entry_data in data.items()}

        except json.JSONDecodeError as e:
            logger.error(f"Error loading all memory for {agent_id}: {e}")
            return {}

    async def delete(self, agent_id: str, key: str):
        """Delete from file."""
        file_path = self._get_agent_file(agent_id)

        if not file_path.exists():
            return

        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            data.pop(key, None)

            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)

        except json.JSONDecodeError as e:
            logger.error(f"Error deleting memory for {agent_id}: {e}")

    async def clear(self, agent_id: str):
        """Clear file."""
        file_path = self._get_agent_file(agent_id)
        if file_path.exists():
            file_path.unlink()
            logger.debug(f"Cleared memory for {agent_id}")


class AgentMemory:
    """
    Memory system for agents.

    Provides key-value storage with optional persistence for agent state,
    learned information, and context.

    Example:
        >>> memory = AgentMemory("my_agent", store=FileStore())
        >>>
        >>> # Save information
        >>> await memory.save("user_preference", "dark_mode")
        >>> await memory.save("conversation_count", 5)
        >>>
        >>> # Load information
        >>> preference = await memory.load("user_preference")
        >>> count = await memory.load("conversation_count")
    """

    def __init__(
        self,
        agent_id: str,
        store: Optional[MemoryStore] = None,
        auto_save: bool = True,
    ):
        """
        Initialize agent memory.

        Args:
            agent_id: Unique identifier for the agent
            store: Storage backend (defaults to InMemoryStore)
            auto_save: Automatically save changes
        """
        self.agent_id = agent_id
        self.store = store or InMemoryStore()
        self.auto_save = auto_save
        self._cache: Dict[str, Any] = {}

    async def save(self, key: str, value: Any, metadata: Optional[Dict] = None):
        """
        Save a value to memory.

        Args:
            key: Memory key
            value: Value to store
            metadata: Optional metadata
        """
        self._cache[key] = value

        if self.auto_save:
            await self.store.save(self.agent_id, key, value, metadata)

    async def load(self, key: str, default: Any = None) -> Any:
        """
        Load a value from memory.

        Args:
            key: Memory key
            default: Default value if key not found

        Returns:
            Stored value or default
        """
        # Check cache first
        if key in self._cache:
            return self._cache[key]

        # Load from store
        value = await self.store.load(self.agent_id, key)
        if value is not None:
            self._cache[key] = value
            return value

        return default

    async def load_all(self) -> Dict[str, Any]:
        """Load all memory entries."""
        data = await self.store.load_all(self.agent_id)
        self._cache.update(data)
        return data

    async def delete(self, key: str):
        """Delete a memory entry."""
        self._cache.pop(key, None)
        await self.store.delete(self.agent_id, key)

    async def clear(self):
        """Clear all memory."""
        self._cache.clear()
        await self.store.clear(self.agent_id)

    async def flush(self):
        """Flush cache to storage."""
        for key, value in self._cache.items():
            await self.store.save(self.agent_id, key, value)

    def get_cache(self) -> Dict[str, Any]:
        """Get current cache contents."""
        return self._cache.copy()

    def __repr__(self) -> str:
        return f"AgentMemory(agent_id={self.agent_id}, entries={len(self._cache)})"

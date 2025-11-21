"""
Agent memory system for maintaining context and state.

FIXED: Async file I/O with proper locking for concurrent access.
Platform compatibility: Works on Unix/Linux/macOS and Windows.
"""

import json
import asyncio
import sys
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from collections import OrderedDict

# Platform-specific imports for file locking
# fcntl is Unix/Linux/macOS only, use msvcrt on Windows
if sys.platform == "win32":
    import msvcrt
    HAS_FCNTL = False
else:
    try:
        import fcntl
        HAS_FCNTL = True
    except ImportError:
        HAS_FCNTL = False

from ..observability.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MemoryEntry:
    """Single memory entry."""
    key: str
    value: Any
    timestamp: datetime = field(default_factory=lambda: datetime.now())
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
    """In-memory storage (not persistent) with thread safety."""

    def __init__(self):
        self._data: Dict[str, Dict[str, MemoryEntry]] = {}
        self._lock = asyncio.Lock()

    async def save(self, agent_id: str, key: str, value: Any, metadata: Optional[Dict] = None):
        async with self._lock:
            if agent_id not in self._data:
                self._data[agent_id] = {}

            entry = MemoryEntry(
                key=key,
                value=value,
                metadata=metadata or {},
            )
            self._data[agent_id][key] = entry

    async def load(self, agent_id: str, key: str) -> Optional[Any]:
        async with self._lock:
            if agent_id in self._data and key in self._data[agent_id]:
                return self._data[agent_id][key].value
            return None

    async def load_all(self, agent_id: str) -> Dict[str, Any]:
        async with self._lock:
            if agent_id not in self._data:
                return {}
            return {key: entry.value for key, entry in self._data[agent_id].items()}

    async def delete(self, agent_id: str, key: str):
        async with self._lock:
            if agent_id in self._data:
                self._data[agent_id].pop(key, None)

    async def clear(self, agent_id: str):
        async with self._lock:
            self._data.pop(agent_id, None)


class FileStore(MemoryStore):
    """
    File-based persistent storage with async I/O and file locking.

    FIXED: Uses async I/O and fcntl for proper concurrent access.
    """

    def __init__(self, base_path: str = ".autogen_memory"):
        """
        Initialize file store.

        Args:
            base_path: Base directory for storing memory files
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        self._locks: Dict[str, asyncio.Lock] = {}
        self._locks_lock = asyncio.Lock()

    async def _get_lock(self, agent_id: str) -> asyncio.Lock:
        async with self._locks_lock:
            if agent_id not in self._locks:
                self._locks[agent_id] = asyncio.Lock()
            return self._locks[agent_id]

    def _get_agent_file(self, agent_id: str) -> Path:
        """
        Get file path for agent memory with proper sanitization.

        FIXED: Strict validation to prevent path traversal.
        """
        # Strict validation - only alphanumeric, dash, and underscore
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', agent_id):
            raise ValueError(
                f"Invalid agent_id '{agent_id}': must contain only alphanumeric, "
                "dash, and underscore characters"
            )

        file_path = (self.base_path / f"{agent_id}.json").resolve()

        # Ensure it's within base_path (prevent traversal)
        if not str(file_path).startswith(str(self.base_path.resolve())):
            raise ValueError(f"Path traversal attempt detected: {agent_id}")

        return file_path

    async def save(self, agent_id: str, key: str, value: Any, metadata: Optional[Dict] = None):
        """
        Save to file with proper locking.

        FIXED: Uses async I/O and file locking to prevent corruption.
        """
        file_path = self._get_agent_file(agent_id)
        lock = await self._get_lock(agent_id)

        async with lock:
            # Run file operations in thread pool to avoid blocking
            await asyncio.to_thread(self._save_sync, file_path, key, value, metadata)

        logger.debug(f"Saved memory for {agent_id}: {key}")

    def _lock_file(self, file_obj, exclusive: bool = True):
        """Platform-independent file locking."""
        if sys.platform == "win32":
            # Windows: use msvcrt
            msvcrt.locking(file_obj.fileno(), msvcrt.LK_LOCK if exclusive else msvcrt.LK_NBLCK, 1)
        elif HAS_FCNTL:
            # Unix/Linux/macOS: use fcntl
            fcntl.flock(file_obj.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        else:
            # No locking available - log warning
            logger.warning("File locking not available on this platform")

    def _unlock_file(self, file_obj):
        """Platform-independent file unlocking."""
        if sys.platform == "win32":
            # Windows: use msvcrt
            msvcrt.locking(file_obj.fileno(), msvcrt.LK_UNLCK, 1)
        elif HAS_FCNTL:
            # Unix/Linux/macOS: use fcntl
            fcntl.flock(file_obj.fileno(), fcntl.LOCK_UN)

    def _save_sync(self, file_path: Path, key: str, value: Any, metadata: Optional[Dict]):
        """Synchronous save with file locking."""
        # Use exclusive lock for write
        mode = "r+" if file_path.exists() else "w+"

        with open(file_path, mode) as f:
            # Acquire exclusive lock
            self._lock_file(f, exclusive=True)

            try:
                if file_path.stat().st_size > 0:
                    f.seek(0)
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        logger.warning(f"Corrupted memory file, resetting: {file_path}")
                        data = {}
                else:
                    data = {}

                entry = MemoryEntry(key=key, value=value, metadata=metadata or {})
                data[key] = entry.to_dict()

                f.seek(0)
                f.truncate()
                json.dump(data, f, indent=2)
                f.flush()

            finally:
                self._unlock_file(f)

    async def load(self, agent_id: str, key: str) -> Optional[Any]:
        """Load from file with proper locking."""
        file_path = self._get_agent_file(agent_id)

        if not file_path.exists():
            return None

        lock = await self._get_lock(agent_id)
        async with lock:
            return await asyncio.to_thread(self._load_sync, file_path, key)

    def _load_sync(self, file_path: Path, key: str) -> Optional[Any]:
        """Synchronous load with file locking."""
        with open(file_path, "r") as f:
            # Acquire shared lock for read
            self._lock_file(f, exclusive=False)

            try:
                data = json.load(f)
                if key in data:
                    entry = MemoryEntry.from_dict(data[key])
                    return entry.value
            except json.JSONDecodeError as e:
                logger.error(f"Error loading memory: {e}")
            finally:
                self._unlock_file(f)

        return None

    async def load_all(self, agent_id: str) -> Dict[str, Any]:
        """Load all from file with proper locking."""
        file_path = self._get_agent_file(agent_id)

        if not file_path.exists():
            return {}

        lock = await self._get_lock(agent_id)
        async with lock:
            return await asyncio.to_thread(self._load_all_sync, file_path)

    def _load_all_sync(self, file_path: Path) -> Dict[str, Any]:
        """Synchronous load all with file locking."""
        with open(file_path, "r") as f:
            self._lock_file(f, exclusive=False)

            try:
                data = json.load(f)
                return {
                    key: MemoryEntry.from_dict(entry_data).value
                    for key, entry_data in data.items()
                }
            except json.JSONDecodeError as e:
                logger.error(f"Error loading all memory: {e}")
                return {}
            finally:
                self._unlock_file(f)

    async def delete(self, agent_id: str, key: str):
        """Delete from file with proper locking."""
        file_path = self._get_agent_file(agent_id)

        if not file_path.exists():
            return

        lock = await self._get_lock(agent_id)
        async with lock:
            await asyncio.to_thread(self._delete_sync, file_path, key)

    def _delete_sync(self, file_path: Path, key: str):
        """Synchronous delete with file locking."""
        with open(file_path, "r+") as f:
            self._lock_file(f, exclusive=True)

            try:
                data = json.load(f)
                data.pop(key, None)

                f.seek(0)
                f.truncate()
                json.dump(data, f, indent=2)
                f.flush()
            except json.JSONDecodeError as e:
                logger.error(f"Error deleting memory: {e}")
            finally:
                self._unlock_file(f)

    async def clear(self, agent_id: str):
        """Clear file."""
        file_path = self._get_agent_file(agent_id)

        if file_path.exists():
            lock = await self._get_lock(agent_id)
            async with lock:
                await asyncio.to_thread(file_path.unlink)
            logger.debug(f"Cleared memory for {agent_id}")


class AgentMemory:
    """
    Memory system for agents with LRU cache.

    Provides key-value storage with optional persistence for agent state,
    learned information, and context.

    FIXED: Added cache size limits and thread safety.

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
        max_cache_size: int = 1000,
    ):
        """
        Initialize agent memory.

        Args:
            agent_id: Unique identifier for the agent
            store: Storage backend (defaults to InMemoryStore)
            auto_save: Automatically save changes
            max_cache_size: Maximum cache entries (LRU eviction)
        """
        self.agent_id = agent_id
        self.store = store or InMemoryStore()
        self.auto_save = auto_save
        self.max_cache_size = max_cache_size
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._cache_lock = asyncio.Lock()

    async def save(self, key: str, value: Any, metadata: Optional[Dict] = None):
        """
        Save a value to memory.

        Args:
            key: Memory key
            value: Value to store
            metadata: Optional metadata
        """
        async with self._cache_lock:
            # Add to cache with LRU eviction
            if key in self._cache:
                # Move to end (most recent)
                self._cache.move_to_end(key)
            self._cache[key] = value

            # Evict oldest if over limit
            while len(self._cache) > self.max_cache_size:
                self._cache.popitem(last=False)

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
        async with self._cache_lock:
            if key in self._cache:
                # Move to end (most recent)
                self._cache.move_to_end(key)
                return self._cache[key]

        value = await self.store.load(self.agent_id, key)
        if value is not None:
            async with self._cache_lock:
                self._cache[key] = value
            return value

        return default

    async def load_all(self) -> Dict[str, Any]:
        """Load all memory entries."""
        data = await self.store.load_all(self.agent_id)
        async with self._cache_lock:
            self._cache.update(data)
            # Evict if over limit
            while len(self._cache) > self.max_cache_size:
                self._cache.popitem(last=False)
        return data

    async def delete(self, key: str):
        """Delete a memory entry."""
        async with self._cache_lock:
            self._cache.pop(key, None)
        await self.store.delete(self.agent_id, key)

    async def clear(self):
        """Clear all memory."""
        async with self._cache_lock:
            self._cache.clear()
        await self.store.clear(self.agent_id)

    async def flush(self):
        """Flush cache to storage."""
        async with self._cache_lock:
            items = list(self._cache.items())

        for key, value in items:
            await self.store.save(self.agent_id, key, value)

    def get_cache(self) -> Dict[str, Any]:
        """Get current cache contents (snapshot)."""
        return dict(self._cache)

    def __repr__(self) -> str:
        return f"AgentMemory(agent_id={self.agent_id}, entries={len(self._cache)})"

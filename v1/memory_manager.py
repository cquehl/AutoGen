"""
Memory Manager for AutoGen CLI Agent

Provides persistent memory storage across sessions, allowing the agent
to remember context from previous conversations.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from collections import deque


@dataclass
class Memory:
    """Represents a single memory entry."""
    id: str
    content: str
    timestamp: str
    session_id: str
    importance: int = 5  # 1-10 scale
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> 'Memory':
        return Memory(**data)


@dataclass
class Session:
    """Represents a conversation session."""
    id: str
    start_time: str
    end_time: Optional[str] = None
    team: str = "default"
    message_count: int = 0
    summary: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> 'Session':
        return Session(**data)


class MemoryManager:
    """Manages persistent memories and session context."""

    def __init__(
        self,
        memory_dir: Path = None,
        max_memories: int = 100,
        max_context_memories: int = 10
    ):
        """
        Initialize the memory manager.

        Args:
            memory_dir: Directory to store memories (default: ~/.autogen_cli)
            max_memories: Maximum number of memories to keep
            max_context_memories: Max memories to inject into agent context
        """
        if memory_dir is None:
            memory_dir = Path.home() / ".autogen_cli"

        self.memory_dir = memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        self.memory_file = self.memory_dir / "memories.json"
        self.session_file = self.memory_dir / "sessions.json"

        self.max_memories = max_memories
        self.max_context_memories = max_context_memories

        self.memories: List[Memory] = []
        self.sessions: List[Session] = []
        self.current_session: Optional[Session] = None

        self._load()

    def _load(self):
        """Load memories and sessions from disk."""
        # Load memories
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r') as f:
                    data = json.load(f)
                    self.memories = [Memory.from_dict(m) for m in data]
            except Exception as e:
                print(f"Warning: Could not load memories: {e}")
                self.memories = []

        # Load sessions
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r') as f:
                    data = json.load(f)
                    self.sessions = [Session.from_dict(s) for s in data]
            except Exception as e:
                print(f"Warning: Could not load sessions: {e}")
                self.sessions = []

    def _save(self):
        """Save memories and sessions to disk."""
        # Save memories
        try:
            with open(self.memory_file, 'w') as f:
                json.dump([m.to_dict() for m in self.memories], f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save memories: {e}")

        # Save sessions
        try:
            with open(self.session_file, 'w') as f:
                json.dump([s.to_dict() for s in self.sessions], f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save sessions: {e}")

    def start_session(self, team: str = "default") -> Session:
        """Start a new conversation session."""
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_session = Session(
            id=session_id,
            start_time=datetime.now().isoformat(),
            team=team
        )
        self.sessions.append(self.current_session)
        self._save()
        return self.current_session

    def end_session(self, summary: str = ""):
        """End the current session."""
        if self.current_session:
            self.current_session.end_time = datetime.now().isoformat()
            self.current_session.summary = summary
            self._save()
            self.current_session = None

    def get_last_session(self) -> Optional[Session]:
        """Get the most recent session."""
        if self.sessions:
            return self.sessions[-1]
        return None

    def add_memory(
        self,
        content: str,
        importance: int = 5,
        tags: List[str] = None
    ) -> Memory:
        """
        Add a new memory.

        Args:
            content: The memory content
            importance: Importance score (1-10)
            tags: Optional tags for categorization

        Returns:
            The created Memory object
        """
        memory_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        session_id = self.current_session.id if self.current_session else "no_session"

        memory = Memory(
            id=memory_id,
            content=content,
            timestamp=datetime.now().isoformat(),
            session_id=session_id,
            importance=importance,
            tags=tags or []
        )

        self.memories.append(memory)

        # Prune old memories if we exceed max
        self._prune_memories()

        self._save()
        return memory

    def _prune_memories(self):
        """Remove old, low-importance memories to stay under max_memories."""
        if len(self.memories) > self.max_memories:
            # Sort by importance (descending) and timestamp (recent first)
            self.memories.sort(
                key=lambda m: (m.importance, m.timestamp),
                reverse=True
            )
            # Keep only the top max_memories
            self.memories = self.memories[:self.max_memories]

    def get_memories(
        self,
        limit: int = None,
        min_importance: int = 0,
        tags: List[str] = None,
        session_id: str = None
    ) -> List[Memory]:
        """
        Retrieve memories with optional filtering.

        Args:
            limit: Maximum number of memories to return
            min_importance: Minimum importance score
            tags: Filter by tags (any match)
            session_id: Filter by session ID

        Returns:
            List of matching memories
        """
        filtered = self.memories

        # Filter by importance
        if min_importance > 0:
            filtered = [m for m in filtered if m.importance >= min_importance]

        # Filter by tags
        if tags:
            filtered = [
                m for m in filtered
                if any(tag in m.tags for tag in tags)
            ]

        # Filter by session
        if session_id:
            filtered = [m for m in filtered if m.session_id == session_id]

        # Sort by importance and recency
        filtered.sort(key=lambda m: (m.importance, m.timestamp), reverse=True)

        # Apply limit
        if limit:
            filtered = filtered[:limit]

        return filtered

    def get_context_memories(self) -> List[Memory]:
        """
        Get the most relevant memories for current context.

        Returns memories sorted by importance and recency, limited to
        max_context_memories.
        """
        return self.get_memories(limit=self.max_context_memories, min_importance=3)

    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory by ID.

        Args:
            memory_id: The memory ID to delete

        Returns:
            True if deleted, False if not found
        """
        original_count = len(self.memories)
        self.memories = [m for m in self.memories if m.id != memory_id]

        if len(self.memories) < original_count:
            self._save()
            return True
        return False

    def clear_all_memories(self):
        """Delete all memories."""
        self.memories = []
        self._save()

    def format_memories_for_context(self, memories: List[Memory] = None) -> str:
        """
        Format memories into a string suitable for agent context.

        Args:
            memories: Specific memories to format (default: use context memories)

        Returns:
            Formatted string
        """
        if memories is None:
            memories = self.get_context_memories()

        if not memories:
            return ""

        lines = ["## Previous Context (From Memory)"]
        lines.append("")

        for memory in memories:
            timestamp = memory.timestamp.split('T')[0]  # Just date
            lines.append(f"- [{timestamp}] {memory.content}")

        lines.append("")
        return "\n".join(lines)

    def get_session_summary(self, session_id: str = None) -> str:
        """
        Get summary of a specific session.

        Args:
            session_id: Session ID (default: current session)

        Returns:
            Session summary string
        """
        if session_id is None and self.current_session:
            session_id = self.current_session.id

        session = next((s for s in self.sessions if s.id == session_id), None)
        if not session:
            return "Session not found"

        return f"""
Session: {session.id}
Started: {session.start_time}
Ended: {session.end_time or 'Active'}
Team: {session.team}
Messages: {session.message_count}
Summary: {session.summary or 'No summary'}
        """.strip()

    def increment_message_count(self):
        """Increment message counter for current session."""
        if self.current_session:
            self.current_session.message_count += 1
            self._save()

    def search_memories(self, query: str, limit: int = 5) -> List[Memory]:
        """
        Simple keyword search through memories.

        Args:
            query: Search query
            limit: Max results

        Returns:
            List of matching memories
        """
        query_lower = query.lower()
        matches = [
            m for m in self.memories
            if query_lower in m.content.lower()
        ]

        # Sort by importance and recency
        matches.sort(key=lambda m: (m.importance, m.timestamp), reverse=True)

        return matches[:limit]

    def get_stats(self) -> dict:
        """Get memory system statistics."""
        return {
            "total_memories": len(self.memories),
            "total_sessions": len(self.sessions),
            "current_session": self.current_session.id if self.current_session else None,
            "max_memories": self.max_memories,
            "oldest_memory": self.memories[0].timestamp if self.memories else None,
            "newest_memory": self.memories[-1].timestamp if self.memories else None,
        }

"""
Conversation history management for agents.
"""

import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

from ..observability.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ConversationMessage:
    """Single message in a conversation."""
    role: str  # "user", "assistant", "system"
    content: str
    name: Optional[str] = None  # Agent/user name
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.name:
            data["name"] = self.name
        if self.metadata:
            data["metadata"] = self.metadata
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationMessage":
        """Create from dictionary."""
        return cls(
            role=data["role"],
            content=data["content"],
            name=data.get("name"),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            metadata=data.get("metadata", {}),
        )


class ConversationHistory:
    """
    Manages conversation history for agents.

    Provides message storage, retrieval, and summarization capabilities.

    Example:
        >>> history = ConversationHistory("conversation_123")
        >>>
        >>> # Add messages
        >>> history.add_message("user", "Hello!")
        >>> history.add_message("assistant", "Hi there!", name="Agent1")
        >>>
        >>> # Get recent messages
        >>> recent = history.get_messages(limit=10)
        >>>
        >>> # Save/load
        >>> await history.save()
        >>> await history.load()
    """

    def __init__(
        self,
        conversation_id: str,
        max_messages: Optional[int] = None,
        storage_path: Optional[str] = None,
    ):
        """
        Initialize conversation history.

        Args:
            conversation_id: Unique conversation identifier
            max_messages: Maximum messages to keep (None for unlimited)
            storage_path: Directory for saving conversations
        """
        self.conversation_id = conversation_id
        self.max_messages = max_messages
        self.storage_path = Path(storage_path) if storage_path else Path(".autogen_conversations")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.messages: List[ConversationMessage] = []
        self.metadata: Dict[str, Any] = {
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
        }

    def add_message(
        self,
        role: str,
        content: str,
        name: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> ConversationMessage:
        """
        Add a message to the conversation.

        Args:
            role: Message role (user, assistant, system)
            content: Message content
            name: Optional agent/user name
            metadata: Optional metadata

        Returns:
            Created ConversationMessage
        """
        message = ConversationMessage(
            role=role,
            content=content,
            name=name,
            metadata=metadata or {},
        )

        self.messages.append(message)

        # Enforce max_messages limit
        if self.max_messages and len(self.messages) > self.max_messages:
            # Keep most recent messages
            self.messages = self.messages[-self.max_messages:]

        self.metadata["last_updated"] = datetime.now().isoformat()
        self.metadata["message_count"] = len(self.messages)

        return message

    def get_messages(
        self,
        role: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[ConversationMessage]:
        """
        Get messages from history.

        Args:
            role: Filter by role (None for all)
            limit: Maximum messages to return
            offset: Number of messages to skip from start

        Returns:
            List of messages
        """
        messages = self.messages

        # Filter by role
        if role:
            messages = [m for m in messages if m.role == role]

        # Apply offset and limit
        if offset:
            messages = messages[offset:]
        if limit:
            messages = messages[-limit:]

        return messages

    def get_last_message(self, role: Optional[str] = None) -> Optional[ConversationMessage]:
        """
        Get the last message.

        Args:
            role: Optional role filter

        Returns:
            Last message or None
        """
        if role:
            role_messages = self.get_messages(role=role)
            return role_messages[-1] if role_messages else None
        return self.messages[-1] if self.messages else None

    def clear(self):
        """Clear all messages."""
        self.messages.clear()
        self.metadata["last_updated"] = datetime.now().isoformat()
        self.metadata["message_count"] = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "conversation_id": self.conversation_id,
            "messages": [msg.to_dict() for msg in self.messages],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationHistory":
        """Create from dictionary."""
        history = cls(data["conversation_id"])
        history.messages = [
            ConversationMessage.from_dict(msg_data)
            for msg_data in data.get("messages", [])
        ]
        history.metadata = data.get("metadata", {})
        return history

    async def save(self, file_path: Optional[Path] = None):
        """
        Save conversation to file.

        Args:
            file_path: Optional custom file path
        """
        if file_path is None:
            safe_id = self.conversation_id.replace("/", "_").replace("\\", "_")
            file_path = self.storage_path / f"{safe_id}.json"

        data = self.to_dict()

        try:
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved conversation {self.conversation_id} to {file_path}")
        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
            raise

    async def load(self, file_path: Optional[Path] = None):
        """
        Load conversation from file.

        Args:
            file_path: Optional custom file path
        """
        if file_path is None:
            safe_id = self.conversation_id.replace("/", "_").replace("\\", "_")
            file_path = self.storage_path / f"{safe_id}.json"

        if not file_path.exists():
            logger.warning(f"Conversation file not found: {file_path}")
            return

        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            loaded_history = self.from_dict(data)
            self.messages = loaded_history.messages
            self.metadata = loaded_history.metadata

            logger.debug(f"Loaded conversation {self.conversation_id} from {file_path}")
        except Exception as e:
            logger.error(f"Error loading conversation: {e}")
            raise

    def format_for_llm(
        self,
        limit: Optional[int] = None,
        include_system: bool = True,
    ) -> List[Dict[str, str]]:
        """
        Format messages for LLM input.

        Args:
            limit: Maximum messages to include
            include_system: Whether to include system messages

        Returns:
            List of message dictionaries for LLM
        """
        messages = self.get_messages(limit=limit)

        formatted = []
        for msg in messages:
            if not include_system and msg.role == "system":
                continue

            msg_dict = {"role": msg.role, "content": msg.content}
            if msg.name:
                msg_dict["name"] = msg.name

            formatted.append(msg_dict)

        return formatted

    def get_summary(self) -> str:
        """
        Get a text summary of the conversation.

        Returns:
            Summary string
        """
        total = len(self.messages)
        by_role = {}
        for msg in self.messages:
            by_role[msg.role] = by_role.get(msg.role, 0) + 1

        summary_parts = [
            f"Conversation: {self.conversation_id}",
            f"Total messages: {total}",
            f"By role: {', '.join(f'{role}: {count}' for role, count in by_role.items())}",
        ]

        if self.messages:
            first_msg = self.messages[0]
            last_msg = self.messages[-1]
            summary_parts.append(f"Started: {first_msg.timestamp.isoformat()}")
            summary_parts.append(f"Last update: {last_msg.timestamp.isoformat()}")

        return "\n".join(summary_parts)

    def __len__(self) -> int:
        return len(self.messages)

    def __repr__(self) -> str:
        return f"ConversationHistory(id={self.conversation_id}, messages={len(self.messages)})"

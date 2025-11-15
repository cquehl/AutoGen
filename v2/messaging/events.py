"""
Event types for the message bus.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from datetime import datetime
from enum import Enum


class EventType(Enum):
    """Types of events in the system."""
    AGENT_MESSAGE = "agent_message"
    TOOL_EXECUTION = "tool_execution"
    WORKFLOW_START = "workflow_start"
    WORKFLOW_END = "workflow_end"
    WORKFLOW_NODE = "workflow_node"
    SYSTEM_ERROR = "system_error"
    SYSTEM_INFO = "system_info"


@dataclass
class Event:
    """Base event class."""
    event_type: EventType = EventType.SYSTEM_INFO
    event_id: Optional[str] = field(default=None)
    timestamp: datetime = field(default_factory=lambda: datetime.now())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "event_id": self.event_id,
        }


@dataclass
class AgentMessageEvent(Event):
    """Event for agent messages."""
    agent_name: str = ""
    role: str = "assistant"  # "user", "assistant", "system"
    content: str = ""
    recipient: Optional[str] = None  # Target agent name
    conversation_id: Optional[str] = None

    def __post_init__(self):
        self.event_type = EventType.AGENT_MESSAGE

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "agent_name": self.agent_name,
            "role": self.role,
            "content": self.content,
            "recipient": self.recipient,
            "conversation_id": self.conversation_id,
        })
        return data


@dataclass
class ToolExecutionEvent(Event):
    """Event for tool execution."""
    tool_name: str = ""
    agent_name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    success: bool = True
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None

    def __post_init__(self):
        self.event_type = EventType.TOOL_EXECUTION

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "tool_name": self.tool_name,
            "agent_name": self.agent_name,
            "parameters": self.parameters,
            "success": self.success,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
        })
        return data


@dataclass
class WorkflowEvent(Event):
    """Event for workflow state changes."""
    workflow_id: str = ""
    node_name: Optional[str] = None
    status: str = "running"  # "running", "completed", "failed"
    payload: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Determine event type based on status
        if self.status == "running" and not self.node_name:
            self.event_type = EventType.WORKFLOW_START
        elif self.status in ("completed", "failed"):
            self.event_type = EventType.WORKFLOW_END
        else:
            self.event_type = EventType.WORKFLOW_NODE

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "workflow_id": self.workflow_id,
            "node_name": self.node_name,
            "status": self.status,
            "payload": self.payload,
        })
        return data


@dataclass
class SystemEvent(Event):
    """Event for system-level notifications."""
    level: str = "info"  # "info", "warning", "error"
    message: str = ""
    component: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.level == "error":
            self.event_type = EventType.SYSTEM_ERROR
        else:
            self.event_type = EventType.SYSTEM_INFO

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "level": self.level,
            "message": self.message,
            "component": self.component,
            "error_details": self.error_details,
        })
        return data

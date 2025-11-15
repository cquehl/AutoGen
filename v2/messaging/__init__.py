"""
Event-driven message bus for agent communication.

Provides centralized, observable message passing between agents inspired
by AutoGen 0.7.x event-driven architecture.
"""

from .message_bus import MessageBus, Message
from .events import (
    Event,
    AgentMessageEvent,
    ToolExecutionEvent,
    WorkflowEvent,
    SystemEvent,
)
from .handlers import EventHandler, LoggingHandler, MetricsHandler

__all__ = [
    "MessageBus",
    "Message",
    "Event",
    "AgentMessageEvent",
    "ToolExecutionEvent",
    "WorkflowEvent",
    "SystemEvent",
    "EventHandler",
    "LoggingHandler",
    "MetricsHandler",
]

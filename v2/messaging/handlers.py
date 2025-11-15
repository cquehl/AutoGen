"""
Event handlers for the message bus.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from collections import defaultdict
import time

from .events import Event, EventType, AgentMessageEvent, ToolExecutionEvent
from ..observability.logger import get_logger

logger = get_logger(__name__)


class EventHandler(ABC):
    """Base class for event handlers."""

    @abstractmethod
    async def handle(self, event: Event):
        """
        Handle an event.

        Args:
            event: Event to handle
        """
        pass


class LoggingHandler(EventHandler):
    """Handler that logs all events."""

    def __init__(self, log_level: str = "INFO"):
        """
        Initialize logging handler.

        Args:
            log_level: Log level (DEBUG, INFO, WARNING, ERROR)
        """
        self.log_level = log_level.upper()

    async def handle(self, event: Event):
        """Log the event."""
        if self.log_level == "DEBUG":
            logger.debug(f"Event: {event.event_type.value} - {event.to_dict()}")
        else:
            # Log summary for non-debug levels
            if isinstance(event, AgentMessageEvent):
                logger.info(f"[{event.agent_name}] {event.content[:100]}...")
            elif isinstance(event, ToolExecutionEvent):
                status = "✓" if event.success else "✗"
                logger.info(f"{status} Tool: {event.tool_name} by {event.agent_name}")
            else:
                logger.info(f"Event: {event.event_type.value}")


class MetricsHandler(EventHandler):
    """Handler that collects metrics from events."""

    def __init__(self):
        """Initialize metrics handler."""
        self.metrics = {
            "event_counts": defaultdict(int),
            "agent_message_counts": defaultdict(int),
            "tool_execution_counts": defaultdict(int),
            "tool_success_counts": defaultdict(int),
            "tool_failure_counts": defaultdict(int),
            "total_tool_execution_time_ms": defaultdict(float),
        }
        self.start_time = time.time()

    async def handle(self, event: Event):
        """Collect metrics from event."""
        # Count events by type
        self.metrics["event_counts"][event.event_type.value] += 1

        # Agent-specific metrics
        if isinstance(event, AgentMessageEvent):
            self.metrics["agent_message_counts"][event.agent_name] += 1

        # Tool-specific metrics
        elif isinstance(event, ToolExecutionEvent):
            self.metrics["tool_execution_counts"][event.tool_name] += 1

            if event.success:
                self.metrics["tool_success_counts"][event.tool_name] += 1
            else:
                self.metrics["tool_failure_counts"][event.tool_name] += 1

            if event.execution_time_ms:
                self.metrics["total_tool_execution_time_ms"][event.tool_name] += event.execution_time_ms

    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics."""
        uptime = time.time() - self.start_time

        return {
            "uptime_seconds": uptime,
            "event_counts": dict(self.metrics["event_counts"]),
            "agent_message_counts": dict(self.metrics["agent_message_counts"]),
            "tool_execution_counts": dict(self.metrics["tool_execution_counts"]),
            "tool_success_counts": dict(self.metrics["tool_success_counts"]),
            "tool_failure_counts": dict(self.metrics["tool_failure_counts"]),
            "tool_avg_execution_time_ms": self._calculate_avg_execution_times(),
        }

    def _calculate_avg_execution_times(self) -> Dict[str, float]:
        """Calculate average execution times for tools."""
        avg_times = {}
        for tool_name, total_time in self.metrics["total_tool_execution_time_ms"].items():
            count = self.metrics["tool_execution_counts"][tool_name]
            if count > 0:
                avg_times[tool_name] = total_time / count
        return avg_times

    def reset(self):
        """Reset all metrics."""
        self.metrics = {
            "event_counts": defaultdict(int),
            "agent_message_counts": defaultdict(int),
            "tool_execution_counts": defaultdict(int),
            "tool_success_counts": defaultdict(int),
            "tool_failure_counts": defaultdict(int),
            "total_tool_execution_time_ms": defaultdict(float),
        }
        self.start_time = time.time()


class HistoryHandler(EventHandler):
    """Handler that maintains a searchable event history."""

    def __init__(self, max_events: int = 10000):
        """
        Initialize history handler.

        Args:
            max_events: Maximum events to store
        """
        self.max_events = max_events
        self.events = []
        self.events_by_type = defaultdict(list)
        self.events_by_agent = defaultdict(list)

    async def handle(self, event: Event):
        """Store event in history."""
        # Add to main history
        self.events.append(event)
        if len(self.events) > self.max_events:
            self.events.pop(0)

        # Index by type
        self.events_by_type[event.event_type].append(event)

        # Index by agent if applicable
        if isinstance(event, AgentMessageEvent):
            self.events_by_agent[event.agent_name].append(event)
        elif isinstance(event, ToolExecutionEvent):
            self.events_by_agent[event.agent_name].append(event)

    def search(
        self,
        event_type: Optional[EventType] = None,
        agent_name: Optional[str] = None,
        limit: Optional[int] = None,
    ):
        """
        Search event history.

        Args:
            event_type: Filter by event type
            agent_name: Filter by agent name
            limit: Maximum results

        Returns:
            List of matching events
        """
        if event_type and agent_name:
            # Both filters
            results = [
                e for e in self.events_by_type[event_type]
                if self._event_matches_agent(e, agent_name)
            ]
        elif event_type:
            results = self.events_by_type[event_type]
        elif agent_name:
            results = self.events_by_agent[agent_name]
        else:
            results = self.events

        if limit:
            results = results[-limit:]

        return results

    def _event_matches_agent(self, event: Event, agent_name: str) -> bool:
        """Check if event matches agent name."""
        if isinstance(event, (AgentMessageEvent, ToolExecutionEvent)):
            return event.agent_name == agent_name
        return False

    def clear(self):
        """Clear all history."""
        self.events.clear()
        self.events_by_type.clear()
        self.events_by_agent.clear()

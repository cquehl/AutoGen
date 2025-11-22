"""
Yamazaki v2 - History Service

Provides unified access to conversation history, message bus events, and tool execution logs.
Alfred uses this to answer "What were my last actions?" questions.
"""

from typing import List, Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime, timedelta
from pathlib import Path
import json

from ..observability.logger import get_logger

if TYPE_CHECKING:
    from ..messaging.message_bus import MessageBus
    from ..observability.manager import ObservabilityManager

logger = get_logger(__name__)


class HistoryService:
    """
    Service for unified history access across multiple sources.

    Aggregates:
    - Conversation history (user/assistant messages)
    - Message bus events (agent interactions)
    - Tool execution logs (from observability)
    """

    def __init__(
        self,
        message_bus: "MessageBus",
        observability_manager: "ObservabilityManager"
    ) -> None:
        """Initialize history service."""
        self.message_bus = message_bus
        self.observability_manager = observability_manager
        self.conversation_storage_path = Path(".autogen_conversations")

    def get_recent_actions(
        self,
        limit: int = 5,
        include_conversations: bool = True,
        include_events: bool = True,
        include_tool_executions: bool = True,
    ) -> List[Dict[str, Any]]:
        """Get recent actions across all history sources, sorted by timestamp (newest first)."""
        all_actions = []

        if include_conversations:
            conv_messages = self._get_recent_conversations(limit * 2)
            all_actions.extend(conv_messages)

        if include_events:
            bus_events = self._get_recent_bus_events(limit * 2)
            all_actions.extend(bus_events)

        if include_tool_executions:
            tool_logs = self._get_recent_tool_executions(limit * 2)
            all_actions.extend(tool_logs)

        all_actions.sort(key=lambda x: x.get("timestamp", datetime.min), reverse=True)

        return all_actions[:limit]

    def get_session_history(
        self,
        session_duration_minutes: int = 60,
    ) -> Dict[str, Any]:
        """Get all history from the current session."""
        cutoff_time = datetime.now() - timedelta(minutes=session_duration_minutes)

        recent_actions = self.get_recent_actions(limit=100)

        session_actions = [
            action for action in recent_actions
            if action.get("timestamp", datetime.min) >= cutoff_time
        ]

        categorized = {
            "conversations": [],
            "agent_interactions": [],
            "tool_executions": [],
            "session_start": cutoff_time,
            "session_duration_minutes": session_duration_minutes,
            "total_actions": len(session_actions),
        }

        for action in session_actions:
            action_type = action.get("type", "unknown")
            if action_type == "conversation":
                categorized["conversations"].append(action)
            elif action_type == "event":
                categorized["agent_interactions"].append(action)
            elif action_type == "tool_execution":
                categorized["tool_executions"].append(action)

        return categorized

    def get_history_by_timerange(
        self,
        start: datetime,
        end: datetime,
    ) -> List[Dict[str, Any]]:
        """Get history within a specific time range."""
        all_actions = self.get_recent_actions(limit=1000)

        filtered = [
            action for action in all_actions
            if start <= action.get("timestamp", datetime.min) <= end
        ]

        return filtered

    def _get_recent_conversations(self, limit: int) -> List[Dict[str, Any]]:
        """Get recent conversation messages from stored conversations."""
        conversations = []

        try:
            if not self.conversation_storage_path.exists():
                return []

            conv_files = sorted(
                self.conversation_storage_path.glob("*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

            for conv_file in conv_files[:5]:
                try:
                    with open(conv_file, "r") as f:
                        data = json.load(f)

                    for msg in data.get("messages", []):
                        # Safely parse timestamp with fallback to current time
                        timestamp_str = msg.get("timestamp")
                        try:
                            timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else datetime.now()
                        except (ValueError, TypeError):
                            timestamp = datetime.now()

                        conversations.append({
                            "type": "conversation",
                            "role": msg.get("role"),
                            "content": msg.get("content"),
                            "name": msg.get("name"),
                            "timestamp": timestamp,
                            "conversation_id": data.get("conversation_id"),
                        })
                except Exception as e:
                    logger.error(f"Error loading conversation {conv_file}: {e}")

        except Exception as e:
            logger.error(f"Error accessing conversation history: {e}")

        conversations.sort(key=lambda x: x["timestamp"], reverse=True)
        return conversations[:limit]

    def _get_recent_bus_events(self, limit: int) -> List[Dict[str, Any]]:
        """Get recent message bus events."""
        events = []

        try:
            if not self.message_bus:
                logger.warning("Message bus not available for history retrieval")
                return events

            bus_events = self.message_bus.get_history(limit=limit)

            for event in bus_events:
                events.append({
                    "type": "event",
                    "event_type": event.event_type.value if hasattr(event, 'event_type') else "unknown",
                    "event_id": getattr(event, 'event_id', 'unknown'),
                    "timestamp": getattr(event, 'timestamp', datetime.now()),
                    "data": getattr(event, 'data', {}),
                })

        except Exception as e:
            logger.error(f"Error accessing message bus events: {e}", exc_info=True)

        return events

    def _get_recent_tool_executions(self, limit: int) -> List[Dict[str, Any]]:
        """Get recent tool execution events from message bus."""
        tool_executions = []

        try:
            from ..messaging.events import EventType

            bus_events = self.message_bus.get_history(
                event_type=EventType.TOOL_EXECUTION,
                limit=limit,
            )

            for event in bus_events:
                tool_executions.append({
                    "type": "tool_execution",
                    "tool_name": event.data.get("tool_name"),
                    "result": event.data.get("result"),
                    "success": event.data.get("success"),
                    "timestamp": event.timestamp,
                    "event_id": event.event_id,
                })

        except Exception as e:
            logger.error(f"Error accessing tool execution logs: {e}")

        return tool_executions

    def format_history_for_display(
        self,
        history: List[Dict[str, Any]],
        include_details: bool = False,
    ) -> str:
        """Format history in a conversational, user-friendly format for Alfred."""
        if not history:
            return "No recent activity found."

        output = []

        for idx, item in enumerate(history, 1):
            item_type = item.get("type", "unknown")
            timestamp = item.get("timestamp")

            if isinstance(timestamp, datetime):
                time_str = timestamp.strftime("%Y-%m-%d %H:%M")
            else:
                time_str = "Unknown time"

            if item_type == "conversation":
                role = item.get("role", "unknown")
                content = item.get("content", "")
                name = item.get("name", role)

                # Truncate long content unless details requested
                if len(content) > 100 and not include_details:
                    content = content[:97] + "..."

                output.append(f"{idx}. [{time_str}] {name}: {content}")

            elif item_type == "event":
                event_type = item.get("event_type", "unknown")
                output.append(f"{idx}. [{time_str}] Event: {event_type}")

                if include_details:
                    data = item.get("data", {})
                    for key, value in data.items():
                        output.append(f"   - {key}: {value}")

            elif item_type == "tool_execution":
                tool_name = item.get("tool_name", "unknown")
                success = item.get("success", False)
                status = "✓" if success else "✗"

                output.append(f"{idx}. [{time_str}] Tool: {tool_name} {status}")

                if include_details:
                    result = item.get("result", "No result")
                    output.append(f"   Result: {result}")

        return "\n".join(output)

    def format_session_history(self, session: Dict[str, Any]) -> str:
        """Format session history for conversational display."""
        output = []

        output.append(f"**Session Summary:**")
        output.append(f"Duration: {session['session_duration_minutes']} minutes")
        output.append(f"Total Actions: {session['total_actions']}")

        # Conversations
        if session["conversations"]:
            output.append(f"\n**Conversations ({len(session['conversations'])}):**")
            for conv in session["conversations"][:5]:
                role = conv.get("role", "unknown")
                content = conv.get("content", "")[:80]
                output.append(f"- {role}: {content}...")

        # Agent interactions
        if session["agent_interactions"]:
            output.append(f"\n**Agent Interactions ({len(session['agent_interactions'])}):**")
            for interaction in session["agent_interactions"][:5]:
                event_type = interaction.get("event_type", "unknown")
                output.append(f"- {event_type}")

        # Tool executions
        if session["tool_executions"]:
            output.append(f"\n**Tool Executions ({len(session['tool_executions'])}):**")
            for execution in session["tool_executions"][:5]:
                tool_name = execution.get("tool_name", "unknown")
                success = "✓" if execution.get("success") else "✗"
                output.append(f"- {tool_name} {success}")

        return "\n".join(output)

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall history statistics."""
        recent_actions = self.get_recent_actions(limit=1000)

        stats = {
            "total_recent_actions": len(recent_actions),
            "by_type": {
                "conversations": len([a for a in recent_actions if a["type"] == "conversation"]),
                "events": len([a for a in recent_actions if a["type"] == "event"]),
                "tool_executions": len([a for a in recent_actions if a["type"] == "tool_execution"]),
            },
            "message_bus_stats": self.message_bus.get_stats(),
        }

        return stats

    def clear_session_history(self):
        """Clear all session history (warning: destructive operation)."""
        logger.warning("Clearing all session history")
        self.message_bus.clear_history()
        logger.info("Session history cleared")

    def __repr__(self) -> str:
        stats = self.get_statistics()
        return (
            f"HistoryService("
            f"recent_actions={stats['total_recent_actions']}, "
            f"conversations={stats['by_type']['conversations']}, "
            f"events={stats['by_type']['events']})"
        )

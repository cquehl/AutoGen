"""
Condition functions for workflow edge routing.

Inspired by AutoGen 0.7.x callable conditions.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Dict, Callable
import re


class Condition(ABC):
    """Base class for workflow conditions."""

    @abstractmethod
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Evaluate the condition.

        Args:
            context: Current workflow context including messages, state, etc.

        Returns:
            True if condition is met, False otherwise
        """
        pass

    def __call__(self, context: Dict[str, Any]) -> bool:
        """Make condition callable."""
        return self.evaluate(context)


class MessageCountCondition(Condition):
    """Condition based on message count."""

    def __init__(self, count: int, operator: str = ">="):
        """
        Initialize message count condition.

        Args:
            count: Message count threshold
            operator: Comparison operator (>=, <=, ==, >, <)
        """
        self.count = count
        self.operator = operator

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate based on message count."""
        messages = context.get("messages", [])
        msg_count = len(messages)

        if self.operator == ">=":
            return msg_count >= self.count
        elif self.operator == "<=":
            return msg_count <= self.count
        elif self.operator == "==":
            return msg_count == self.count
        elif self.operator == ">":
            return msg_count > self.count
        elif self.operator == "<":
            return msg_count < self.count
        else:
            raise ValueError(f"Unknown operator: {self.operator}")


class ContentCondition(Condition):
    """Condition based on message content."""

    def __init__(self, pattern: str, match_type: str = "contains"):
        """
        Initialize content condition.

        Args:
            pattern: Pattern to match
            match_type: Type of matching (contains, regex, equals)
        """
        self.pattern = pattern
        self.match_type = match_type

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate based on message content."""
        last_message = context.get("last_message", {})
        content = last_message.get("content", "")

        if self.match_type == "contains":
            return self.pattern.lower() in content.lower()
        elif self.match_type == "regex":
            return bool(re.search(self.pattern, content, re.IGNORECASE))
        elif self.match_type == "equals":
            return content.strip().lower() == self.pattern.lower()
        else:
            raise ValueError(f"Unknown match type: {self.match_type}")


class StateCondition(Condition):
    """Condition based on workflow state."""

    def __init__(self, key: str, value: Any, operator: str = "=="):
        """
        Initialize state condition.

        Args:
            key: State key to check
            value: Expected value
            operator: Comparison operator (==, !=, >, <, >=, <=, in)
        """
        self.key = key
        self.value = value
        self.operator = operator

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate based on state value."""
        state = context.get("state", {})
        state_value = state.get(self.key)

        if self.operator == "==":
            return state_value == self.value
        elif self.operator == "!=":
            return state_value != self.value
        elif self.operator == ">":
            return state_value > self.value
        elif self.operator == "<":
            return state_value < self.value
        elif self.operator == ">=":
            return state_value >= self.value
        elif self.operator == "<=":
            return state_value <= self.value
        elif self.operator == "in":
            return state_value in self.value
        else:
            raise ValueError(f"Unknown operator: {self.operator}")


class CompositeCondition(Condition):
    """Composite condition combining multiple conditions."""

    def __init__(self, conditions: List[Condition], logic: str = "AND"):
        """
        Initialize composite condition.

        Args:
            conditions: List of conditions to combine
            logic: Logic operator (AND, OR)
        """
        self.conditions = conditions
        self.logic = logic.upper()

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate composite condition."""
        results = [cond.evaluate(context) for cond in self.conditions]

        if self.logic == "AND":
            return all(results)
        elif self.logic == "OR":
            return any(results)
        else:
            raise ValueError(f"Unknown logic operator: {self.logic}")


class LambdaCondition(Condition):
    """Condition using a lambda function."""

    def __init__(self, func: Callable[[Dict[str, Any]], bool]):
        """
        Initialize lambda condition.

        Args:
            func: Callable that takes context and returns bool
        """
        self.func = func

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate using lambda function."""
        return self.func(context)


class MaxRetriesCondition(Condition):
    """Condition based on retry count."""

    def __init__(self, max_retries: int):
        """
        Initialize max retries condition.

        Args:
            max_retries: Maximum number of retries allowed
        """
        self.max_retries = max_retries

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate based on retry count."""
        retry_count = context.get("retry_count", 0)
        return retry_count < self.max_retries


# Convenience functions for creating conditions
def message_count_at_least(count: int) -> MessageCountCondition:
    """Create a condition for minimum message count."""
    return MessageCountCondition(count, ">=")


def message_contains(pattern: str) -> ContentCondition:
    """Create a condition for message content containing pattern."""
    return ContentCondition(pattern, "contains")


def state_equals(key: str, value: Any) -> StateCondition:
    """Create a condition for state equality."""
    return StateCondition(key, value, "==")


def all_of(*conditions: Condition) -> CompositeCondition:
    """Create an AND condition from multiple conditions."""
    return CompositeCondition(list(conditions), "AND")


def any_of(*conditions: Condition) -> CompositeCondition:
    """Create an OR condition from multiple conditions."""
    return CompositeCondition(list(conditions), "OR")

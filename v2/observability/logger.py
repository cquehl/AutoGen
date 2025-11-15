"""
Yamazaki v2 - Structured Logging

Structured logging with JSON and console formats.
"""

import logging
import sys
import json
from typing import Any, Dict
from datetime import datetime


class StructuredFormatter(logging.Formatter):
    """
    Structured logging formatter.

    Outputs logs as JSON for machine parsing or pretty console format.
    """

    def __init__(self, format_type: str = "console"):
        """
        Initialize formatter.

        Args:
            format_type: "json" or "console"
        """
        super().__init__()
        self.format_type = format_type

    def format(self, record: logging.LogRecord) -> str:
        """Format log record"""
        if self.format_type == "json":
            return self._format_json(record)
        else:
            return self._format_console(record)

    def _format_json(self, record: logging.LogRecord) -> str:
        """Format as JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)

    def _format_console(self, record: logging.LogRecord) -> str:
        """Format for console"""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        # Color codes for different levels
        colors = {
            "DEBUG": "\033[36m",     # Cyan
            "INFO": "\033[32m",      # Green
            "WARNING": "\033[33m",   # Yellow
            "ERROR": "\033[31m",     # Red
            "CRITICAL": "\033[35m",  # Magenta
        }
        reset = "\033[0m"

        level_color = colors.get(record.levelname, "")

        # Format message
        msg = f"{level_color}[{record.levelname}]{reset} {timestamp} - {record.name} - {record.getMessage()}"

        # Add exception if present
        if record.exc_info:
            msg += f"\n{self.formatException(record.exc_info)}"

        return msg


def setup_logging(config):
    """
    Setup structured logging.

    Args:
        config: ObservabilityConfig
    """
    # Create root logger
    logger = logging.getLogger("yamazaki")
    logger.setLevel(getattr(logging, config.log_level))

    # Remove existing handlers
    logger.handlers.clear()

    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, config.log_level))

    # Create formatter
    formatter = StructuredFormatter(format_type=config.log_format)
    handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(handler)

    return logger


def get_logger(name: str = "yamazaki") -> logging.Logger:
    """
    Get logger instance.

    Args:
        name: Logger name (defaults to "yamazaki")

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter with context.

    Adds contextual information to all log messages.
    """

    def __init__(self, logger: logging.Logger, context: Dict[str, Any]):
        """
        Initialize adapter.

        Args:
            logger: Base logger
            context: Context dict to add to all logs
        """
        super().__init__(logger, context)

    def process(self, msg, kwargs):
        """Add context to log record"""
        if "extra" not in kwargs:
            kwargs["extra"] = {}
        kwargs["extra"].update(self.extra)
        return msg, kwargs


# Convenience methods for structured logging
def log_agent_action(logger: logging.Logger, agent_name: str, action: str, **kwargs):
    """Log agent action with context"""
    logger.info(
        f"Agent action: {agent_name} - {action}",
        extra={
            "event_type": "agent_action",
            "agent_name": agent_name,
            "action": action,
            **kwargs,
        }
    )


def log_tool_execution(
    logger: logging.Logger,
    tool_name: str,
    duration_ms: float,
    success: bool,
    **kwargs
):
    """Log tool execution with metrics"""
    logger.info(
        f"Tool executed: {tool_name} ({duration_ms:.2f}ms) - {'✓' if success else '✗'}",
        extra={
            "event_type": "tool_execution",
            "tool_name": tool_name,
            "duration_ms": duration_ms,
            "success": success,
            **kwargs,
        }
    )


def log_security_event(logger: logging.Logger, event_type: str, details: Dict[str, Any]):
    """Log security event"""
    logger.warning(
        f"Security event: {event_type}",
        extra={
            "event_type": "security",
            "security_event": event_type,
            **details,
        }
    )

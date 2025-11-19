"""
Suntory v3 - Telemetry and Logging
Structured logging with correlation IDs and observability
"""

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any, Dict, Optional

import structlog
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from .config import get_settings

# Context variable for correlation ID
correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def add_correlation_id(
    logger: logging.Logger,
    method_name: str,
    event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Add correlation ID to log entries"""
    cid = correlation_id.get()
    if cid:
        event_dict["correlation_id"] = cid
    return event_dict


def add_trace_context(
    logger: logging.Logger,
    method_name: str,
    event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Add OpenTelemetry trace context to logs"""
    span = trace.get_current_span()
    if span and span.is_recording():
        ctx = span.get_span_context()
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
    return event_dict


def setup_logging(log_level: str = "INFO", log_format: str = "console"):
    """
    Setup structured logging with structlog and OpenTelemetry.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_format: Format type ("console" or "json")
    """
    settings = get_settings()

    # Configure structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        add_correlation_id,
        add_trace_context,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Add appropriate renderer
    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # Setup OpenTelemetry if enabled
    if settings.enable_telemetry:
        setup_telemetry()


def setup_telemetry():
    """Setup OpenTelemetry tracing"""
    settings = get_settings()

    # Create tracer provider
    provider = TracerProvider()

    # Add console exporter for development
    if settings.environment.value == "development":
        processor = BatchSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)

    # Set as global provider
    trace.set_tracer_provider(provider)


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Bound logger instance
    """
    return structlog.get_logger(name)


def set_correlation_id(cid: Optional[str] = None) -> str:
    """
    Set correlation ID for the current context.

    Args:
        cid: Correlation ID (generates UUID if not provided)

    Returns:
        The correlation ID that was set
    """
    if cid is None:
        cid = str(uuid.uuid4())
    correlation_id.set(cid)
    return cid


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID"""
    return correlation_id.get()


def clear_correlation_id():
    """Clear correlation ID from context"""
    correlation_id.set(None)


class LoggerMixin:
    """Mixin to add logging capabilities to classes"""

    @property
    def logger(self) -> structlog.BoundLogger:
        """Get logger for this class"""
        if not hasattr(self, '_logger'):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger


# Initialize logging on import
setup_logging(
    log_level=get_settings().log_level,
    log_format="console" if get_settings().environment.value == "development" else "json"
)

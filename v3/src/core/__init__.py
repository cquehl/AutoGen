"""
Suntory v3 - Core Module
Foundational components for the system
"""

from .config import get_settings, reset_settings, SuntorySettings
from .llm_gateway import get_llm_gateway, reset_llm_gateway, LLMGateway
from .model_factory import (
    get_model_client_factory,
    create_model_client,
    reset_model_factory,
    ModelClientFactory,
)
from .persistence import (
    get_db_manager,
    get_vector_manager,
    reset_persistence,
    DatabaseManager,
    VectorStoreManager,
)
from .telemetry import (
    get_logger,
    set_correlation_id,
    get_correlation_id,
    clear_correlation_id,
    LoggerMixin,
)
from .errors import (
    SuntoryError,
    APIKeyError,
    RateLimitError,
    NetworkError,
    ModelNotFoundError,
    ConfigurationError,
    AgentError,
    ResourceError,
    ValidationError,
    handle_exception,
    log_error,
)
from .cost_tracking import get_cost_tracker, reset_cost_tracker, CostTracker
from .docker_executor import get_docker_executor, reset_docker_executor, DockerExecutor
from .streaming import stream_completion, stream_with_thinking, StreamingResponse

__all__ = [
    # Config
    "get_settings",
    "reset_settings",
    "SuntorySettings",
    # LLM Gateway
    "get_llm_gateway",
    "reset_llm_gateway",
    "LLMGateway",
    # Model Factory
    "get_model_client_factory",
    "create_model_client",
    "reset_model_factory",
    "ModelClientFactory",
    # Persistence
    "get_db_manager",
    "get_vector_manager",
    "reset_persistence",
    "DatabaseManager",
    "VectorStoreManager",
    # Telemetry
    "get_logger",
    "set_correlation_id",
    "get_correlation_id",
    "clear_correlation_id",
    "LoggerMixin",
    # Errors
    "SuntoryError",
    "APIKeyError",
    "RateLimitError",
    "NetworkError",
    "ModelNotFoundError",
    "ConfigurationError",
    "AgentError",
    "ResourceError",
    "ValidationError",
    "handle_exception",
    "log_error",
    # Cost Tracking
    "get_cost_tracker",
    "reset_cost_tracker",
    "CostTracker",
    # Docker Execution
    "get_docker_executor",
    "reset_docker_executor",
    "DockerExecutor",
    # Streaming
    "stream_completion",
    "stream_with_thinking",
    "StreamingResponse",
]

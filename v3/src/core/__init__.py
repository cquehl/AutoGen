"""
Suntory v3 - Core Module
Foundational components for the system
"""

from .config import get_settings, reset_settings, SuntorySettings
from .llm_gateway import get_llm_gateway, reset_llm_gateway, LLMGateway
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

__all__ = [
    # Config
    "get_settings",
    "reset_settings",
    "SuntorySettings",
    # LLM Gateway
    "get_llm_gateway",
    "reset_llm_gateway",
    "LLMGateway",
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
]

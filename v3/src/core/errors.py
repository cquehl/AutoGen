"""
Suntory v3 - Error Handling
Comprehensive error handling with recovery suggestions
"""

from enum import Enum
from typing import List, Optional

from .telemetry import get_logger

logger = get_logger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels"""
    LOW = "low"  # Non-critical, can continue
    MEDIUM = "medium"  # Important but recoverable
    HIGH = "high"  # Critical, requires user action
    FATAL = "fatal"  # Cannot continue


class ErrorCategory(str, Enum):
    """Error categories"""
    API_KEY = "api_key"
    RATE_LIMIT = "rate_limit"
    NETWORK = "network"
    MODEL = "model"
    CONFIGURATION = "configuration"
    AGENT = "agent"
    VALIDATION = "validation"
    RESOURCE = "resource"
    UNKNOWN = "unknown"


class SuntoryError(Exception):
    """Base exception for Suntory system"""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        recovery_suggestions: Optional[List[str]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.recovery_suggestions = recovery_suggestions or []
        self.original_error = original_error

    def format_for_user(self) -> str:
        """Format error message for user display"""
        lines = [
            f"❌ **Error**: {self.message}",
            ""
        ]

        if self.recovery_suggestions:
            lines.append("**How to fix:**")
            for suggestion in self.recovery_suggestions:
                lines.append(f"  • {suggestion}")
            lines.append("")

        if self.severity == ErrorSeverity.FATAL:
            lines.append("⚠️  This is a critical error. Alfred cannot continue.")

        return "\n".join(lines)


class APIKeyError(SuntoryError):
    """API key is missing or invalid"""

    def __init__(self, provider: str, original_error: Optional[Exception] = None):
        super().__init__(
            message=f"API key for {provider} is missing or invalid",
            category=ErrorCategory.API_KEY,
            severity=ErrorSeverity.HIGH,
            recovery_suggestions=[
                f"Add {provider.upper()}_API_KEY to your .env file",
                "Verify the API key is correct and active",
                f"Check {provider}'s documentation for API key format",
                "Try switching to a different provider with /model command"
            ],
            original_error=original_error
        )


class RateLimitError(SuntoryError):
    """Rate limit exceeded"""

    def __init__(self, provider: str, retry_after: Optional[int] = None):
        message = f"Rate limit exceeded for {provider}"
        if retry_after:
            message += f" (retry after {retry_after} seconds)"

        super().__init__(
            message=message,
            category=ErrorCategory.RATE_LIMIT,
            severity=ErrorSeverity.MEDIUM,
            recovery_suggestions=[
                "Wait a moment and try again",
                "Use /model to switch to a different provider",
                "Upgrade your API plan for higher limits",
                "Simplify your request to use fewer tokens"
            ]
        )


class NetworkError(SuntoryError):
    """Network connection error"""

    def __init__(self, original_error: Optional[Exception] = None):
        super().__init__(
            message="Network connection failed",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            recovery_suggestions=[
                "Check your internet connection",
                "Verify firewall settings allow API access",
                "Try again in a moment (automatic retry in progress)",
                "Check if the API service is experiencing downtime"
            ],
            original_error=original_error
        )


class ModelNotFoundError(SuntoryError):
    """Model not available or not found"""

    def __init__(self, model: str, available_models: Optional[List[str]] = None):
        message = f"Model '{model}' not found or not available"

        suggestions = [
            "Check the model name spelling",
            "Verify the model is available in your API tier",
        ]

        if available_models:
            suggestions.append(f"Try one of: {', '.join(available_models[:3])}")
        else:
            suggestions.append("Use /model to see available models")

        super().__init__(
            message=message,
            category=ErrorCategory.MODEL,
            severity=ErrorSeverity.MEDIUM,
            recovery_suggestions=suggestions
        )


class ConfigurationError(SuntoryError):
    """Configuration is invalid or missing"""

    def __init__(self, config_item: str, original_error: Optional[Exception] = None):
        super().__init__(
            message=f"Configuration error: {config_item}",
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            recovery_suggestions=[
                "Check your .env file for missing or invalid values",
                "Compare against .env.example for correct format",
                "Ensure all required environment variables are set",
                "Run ./Suntory.sh to validate configuration"
            ],
            original_error=original_error
        )


class AgentError(SuntoryError):
    """Agent execution failed"""

    def __init__(
        self,
        agent_name: str,
        task_description: str,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=f"Agent '{agent_name}' failed while: {task_description}",
            category=ErrorCategory.AGENT,
            severity=ErrorSeverity.MEDIUM,
            recovery_suggestions=[
                "Try rephrasing your request",
                "Break down the task into smaller steps",
                "Check if the task requires resources not available",
                "Use /team to engage multiple agents"
            ],
            original_error=original_error
        )


class ResourceError(SuntoryError):
    """Resource limit exceeded"""

    def __init__(self, resource_type: str, limit: str):
        super().__init__(
            message=f"{resource_type} limit exceeded ({limit})",
            category=ErrorCategory.RESOURCE,
            severity=ErrorSeverity.MEDIUM,
            recovery_suggestions=[
                "Simplify your request to use fewer resources",
                "Clear conversation history with /clear",
                "Check configuration for resource limits",
                "Contact support if limits are too restrictive"
            ]
        )


class ValidationError(SuntoryError):
    """Input validation failed"""

    def __init__(self, field: str, reason: str):
        super().__init__(
            message=f"Invalid {field}: {reason}",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            recovery_suggestions=[
                "Check the input format",
                "Refer to documentation for correct syntax",
                "Use /help to see command examples"
            ]
        )


def handle_exception(e: Exception) -> SuntoryError:
    """
    Convert generic exceptions to SuntoryError with helpful context.

    Args:
        e: Exception to handle

    Returns:
        SuntoryError with recovery suggestions
    """
    logger.error(f"Handling exception: {type(e).__name__}: {str(e)}")

    # Already a SuntoryError
    if isinstance(e, SuntoryError):
        return e

    # Map common exceptions to SuntoryErrors
    error_str = str(e).lower()

    # API Key errors
    if any(keyword in error_str for keyword in ["api key", "authentication", "unauthorized", "401"]):
        provider = "OpenAI"  # Default
        if "anthropic" in error_str:
            provider = "Anthropic"
        elif "google" in error_str or "gemini" in error_str:
            provider = "Google"
        return APIKeyError(provider, e)

    # Rate limit errors
    if any(keyword in error_str for keyword in ["rate limit", "quota", "429"]):
        provider = "the API"
        if "openai" in error_str:
            provider = "OpenAI"
        elif "anthropic" in error_str:
            provider = "Anthropic"
        elif "google" in error_str:
            provider = "Google"
        return RateLimitError(provider)

    # Network errors
    if any(keyword in error_str for keyword in ["connection", "timeout", "network", "503", "502"]):
        return NetworkError(e)

    # Model errors
    if any(keyword in error_str for keyword in ["model not found", "invalid model", "404"]):
        return ModelNotFoundError("unknown")

    # Generic error
    return SuntoryError(
        message=f"An unexpected error occurred: {str(e)}",
        category=ErrorCategory.UNKNOWN,
        severity=ErrorSeverity.MEDIUM,
        recovery_suggestions=[
            "Try your request again",
            "Rephrase your question differently",
            "Check the logs for more details",
            "Contact support if the issue persists"
        ],
        original_error=e
    )


def log_error(error: SuntoryError):
    """Log error with appropriate level"""
    log_data = {
        "category": error.category.value,
        "severity": error.severity.value,
        "message": error.message
    }

    if error.severity == ErrorSeverity.FATAL:
        logger.critical("Fatal error", **log_data)
    elif error.severity == ErrorSeverity.HIGH:
        logger.error("High severity error", **log_data)
    elif error.severity == ErrorSeverity.MEDIUM:
        logger.warning("Medium severity error", **log_data)
    else:
        logger.info("Low severity error", **log_data)

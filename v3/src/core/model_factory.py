"""
Suntory v3 - Model Client Factory
Bridge between LLMGateway and AutoGen's ModelClient architecture
"""

from typing import Optional

from autogen_ext.models.openai import AzureOpenAIChatCompletionClient, OpenAIChatCompletionClient
from autogen_core.models import ChatCompletionClient

from .config import get_settings
from .telemetry import get_logger

logger = get_logger(__name__)


class ModelClientFactory:
    """
    Factory for creating AutoGen-compatible ModelClient instances.

    This bridges the gap between our LLMGateway abstraction and AutoGen's
    requirement for ModelClient objects with model_info attributes.
    """

    # FIX: Add maximum cache size to prevent unbounded memory growth
    MAX_CACHE_SIZE = 10

    def __init__(self):
        self.settings = get_settings()
        # Use OrderedDict for LRU cache implementation
        from collections import OrderedDict
        self._client_cache = OrderedDict()

    def create_client(self, model: Optional[str] = None) -> ChatCompletionClient:
        """
        Create an AutoGen ModelClient for the specified model.

        Args:
            model: Model name (e.g., "gpt-4o", "azure/StellaSource-GPT4o")
                   If None, uses default from settings.

        Returns:
            AutoGen-compatible ChatCompletionClient
        """
        model_name = model or self.settings.default_model

        # Check cache first
        if model_name in self._client_cache:
            logger.debug(f"Using cached client for {model_name}")
            # Move to end for LRU tracking
            self._client_cache.move_to_end(model_name)
            return self._client_cache[model_name]

        # Create new client based on model name
        client = self._create_client_for_model(model_name)

        # FIX: Implement LRU eviction to prevent unbounded cache growth
        # Remove oldest entry if cache is full
        if len(self._client_cache) >= self.MAX_CACHE_SIZE:
            oldest_key = next(iter(self._client_cache))
            logger.debug(f"Cache full, evicting oldest client: {oldest_key}")
            self._client_cache.pop(oldest_key)

        # Cache it
        self._client_cache[model_name] = client

        logger.info(f"Created ModelClient for {model_name}", client_type=type(client).__name__)
        return client

    def _create_client_for_model(self, model_name: str) -> ChatCompletionClient:
        """Create the appropriate client based on model name"""

        # Azure OpenAI models
        if model_name.startswith("azure/") or model_name == self.settings.azure_openai_deployment_name:
            return self._create_azure_client(model_name)

        # OpenAI models
        if any(x in model_name.lower() for x in ["gpt-4", "gpt-3.5", "gpt-4o"]):
            return self._create_openai_client(model_name)

        # Anthropic models
        if "claude" in model_name.lower():
            # For Claude, we'll use OpenAI-compatible client via LiteLLM
            # AutoGen doesn't have native Anthropic support yet
            return self._create_openai_client(model_name)

        # Default to OpenAI client (works with most providers via LiteLLM)
        logger.warning(f"Unknown model type: {model_name}, defaulting to OpenAI client")
        return self._create_openai_client(model_name)

    def _create_azure_client(self, model_name: str) -> AzureOpenAIChatCompletionClient:
        """Create Azure OpenAI client"""
        from autogen_core.models import ModelInfo, ModelCapabilities

        # Strip 'azure/' prefix if present
        deployment_name = model_name.replace("azure/", "")

        if not self.settings.azure_openai_api_key:
            raise ValueError("Azure OpenAI API key not configured")

        if not self.settings.azure_openai_endpoint:
            raise ValueError("Azure OpenAI endpoint not configured")

        logger.info(
            "Creating Azure OpenAI client",
            deployment=deployment_name,
            endpoint=self.settings.azure_openai_endpoint
        )

        # Create ModelInfo to avoid "model_info is required" error
        # This is needed because Azure deployment names are not standard OpenAI model names
        model_info = ModelInfo(
            vision=True,  # GPT-4o supports vision
            function_calling=True,  # Supports function calling
            json_output=True,  # Supports JSON mode
            family="gpt-4o",  # Model family
            structured_output=True  # Supports structured output (required field)
        )

        return AzureOpenAIChatCompletionClient(
            model=deployment_name,
            api_version="2024-02-15-preview",
            azure_endpoint=self.settings.azure_openai_endpoint,
            api_key=self.settings.azure_openai_api_key,
            azure_deployment=deployment_name,
            model_info=model_info  # Explicitly provide model_info
        )

    def _create_openai_client(self, model_name: str) -> OpenAIChatCompletionClient:
        """Create OpenAI client"""

        if not self.settings.openai_api_key:
            raise ValueError("OpenAI API key not configured")

        logger.info("Creating OpenAI client", model=model_name)

        return OpenAIChatCompletionClient(
            model=model_name,
            api_key=self.settings.openai_api_key
        )

    def clear_cache(self):
        """Clear the client cache (useful for testing or config changes)"""
        self._client_cache.clear()
        logger.info("Model client cache cleared")


# Singleton instance with thread safety
import threading
_factory: Optional[ModelClientFactory] = None
_factory_lock = threading.Lock()


def get_model_client_factory() -> ModelClientFactory:
    """Get or create ModelClientFactory singleton (thread-safe)"""
    global _factory
    if _factory is not None:
        return _factory

    with _factory_lock:
        # Double-check locking pattern
        if _factory is None:
            _factory = ModelClientFactory()
    return _factory


def create_model_client(model: Optional[str] = None) -> ChatCompletionClient:
    """
    Convenience function to create a model client.

    Args:
        model: Model name or None for default

    Returns:
        AutoGen-compatible ChatCompletionClient
    """
    factory = get_model_client_factory()
    return factory.create_client(model)


def reset_model_factory():
    """Reset factory singleton (useful for testing)"""
    global _factory
    _factory = None

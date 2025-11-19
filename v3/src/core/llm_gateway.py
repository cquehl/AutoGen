"""
Suntory v3 - LLM Gateway
Unified interface to multiple LLM providers using LiteLLM
"""

import os
from typing import Any, Dict, List, Optional, Union

import litellm
from litellm import completion, acompletion
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import get_settings
from .telemetry import get_logger

logger = get_logger(__name__)


class LLMGateway:
    """
    Unified gateway to multiple LLM providers.

    Supports:
    - OpenAI (GPT-4, GPT-3.5)
    - Anthropic (Claude 3.5 Sonnet, Opus, Haiku)
    - Google (Gemini Pro, Ultra)
    - Azure OpenAI

    Features:
    - Automatic provider selection
    - Graceful fallback
    - Retry logic with exponential backoff
    - Token usage tracking
    """

    def __init__(self):
        self.settings = get_settings()
        self.current_model = self._normalize_model_name(self.settings.default_model)
        self._setup_providers()

        # Disable LiteLLM's verbose logging
        litellm.suppress_debug_info = True
        litellm.set_verbose = False

    def _normalize_model_name(self, model: str) -> str:
        """
        Normalize model name for LiteLLM.

        For Azure OpenAI deployments, ensure they have the 'azure/' prefix.
        This allows LiteLLM to correctly route to Azure OpenAI.

        Args:
            model: Model name or Azure deployment name

        Returns:
            Normalized model name with proper provider prefix
        """
        # Skip if already has a provider prefix
        if "/" in model:
            return model

        # If Azure is configured and model matches deployment name, add azure/ prefix
        if (self.settings.azure_openai_api_key and
            self.settings.azure_openai_deployment_name and
            model == self.settings.azure_openai_deployment_name):
            logger.info(f"Normalizing Azure deployment name: {model} -> azure/{model}")
            return f"azure/{model}"

        return model

    def _setup_providers(self):
        """Configure API keys for all providers"""
        if self.settings.openai_api_key:
            os.environ["OPENAI_API_KEY"] = self.settings.openai_api_key

        if self.settings.anthropic_api_key:
            os.environ["ANTHROPIC_API_KEY"] = self.settings.anthropic_api_key

        if self.settings.google_api_key:
            os.environ["GOOGLE_API_KEY"] = self.settings.google_api_key

        if self.settings.azure_openai_api_key:
            os.environ["AZURE_API_KEY"] = self.settings.azure_openai_api_key
            if self.settings.azure_openai_endpoint:
                os.environ["AZURE_API_BASE"] = self.settings.azure_openai_endpoint

        logger.info(
            "LLM Gateway initialized",
            available_providers=self.settings.get_available_providers(),
            default_model=self.current_model
        )

    def switch_model(self, model: str) -> str:
        """
        Switch to a different model.

        Args:
            model: Model name (e.g., "gpt-4", "claude-3-5-sonnet-20241022")

        Returns:
            Previous model name
        """
        previous_model = self.current_model
        self.current_model = self._normalize_model_name(model)
        logger.info(f"Switched model from {previous_model} to {self.current_model}")
        return previous_model

    def get_current_model(self) -> str:
        """Get currently active model"""
        return self.current_model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Any:
        """
        Synchronous completion with automatic retry.

        Args:
            messages: List of message dictionaries
            model: Override model (optional)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            tools: Function calling tools
            **kwargs: Additional arguments for LiteLLM

        Returns:
            LiteLLM completion response
        """
        model_to_use = self._normalize_model_name(model) if model else self.current_model

        try:
            logger.debug(
                "Requesting completion",
                model=model_to_use,
                message_count=len(messages),
                temperature=temperature
            )

            response = completion(
                model=model_to_use,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                **kwargs
            )

            # Log token usage
            if hasattr(response, 'usage'):
                logger.info(
                    "Completion successful",
                    model=model_to_use,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens
                )

            return response

        except Exception as e:
            logger.error(
                "Completion failed",
                model=model_to_use,
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def acomplete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Any:
        """
        Asynchronous completion with automatic retry.

        Args:
            messages: List of message dictionaries
            model: Override model (optional)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            tools: Function calling tools
            **kwargs: Additional arguments for LiteLLM

        Returns:
            LiteLLM completion response
        """
        model_to_use = self._normalize_model_name(model) if model else self.current_model

        try:
            logger.debug(
                "Requesting async completion",
                model=model_to_use,
                message_count=len(messages),
                temperature=temperature
            )

            response = await acompletion(
                model=model_to_use,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                **kwargs
            )

            # Log token usage
            if hasattr(response, 'usage'):
                logger.info(
                    "Async completion successful",
                    model=model_to_use,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens
                )

            return response

        except Exception as e:
            logger.error(
                "Async completion failed",
                model=model_to_use,
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    def get_fallback_models(self, primary_model: str) -> List[str]:
        """
        Get fallback models based on primary model.

        Args:
            primary_model: Primary model name

        Returns:
            List of fallback models
        """
        # Claude models
        if "claude" in primary_model.lower():
            return [
                "claude-3-5-sonnet-20241022",
                "gpt-4o",
                "gpt-4-turbo",
                "gemini-pro"
            ]

        # GPT models
        if "gpt-4" in primary_model.lower():
            return [
                "gpt-4o",
                "claude-3-5-sonnet-20241022",
                "gpt-4-turbo",
                "gemini-pro"
            ]

        # Gemini models
        if "gemini" in primary_model.lower():
            return [
                "gemini-pro",
                "claude-3-5-sonnet-20241022",
                "gpt-4o"
            ]

        # Default fallback chain
        return [
            "claude-3-5-sonnet-20241022",
            "gpt-4o",
            "gpt-4-turbo",
            "gemini-pro"
        ]

    def complete_with_fallback(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Complete with automatic fallback to alternative models.

        Args:
            messages: List of message dictionaries
            model: Primary model to try
            **kwargs: Additional arguments

        Returns:
            LiteLLM completion response
        """
        primary_model = model or self.current_model
        fallback_models = self.get_fallback_models(primary_model)

        # Try primary model first
        models_to_try = [primary_model] + [
            m for m in fallback_models if m != primary_model
        ]

        last_error = None
        for attempt_model in models_to_try:
            try:
                logger.info(f"Trying model: {attempt_model}")
                return self.complete(messages, model=attempt_model, **kwargs)
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Model {attempt_model} failed, trying next",
                    error=str(e)
                )
                continue

        # All models failed
        logger.error("All models failed", last_error=str(last_error))
        raise last_error


# Singleton instance
_gateway: Optional[LLMGateway] = None


def get_llm_gateway() -> LLMGateway:
    """Get or create LLM gateway singleton"""
    global _gateway
    if _gateway is None:
        _gateway = LLMGateway()
    return _gateway


def reset_llm_gateway() -> None:
    """Reset gateway (useful for testing)"""
    global _gateway
    _gateway = None

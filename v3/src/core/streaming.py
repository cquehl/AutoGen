"""
Suntory v3 - Response Streaming
Token-by-token streaming for real-time feedback
"""

from typing import AsyncIterator, Optional

from .llm_gateway import get_llm_gateway
from .telemetry import get_logger

logger = get_logger(__name__)


class StreamingResponse:
    """
    Wrapper for streaming LLM responses.

    Provides token-by-token streaming for better UX.
    """

    def __init__(self, response_iterator: AsyncIterator[str]):
        self.iterator = response_iterator
        self.full_response = ""

    async def __aiter__(self):
        """Async iterator for tokens"""
        async for token in self.iterator:
            self.full_response += token
            yield token

    def get_full_response(self) -> str:
        """Get accumulated response"""
        return self.full_response


async def stream_completion(
    messages: list[dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
) -> AsyncIterator[str]:
    """
    Stream completion tokens from LLM.

    Args:
        messages: Conversation messages
        model: Model to use (optional)
        temperature: Sampling temperature
        max_tokens: Max tokens to generate

    Yields:
        Individual tokens from the response
    """
    gateway = get_llm_gateway()
    model_to_use = model or gateway.get_current_model()

    logger.debug(
        "Starting streaming completion",
        model=model_to_use,
        message_count=len(messages)
    )

    try:
        # Import here to avoid circular dependency
        from litellm import acompletion

        response = await acompletion(
            model=model_to_use,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True  # Enable streaming
        )

        # Stream tokens with robust validation
        async for chunk in response:
            try:
                # Validate chunk structure
                if not hasattr(chunk, 'choices'):
                    logger.warning(f"Unexpected chunk structure: {type(chunk)}")
                    continue

                if not chunk.choices or len(chunk.choices) == 0:
                    continue

                delta = chunk.choices[0].delta

                # Validate delta has content
                if hasattr(delta, 'content') and delta.content is not None:
                    yield delta.content

            except (AttributeError, IndexError, TypeError) as chunk_error:
                logger.warning(
                    f"Malformed streaming chunk: {chunk_error}",
                    chunk_type=type(chunk).__name__
                )
                continue

    except Exception as e:
        logger.error(f"Streaming failed: {e}", exc_info=True)
        # Raise proper error instead of yielding error message
        from .errors import handle_exception
        raise handle_exception(e)


async def stream_with_thinking(
    messages: list[dict[str, str]],
    thinking_message: str = "thinking...",
    **kwargs
) -> AsyncIterator[str]:
    """
    Stream response with thinking indicator.

    Args:
        messages: Conversation messages
        thinking_message: Message to show while thinking
        **kwargs: Additional arguments for streaming

    Yields:
        Tokens from response
    """
    # First yield thinking indicator (will be cleared)
    yield f"\n💭 {thinking_message}\n\n"

    # Then stream actual response
    async for token in stream_completion(messages, **kwargs):
        yield token

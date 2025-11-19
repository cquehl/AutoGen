"""
Vision Service - Abstraction for vision model operations

Provides a clean interface for image analysis, decoupling tools
from direct model client dependencies.
"""

import base64
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

from ..config.models import MultimodalConfig, AppSettings


@dataclass
class VisionResult:
    """Result of vision analysis"""
    success: bool
    analysis: str = ""
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class VisionService:
    """
    Service for vision model operations.

    Provides image analysis capabilities using configured vision models.
    Abstracts away the model client details from tools.
    """

    def __init__(self, config: MultimodalConfig, llm_settings: AppSettings, security_middleware=None):
        """
        Initialize vision service.

        Args:
            config: Multimodal configuration
            llm_settings: Application settings for LLM client
            security_middleware: Security middleware for path validation (optional but recommended)
        """
        self.config = config
        self.llm_settings = llm_settings
        self.security = security_middleware
        self._model_client = None

    def _get_model_client(self):
        """Get or create vision model client (lazy initialization)"""
        if self._model_client is None:
            try:
                # Get model client based on vision_provider
                if self.config.vision_provider == "claude":
                    # Use Azure/OpenAI client with vision model
                    self._model_client = self.llm_settings.get_model_client()
                elif self.config.vision_provider == "gpt4v":
                    from ..config.models import ModelProvider
                    self._model_client = self.llm_settings.get_model_client(
                        provider=ModelProvider.OPENAI
                    )
                elif self.config.vision_provider == "gemini":
                    from ..config.models import ModelProvider
                    self._model_client = self.llm_settings.get_model_client(
                        provider=ModelProvider.GOOGLE
                    )
                else:
                    raise ValueError(f"Unknown vision provider: {self.config.vision_provider}")
            except Exception as e:
                raise RuntimeError(f"Failed to initialize vision model client: {str(e)}") from e

        return self._model_client

    async def analyze_image(
        self,
        image_path: str,
        prompt: str,
        max_tokens: Optional[int] = None,
    ) -> VisionResult:
        """
        Analyze an image using vision model.

        Args:
            image_path: Path to image file
            prompt: Question/instruction about the image
            max_tokens: Maximum tokens in response (default from config)

        Returns:
            VisionResult with analysis
        """
        try:
            # Security validation: Check path is within allowed directories
            if self.security is not None:
                validator = self.security.get_path_validator()
                is_valid, error, validated_path = validator.validate(image_path, operation="read")
                if not is_valid:
                    return VisionResult(
                        success=False,
                        error=f"Security validation failed: {error}"
                    )
                # Use validated path
                image_path = str(validated_path)

            # Validate image path
            image_file = Path(image_path)
            if not image_file.exists():
                return VisionResult(
                    success=False,
                    error=f"Image file not found: {image_path}"
                )

            # Check file type
            if image_file.suffix.lower() not in self.config.supported_image_formats:
                return VisionResult(
                    success=False,
                    error=f"Invalid image format. Supported: {', '.join(self.config.supported_image_formats)}"
                )

            # Check file size
            file_size_mb = image_file.stat().st_size / (1024 * 1024)
            if file_size_mb > self.config.max_image_size_mb:
                return VisionResult(
                    success=False,
                    error=f"Image too large ({file_size_mb:.1f}MB). Max: {self.config.max_image_size_mb}MB"
                )

            # Read and encode image
            with open(image_path, 'rb') as f:
                image_data = base64.standard_b64encode(f.read()).decode('utf-8')

            # Determine media type
            media_type = f"image/{image_file.suffix.lstrip('.').lower()}"
            if media_type == "image/jpg":
                media_type = "image/jpeg"

            # Create message with image
            from autogen_core.models import UserMessage

            message = UserMessage(
                content=[
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
                source="user",
            )

            # Call vision model
            max_tokens = max_tokens or self.config.default_vision_max_tokens
            model_client = self._get_model_client()
            response = await model_client.create([message], max_tokens=max_tokens)

            # Extract response
            analysis = response.content

            return VisionResult(
                success=True,
                analysis=analysis,
                metadata={
                    "image_path": image_path,
                    "prompt": prompt,
                    "model": self.config.vision_model,
                    "provider": self.config.vision_provider,
                    "tokens_used": max_tokens,
                }
            )

        except Exception as e:
            return VisionResult(
                success=False,
                error=f"Image analysis failed: {str(e)}"
            )

    def validate_image(self, image_path: str) -> tuple[bool, Optional[str]]:
        """
        Validate an image file.

        Args:
            image_path: Path to image file

        Returns:
            Tuple of (is_valid, error_message)
        """
        image_file = Path(image_path)

        if not image_file.exists():
            return False, f"Image file not found: {image_path}"

        if image_file.suffix.lower() not in self.config.supported_image_formats:
            return False, f"Invalid image format. Supported: {', '.join(self.config.supported_image_formats)}"

        file_size_mb = image_file.stat().st_size / (1024 * 1024)
        if file_size_mb > self.config.max_image_size_mb:
            return False, f"Image too large ({file_size_mb:.1f}MB). Max: {self.config.max_image_size_mb}MB"

        return True, None

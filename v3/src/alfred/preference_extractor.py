"""
Suntory v3 - LLM-Based Preference Extractor
Robust preference extraction using structured LLM function calling
"""

import json
from typing import Dict, Optional

from ..core import get_llm_gateway, get_logger
from .input_sanitization import sanitize_prompt_input, sanitize_preference_value
from .preference_schema import (
    UserPreferenceExtraction,
    EXTRACTION_SYSTEM_PROMPT,
    create_extraction_prompt
)

logger = get_logger(__name__)


class LLMPreferenceExtractor:
    """
    LLM-based preference extractor using structured output.

    Replaces fragile regex patterns with robust LLM function calling.
    """

    def __init__(self):
        self.llm_gateway = get_llm_gateway()

    def _supports_json_mode(self, model: str) -> bool:
        """
        Check if model supports response_format JSON mode.

        Only certain OpenAI models support the response_format parameter.
        Other providers (Anthropic, Google) do not support this feature.

        Args:
            model: Model name to check

        Returns:
            True if model supports JSON mode, False otherwise
        """
        model_lower = model.lower()

        # Models that support response_format
        json_mode_models = [
            "gpt-4-turbo",
            "gpt-4-1106",
            "gpt-4-0125",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-3.5-turbo-1106",
            "gpt-3.5-turbo-0125",
        ]

        return any(supported in model_lower for supported in json_mode_models)

    async def extract_preferences(
        self,
        user_message: str,
        use_llm: bool = True
    ) -> UserPreferenceExtraction:
        """
        Extract user preferences from message using LLM structured extraction.

        Args:
            user_message: User's message to analyze
            use_llm: If True, use LLM extraction. If False, fall back to regex (for testing)

        Returns:
            UserPreferenceExtraction with any found preferences
        """
        if not user_message or not user_message.strip():
            return UserPreferenceExtraction()

        if not use_llm:
            # Fallback to legacy regex extraction (for comparison/testing)
            return await self._fallback_regex_extraction(user_message)

        try:
            # SECURITY: Sanitize user input before sending to LLM
            sanitized_message = sanitize_prompt_input(user_message, max_length=500)

            # Check if current model supports JSON mode
            current_model = self.llm_gateway.get_current_model()
            supports_json = self._supports_json_mode(current_model)

            # Build messages with sanitized input
            messages = [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": create_extraction_prompt(sanitized_message)}
            ]

            # For models without native JSON mode, add explicit instruction
            if not supports_json:
                messages[0]["content"] += (
                    "\n\nIMPORTANT: You must respond with ONLY valid JSON. "
                    "Do not include markdown code blocks, explanations, or any text outside the JSON object."
                )

            # Prepare request parameters
            request_params = {
                "messages": messages,
                "temperature": 0.1,  # Low temperature for consistent extraction
                "max_tokens": 200,
            }

            # Only add response_format for models that support it
            if supports_json:
                request_params["response_format"] = {"type": "json_object"}
                logger.debug(f"Using JSON mode for model: {current_model}")
            else:
                logger.debug(f"Model {current_model} does not support JSON mode, using prompt instruction")

            # Call LLM with appropriate parameters
            response = await self.llm_gateway.acomplete(**request_params)

            # Parse the JSON response
            response_text = response.choices[0].message.content

            try:
                # Clean up response text - remove markdown code blocks if present
                cleaned_text = response_text.strip()
                if cleaned_text.startswith("```json"):
                    cleaned_text = cleaned_text[7:]  # Remove ```json
                if cleaned_text.startswith("```"):
                    cleaned_text = cleaned_text[3:]  # Remove ```
                if cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[:-3]  # Remove trailing ```
                cleaned_text = cleaned_text.strip()

                # Parse JSON
                extracted_data = json.loads(cleaned_text)

                # SECURITY: Sanitize extracted values before validation
                if "name" in extracted_data and extracted_data["name"]:
                    from .input_sanitization import sanitize_name
                    extracted_data["name"] = sanitize_name(extracted_data["name"])

                if "title" in extracted_data and extracted_data["title"]:
                    extracted_data["title"] = sanitize_preference_value(
                        extracted_data["title"], max_length=50
                    )

                if "timezone" in extracted_data and extracted_data["timezone"]:
                    from .input_sanitization import sanitize_timezone
                    extracted_data["timezone"] = sanitize_timezone(extracted_data["timezone"])

                # Validate and create Pydantic model
                preferences = UserPreferenceExtraction(**extracted_data)

                if preferences.has_any_preference():
                    logger.info(
                        "LLM extracted preferences",
                        message=user_message[:100],
                        preferences=preferences.to_dict()
                    )

                return preferences

            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse LLM response as JSON: {e}")
                logger.debug(f"Response text: {response_text}")
                # Fall back to regex
                return await self._fallback_regex_extraction(user_message)

            except Exception as e:
                logger.warning(f"Failed to validate extracted preferences: {e}")
                # Fall back to regex
                return await self._fallback_regex_extraction(user_message)

        except Exception as e:
            logger.warning(f"LLM extraction failed, using fallback: {e}")
            return await self._fallback_regex_extraction(user_message)

    async def _fallback_regex_extraction(self, user_message: str) -> UserPreferenceExtraction:
        """
        Fallback to regex-based extraction.

        This is kept for backwards compatibility and as a fallback when LLM is unavailable.
        Uses pure regex patterns without any dependencies.
        """
        # Use pure regex pattern extraction (no circular imports)
        from .preference_patterns import (
            extract_gender_preference,
            extract_name,
            extract_title_from_name
        )

        gender = extract_gender_preference(user_message)
        name = extract_name(user_message, max_length=100)
        title = extract_title_from_name(name) if name else None

        return UserPreferenceExtraction(
            gender=gender,
            name=name,
            title=title
        )


# Singleton instance
_extractor: Optional[LLMPreferenceExtractor] = None


def get_preference_extractor() -> LLMPreferenceExtractor:
    """Get or create singleton preference extractor"""
    global _extractor
    if _extractor is None:
        _extractor = LLMPreferenceExtractor()
    return _extractor

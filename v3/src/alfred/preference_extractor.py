"""
Suntory v3 - LLM-Based Preference Extractor
Robust preference extraction using structured LLM function calling
"""

import json
from typing import Dict, Optional

from ..core import get_llm_gateway, get_logger
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
            # Use LLM with structured output (function calling)
            messages = [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": create_extraction_prompt(user_message)}
            ]

            # Call LLM with response_format for structured output
            # Note: This uses the JSON schema mode available in modern LLMs
            response = await self.llm_gateway.acomplete(
                messages=messages,
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=200,
                response_format={"type": "json_object"}  # Request JSON output
            )

            # Parse the JSON response
            response_text = response.choices[0].message.content
            try:
                extracted_data = json.loads(response_text)
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
        Fallback to legacy regex-based extraction.

        This is kept for backwards compatibility and as a fallback when LLM is unavailable.
        """
        # Import the regex methods from the old implementation
        from .user_preferences import UserPreferencesManager

        # Create a temporary instance just for extraction
        temp_manager = UserPreferencesManager("temp_extraction_session")

        gender = temp_manager.extract_gender_preference(user_message)
        name = temp_manager.extract_name(user_message)

        # Infer title from name if present
        title = None
        if name:
            for title_prefix in ["Master", "Mr.", "Mr", "Dr.", "Dr", "Professor", "Prof.", "Miss", "Ms.", "Mrs."]:
                if name.startswith(title_prefix):
                    title = title_prefix.rstrip('.')
                    break

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

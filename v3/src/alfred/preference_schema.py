"""
Suntory v3 - User Preference Schema
Pydantic models for structured LLM extraction of user preferences
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


class UserPreferenceExtraction(BaseModel):
    """
    Structured extraction of user preferences from conversational text.

    Uses LLM function calling to extract preferences robustly without fragile regex.
    """

    gender: Optional[Literal["male", "female", "non-binary"]] = Field(
        default=None,
        description="User's gender preference for how they should be addressed (sir/madam/etc.)"
    )

    name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="User's name or preferred form of address (e.g., 'Charles', 'Master Charles', 'Dr. Smith')"
    )

    formality: Optional[Literal["casual", "formal", "very_formal"]] = Field(
        default=None,
        description="Preferred formality level in Alfred's responses"
    )

    title: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Preferred title (Mr., Dr., Professor, Master, etc.)"
    )

    timezone: Optional[str] = Field(
        default=None,
        description="User's timezone for time-aware greetings (e.g., 'America/New_York', 'UTC')"
    )

    communication_style: Optional[Literal["concise", "detailed", "balanced"]] = Field(
        default=None,
        description="Preferred communication style - how verbose Alfred should be"
    )

    def has_any_preference(self) -> bool:
        """Check if any preference was extracted"""
        return any([
            self.gender is not None,
            self.name is not None,
            self.formality is not None,
            self.title is not None,
            self.timezone is not None,
            self.communication_style is not None
        ])

    def to_dict(self) -> dict:
        """Convert to dict, excluding None values"""
        return {
            k: v for k, v in self.model_dump().items()
            if v is not None
        }


# System prompt for LLM extraction
EXTRACTION_SYSTEM_PROMPT = """You are a preference extraction assistant.

Your task is to analyze user messages and extract any stated preferences about:
1. Gender/addressing (sir/madam/etc.)
2. Name or preferred form of address
3. Formality level (casual vs formal)
4. Title (Mr., Dr., Professor, etc.)
5. Timezone
6. Communication style (concise vs detailed)

IMPORTANT: The user will prefix their preference statements with the command word "memorize".
You should IGNORE this command word and extract ONLY the actual preference content.

Only extract preferences that are EXPLICITLY stated. Do not infer or guess.

Examples:
- "Memorize: I am a sir" → {"gender": "male"}
- "memorize that I'm a sir" → {"gender": "male"}
- "Please memorize: Call me Master Charles" → {"name": "Master Charles", "gender": "male"}
- "Memorize my name is Dr. Smith" → {"name": "Dr. Smith", "title": "Dr."}
- "memorize: Keep it concise" → {"communication_style": "concise"}
- "Memorize I prefer formal communication" → {"formality": "formal"}

If no preferences are mentioned, return an empty object with all fields as null.
"""


def create_extraction_prompt(user_message: str) -> str:
    """
    Create the extraction prompt for the LLM.

    Args:
        user_message: The user's message to analyze

    Returns:
        Formatted prompt for extraction
    """
    return f"""Analyze this message and extract any user preferences:

Message: "{user_message}"

Remember to ignore the "memorize" command word itself - extract only the actual preference content.
Only extract what is explicitly stated. Return null for fields where nothing is mentioned."""

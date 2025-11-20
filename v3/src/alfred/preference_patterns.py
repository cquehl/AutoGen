"""
Suntory v3 - User Preference Pattern Extraction
Pure regex-based pattern matching without dependencies
Used as fallback when LLM extraction is unavailable
"""

import re
from typing import Optional

from .input_sanitization import sanitize_name, sanitize_preference_value


# =================================================================
# Pattern Constants
# =================================================================

MALE_GENDER_PHRASES = [
    "i am a sir", "i'm a sir", "call me sir",
    "i am male", "i'm male",
    "i am not a madam", "not madam"
]

FEMALE_GENDER_PHRASES = [
    "i am a madam", "i'm a madam", "call me madam",
    "i am female", "i'm female",
    "i am not a sir", "not sir"
]

NAME_PATTERNS = [
    # Multi-word with titles: "Master Charles", "Dr. Smith", "Mr. John Doe"
    r"(?:my name is|call me|i'?m) ((?:Master|Mister|Mr\.?|Miss|Ms\.?|Mrs\.?|Dr\.?|Professor|Prof\.?) [A-Z][a-z]+(?: [A-Z][a-z]+)*)",
    # Multi-word names: "John Smith", "Mary Jane Watson"
    r"my name is ([A-Z][a-z]+(?: [A-Z][a-z]+)+)",
    # Single word with capital (proper names): "Charles", "Alice"
    r"(?:my name is|call me) ([A-Z][a-z]+)",
    # Lowercase patterns (will capitalize): "my name is john"
    r"my name is ([a-z]+)",
    r"call me ([a-z]+)",
]

NAME_BLACKLIST = ["a", "not", "the", "sir", "madam", "male", "female", "tired", "busy"]

TITLE_PREFIXES = [
    "Master", "Mister", "Mr.", "Mr",
    "Miss", "Ms.", "Ms", "Mrs.", "Mrs",
    "Dr.", "Dr", "Doctor",
    "Professor", "Prof.", "Prof"
]


def extract_gender_preference(user_message: str) -> Optional[str]:
    """Extract gender preference from user message using regex patterns"""
    message_lower = user_message.lower()
    if any(phrase in message_lower for phrase in MALE_GENDER_PHRASES):
        return "male"
    if any(phrase in message_lower for phrase in FEMALE_GENDER_PHRASES):
        return "female"
    return None


def extract_name(user_message: str, max_length: int = 100) -> Optional[str]:
    """Extract name from user message (supports multi-word names with titles)"""
    for pattern in NAME_PATTERNS:
        match = re.search(pattern, user_message, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            if name.lower() in NAME_BLACKLIST or len(name) > max_length:
                continue
            if name.islower():
                name = name.capitalize()
            sanitized_name = sanitize_name(name)
            if sanitized_name:
                return sanitized_name
    return None


def extract_title_from_name(name: str) -> Optional[str]:
    """Extract title prefix from a name"""
    if not name:
        return None
    for title_prefix in TITLE_PREFIXES:
        if name.startswith(title_prefix):
            return title_prefix.rstrip('.')
    return None


def might_contain_preferences(user_message: str) -> bool:
    """Check if message contains 'memorize' keyword for preference extraction"""
    return "memorize" in user_message.lower()

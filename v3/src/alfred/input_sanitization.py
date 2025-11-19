"""
Suntory v3 - Input Sanitization
Comprehensive security measures for user input validation and sanitization
"""

import html
import re
import unicodedata
from typing import Optional


def sanitize_preference_value(
    value: str,
    max_length: int = 100,
    allow_unicode: bool = True
) -> Optional[str]:
    """
    Sanitize user preference input to prevent security vulnerabilities.

    Protections:
    - HTML/XML injection (XSS)
    - ANSI escape code injection (terminal manipulation)
    - Control character injection
    - Unicode homograph attacks (optional normalization)
    - Length validation

    Args:
        value: Raw user input string
        max_length: Maximum allowed length
        allow_unicode: If True, allows Unicode characters (normalized)

    Returns:
        Sanitized string or None if invalid
    """
    if not value or not isinstance(value, str):
        return None

    # Strip leading/trailing whitespace
    value = value.strip()

    if not value:
        return None

    # Remove ANSI escape codes (terminal color/formatting codes)
    # Pattern matches: \x1B[@-Z\\-_] or \x1B\[[0-?]*[ -/]*[@-~]
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    value = ansi_escape.sub('', value)

    # Remove other control characters (except newline, tab, carriage return)
    # Unicode category 'C' = control characters
    value = ''.join(
        ch for ch in value
        if unicodedata.category(ch)[0] != 'C' or ch in ['\n', '\t', '\r']
    )

    # Normalize Unicode to prevent homograph attacks
    # NFKC normalization converts visually similar characters to canonical form
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)

    # HTML escape to prevent XSS if preferences are ever rendered in web UI
    # Converts: < > & " ' to &lt; &gt; &amp; &quot; &#x27;
    value = html.escape(value, quote=True)

    # Strip again after processing
    value = value.strip()

    # Length validation
    if len(value) > max_length:
        return None

    # Final check: ensure we have something left
    if not value:
        return None

    return value


def sanitize_prompt_input(user_input: str, max_length: int = 500) -> str:
    """
    Sanitize user input before embedding in LLM prompts.

    Protections:
    - Prompt injection attacks
    - Excessive length (DoS)
    - Control characters

    Args:
        user_input: Raw user input
        max_length: Maximum length for prompt inclusion

    Returns:
        Sanitized string safe for prompt inclusion
    """
    if not user_input or not isinstance(user_input, str):
        return ""

    # Truncate to max length
    sanitized = user_input[:max_length]

    # Remove control characters
    sanitized = ''.join(
        ch for ch in sanitized
        if unicodedata.category(ch)[0] != 'C' or ch in ['\n', '\t', ' ']
    )

    # Escape special characters that might affect prompt structure
    # Replace quotes with escaped versions
    sanitized = sanitized.replace('"', '\\"')
    sanitized = sanitized.replace("'", "\\'")

    # Normalize newlines and excessive whitespace
    sanitized = re.sub(r'\n+', ' ', sanitized)  # Replace newlines with spaces
    sanitized = re.sub(r'\s+', ' ', sanitized)  # Collapse multiple spaces

    return sanitized.strip()


def validate_preference_key(key: str) -> bool:
    """
    Validate that a preference key is safe and allowed.

    Args:
        key: Preference key to validate

    Returns:
        True if key is valid, False otherwise
    """
    if not key or not isinstance(key, str):
        return False

    # Define allowed keys
    allowed_keys = [
        "gender",
        "name",
        "formality",
        "title",
        "timezone",
        "communication_style"
    ]

    return key in allowed_keys


def sanitize_name(name: str) -> Optional[str]:
    """
    Specialized sanitization for name fields.

    More restrictive than general preference values to prevent
    common name-based attacks.

    Args:
        name: Raw name input

    Returns:
        Sanitized name or None if invalid
    """
    if not name:
        return None

    # First apply general sanitization
    sanitized = sanitize_preference_value(name, max_length=100)

    if not sanitized:
        return None

    # Additional name-specific validation
    # Names should not contain HTML entities after escaping
    # If they do, it indicates attempted injection
    if '&' in sanitized and any(entity in sanitized for entity in ['&lt;', '&gt;', '&amp;', '&quot;']):
        # Detected attempted HTML injection
        return None

    # Names should be primarily alphanumeric with allowed special chars
    # Allow: letters, spaces, hyphens, apostrophes, periods (for titles like "Dr.")
    allowed_pattern = re.compile(r"^[a-zA-Z0-9\s\-'.]+$")
    if not allowed_pattern.match(sanitized.replace('&', '')):  # Check without HTML entities
        return None

    return sanitized


def sanitize_timezone(timezone: str) -> Optional[str]:
    """
    Specialized sanitization for timezone fields.

    Args:
        timezone: Raw timezone input

    Returns:
        Sanitized timezone or None if invalid
    """
    if not timezone:
        return None

    # General sanitization
    sanitized = sanitize_preference_value(timezone, max_length=50)

    if not sanitized:
        return None

    # Timezone should match common formats:
    # - IANA format: America/New_York, Europe/London, UTC
    # - Offset format: UTC+5, GMT-8
    timezone_pattern = re.compile(r'^[A-Za-z]+(?:[/_][A-Za-z]+)*(?:[+-]\d{1,2})?$')

    if not timezone_pattern.match(sanitized):
        return None

    return sanitized


# Blacklist for common attack strings
ATTACK_PATTERNS = [
    # JavaScript
    r'<script',
    r'javascript:',
    r'onerror=',
    r'onload=',

    # SQL injection
    r';\s*drop\s+table',
    r';\s*delete\s+from',
    r'union\s+select',

    # Command injection
    r';\s*rm\s+-rf',
    r'&&\s*rm',
    r'\|\s*sh',

    # Path traversal
    r'\.\./\.\./',
    r'\.\.\\\.\.\\',
]


def contains_attack_pattern(text: str) -> bool:
    """
    Check if text contains known attack patterns.

    Args:
        text: Text to check

    Returns:
        True if attack pattern detected, False otherwise
    """
    if not text:
        return False

    text_lower = text.lower()

    for pattern in ATTACK_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True

    return False


def get_sanitization_report(original: str, sanitized: Optional[str]) -> dict:
    """
    Generate a report showing what was changed during sanitization.

    Useful for logging and debugging.

    Args:
        original: Original input
        sanitized: Sanitized output

    Returns:
        Dictionary with sanitization statistics
    """
    if sanitized is None:
        return {
            "sanitized": False,
            "reason": "Rejected as invalid",
            "original_length": len(original) if original else 0,
            "sanitized_length": 0,
            "changes": "Input rejected"
        }

    changes = []

    if len(original) != len(sanitized):
        changes.append(f"Length changed: {len(original)} → {len(sanitized)}")

    if original != sanitized:
        changes.append("Content modified")

    if contains_attack_pattern(original):
        changes.append("⚠️ Attack pattern detected in original")

    return {
        "sanitized": True,
        "original_length": len(original),
        "sanitized_length": len(sanitized),
        "changes": "; ".join(changes) if changes else "No changes needed"
    }

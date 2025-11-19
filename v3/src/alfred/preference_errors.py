"""
Suntory v3 - Preference System Error Classes
Custom exceptions for user preference handling
"""


class PreferenceError(Exception):
    """Base exception for preference-related errors"""
    pass


class PreferenceStorageError(PreferenceError):
    """Raised when preference storage operations fail"""

    def __init__(self, message: str, retriable: bool = True):
        """
        Args:
            message: Error description
            retriable: Whether the operation can be retried
        """
        super().__init__(message)
        self.retriable = retriable

    def format_for_user(self) -> str:
        """Format error message for user display"""
        if self.retriable:
            return (
                f"⚠️ Warning: {self.args[0]}\n\n"
                "Your preferences will be remembered for this session, "
                "but may be lost when Alfred restarts."
            )
        else:
            return (
                f"❌ Error: {self.args[0]}\n\n"
                "Unable to save preferences. Please contact support."
            )


class PreferenceValidationError(PreferenceError):
    """Raised when preference validation fails"""

    def __init__(self, field: str, value: str, reason: str):
        """
        Args:
            field: Preference field that failed validation
            value: Invalid value
            reason: Why validation failed
        """
        super().__init__(f"Invalid {field}: {reason}")
        self.field = field
        self.value = value
        self.reason = reason

    def format_for_user(self) -> str:
        """Format error message for user display"""
        return (
            f"⚠️ Invalid preference: **{self.field}**\n\n"
            f"Reason: {self.reason}\n\n"
            f"Please provide a valid {self.field}."
        )


class PreferenceExtractionError(PreferenceError):
    """Raised when preference extraction fails"""

    def __init__(self, message: str, fallback_used: bool = False):
        """
        Args:
            message: Error description
            fallback_used: Whether fallback extraction was used
        """
        super().__init__(message)
        self.fallback_used = fallback_used

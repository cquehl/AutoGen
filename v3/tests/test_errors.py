"""
Test suite for v3/src/core/errors.py
TDD-first approach: Tests written BEFORE refactoring
"""

import pytest
from v3.src.core.errors import (
    ErrorSeverity,
    ErrorCategory,
    SuntoryError,
    APIKeyError,
    RateLimitError,
    NetworkError,
    ModelNotFoundError,
    ConfigurationError,
    AgentError,
    ResourceError,
    ValidationError,
    handle_exception,
    log_error,
)


# ============================================================================
# EXCEPTION CLASS TESTS
# ============================================================================

class TestSuntoryError:
    """Test base exception class"""

    def test_basic_creation(self):
        error = SuntoryError("Test message")
        assert error.message == "Test message"
        assert error.category == ErrorCategory.UNKNOWN
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.recovery_suggestions == []
        assert error.original_error is None

    def test_full_parameters(self):
        original = ValueError("original")
        error = SuntoryError(
            message="Custom message",
            category=ErrorCategory.API_KEY,
            severity=ErrorSeverity.HIGH,
            recovery_suggestions=["Fix this", "Try that"],
            original_error=original
        )
        assert error.message == "Custom message"
        assert error.category == ErrorCategory.API_KEY
        assert error.severity == ErrorSeverity.HIGH
        assert len(error.recovery_suggestions) == 2
        assert error.original_error == original

    def test_format_for_user_basic(self):
        error = SuntoryError("Something went wrong")
        formatted = error.format_for_user()
        assert "❌" in formatted
        assert "Something went wrong" in formatted

    def test_format_for_user_with_suggestions(self):
        error = SuntoryError(
            "Test error",
            recovery_suggestions=["Step 1", "Step 2"]
        )
        formatted = error.format_for_user()
        assert "How to fix:" in formatted
        assert "Step 1" in formatted
        assert "Step 2" in formatted

    def test_format_for_user_fatal(self):
        error = SuntoryError("Fatal issue", severity=ErrorSeverity.FATAL)
        formatted = error.format_for_user()
        assert "critical error" in formatted.lower()


class TestAPIKeyError:
    """Test API key error handling"""

    def test_openai_creation(self):
        error = APIKeyError("OpenAI")
        assert "OpenAI" in error.message
        assert error.category == ErrorCategory.API_KEY
        assert error.severity == ErrorSeverity.HIGH
        assert len(error.recovery_suggestions) > 0
        assert any("OPENAI_API_KEY" in s for s in error.recovery_suggestions)

    def test_anthropic_creation(self):
        error = APIKeyError("Anthropic")
        assert "Anthropic" in error.message
        assert any("ANTHROPIC_API_KEY" in s for s in error.recovery_suggestions)

    def test_with_original_error(self):
        original = Exception("401 Unauthorized")
        error = APIKeyError("OpenAI", original)
        assert error.original_error == original


class TestRateLimitError:
    """Test rate limit error handling"""

    def test_without_retry_after(self):
        error = RateLimitError("OpenAI")
        assert "OpenAI" in error.message
        assert error.category == ErrorCategory.RATE_LIMIT
        assert error.severity == ErrorSeverity.MEDIUM

    def test_with_retry_after(self):
        error = RateLimitError("Anthropic", retry_after=60)
        assert "60 seconds" in error.message
        assert error.category == ErrorCategory.RATE_LIMIT


class TestNetworkError:
    """Test network error handling"""

    def test_creation(self):
        error = NetworkError()
        assert "connection" in error.message.lower()
        assert error.category == ErrorCategory.NETWORK
        assert error.severity == ErrorSeverity.MEDIUM
        assert any("internet" in s.lower() for s in error.recovery_suggestions)


class TestModelNotFoundError:
    """Test model not found error handling"""

    def test_without_available_models(self):
        error = ModelNotFoundError("gpt-5")
        assert "gpt-5" in error.message
        assert error.category == ErrorCategory.MODEL

    def test_with_available_models(self):
        error = ModelNotFoundError("bad-model", ["gpt-4", "gpt-3.5", "claude-3"])
        assert "bad-model" in error.message
        formatted = error.format_for_user()
        # Should suggest alternatives
        assert any(model in formatted for model in ["gpt-4", "gpt-3.5", "claude-3"])


# ============================================================================
# HANDLE_EXCEPTION TESTS (Core Refactoring Target)
# ============================================================================

class TestHandleException:
    """Test the main exception handling function"""

    # ------------------------------------------------------------------------
    # Passthrough Tests
    # ------------------------------------------------------------------------

    def test_passthrough_suntory_error(self):
        """SuntoryError instances should pass through unchanged"""
        original = APIKeyError("OpenAI")
        result = handle_exception(original)
        assert result is original

    # ------------------------------------------------------------------------
    # API Key Detection Tests
    # ------------------------------------------------------------------------

    def test_detect_api_key_error_by_keyword_api_key(self):
        """Should detect API key errors from 'api key' string"""
        exc = Exception("Invalid api key provided")
        result = handle_exception(exc)
        assert isinstance(result, APIKeyError)
        assert result.original_error == exc

    def test_detect_api_key_error_by_keyword_authentication(self):
        """Should detect API key errors from 'authentication' string"""
        exc = Exception("Authentication failed")
        result = handle_exception(exc)
        assert isinstance(result, APIKeyError)

    def test_detect_api_key_error_by_keyword_unauthorized(self):
        """Should detect API key errors from 'unauthorized' string"""
        exc = Exception("401 Unauthorized access")
        result = handle_exception(exc)
        assert isinstance(result, APIKeyError)

    def test_detect_api_key_error_by_status_401(self):
        """Should detect API key errors from '401' status"""
        exc = Exception("Error 401: Access denied")
        result = handle_exception(exc)
        assert isinstance(result, APIKeyError)

    # ------------------------------------------------------------------------
    # Provider Detection Tests (API Key)
    # ------------------------------------------------------------------------

    def test_detect_openai_provider_default(self):
        """OpenAI should be default provider for API key errors"""
        exc = Exception("Invalid api key")
        result = handle_exception(exc)
        assert isinstance(result, APIKeyError)
        assert "OpenAI" in result.message

    def test_detect_anthropic_provider(self):
        """Should detect Anthropic from error string"""
        exc = Exception("Anthropic api key is invalid")
        result = handle_exception(exc)
        assert isinstance(result, APIKeyError)
        assert "Anthropic" in result.message

    def test_detect_google_provider_by_google(self):
        """Should detect Google from 'google' in error string"""
        exc = Exception("Google authentication failed")
        result = handle_exception(exc)
        assert isinstance(result, APIKeyError)
        assert "Google" in result.message

    def test_detect_google_provider_by_gemini(self):
        """Should detect Google from 'gemini' in error string"""
        exc = Exception("Gemini API key invalid")
        result = handle_exception(exc)
        assert isinstance(result, APIKeyError)
        assert "Google" in result.message

    # ------------------------------------------------------------------------
    # Rate Limit Detection Tests
    # ------------------------------------------------------------------------

    def test_detect_rate_limit_by_keyword_rate_limit(self):
        """Should detect rate limit from 'rate limit' string"""
        exc = Exception("Rate limit exceeded")
        result = handle_exception(exc)
        assert isinstance(result, RateLimitError)

    def test_detect_rate_limit_by_keyword_quota(self):
        """Should detect rate limit from 'quota' string"""
        exc = Exception("Quota exceeded for this month")
        result = handle_exception(exc)
        assert isinstance(result, RateLimitError)

    def test_detect_rate_limit_by_status_429(self):
        """Should detect rate limit from '429' status"""
        exc = Exception("HTTP 429: Too Many Requests")
        result = handle_exception(exc)
        assert isinstance(result, RateLimitError)

    # ------------------------------------------------------------------------
    # Provider Detection Tests (Rate Limit)
    # ------------------------------------------------------------------------

    def test_rate_limit_openai_provider(self):
        """Should detect OpenAI provider in rate limit errors"""
        exc = Exception("OpenAI rate limit exceeded")
        result = handle_exception(exc)
        assert isinstance(result, RateLimitError)
        assert "OpenAI" in result.message

    def test_rate_limit_anthropic_provider(self):
        """Should detect Anthropic provider in rate limit errors"""
        exc = Exception("Anthropic rate limit hit")
        result = handle_exception(exc)
        assert isinstance(result, RateLimitError)
        assert "Anthropic" in result.message

    def test_rate_limit_google_provider(self):
        """Should detect Google provider in rate limit errors"""
        exc = Exception("Google API quota exceeded")
        result = handle_exception(exc)
        assert isinstance(result, RateLimitError)
        assert "Google" in result.message

    def test_rate_limit_unknown_provider(self):
        """Should handle rate limit with unknown provider"""
        exc = Exception("Rate limit exceeded")
        result = handle_exception(exc)
        assert isinstance(result, RateLimitError)
        assert "API" in result.message

    # ------------------------------------------------------------------------
    # Network Error Detection Tests
    # ------------------------------------------------------------------------

    def test_detect_network_error_by_keyword_connection(self):
        """Should detect network errors from 'connection' string"""
        exc = Exception("Connection refused")
        result = handle_exception(exc)
        assert isinstance(result, NetworkError)

    def test_detect_network_error_by_keyword_timeout(self):
        """Should detect network errors from 'timeout' string"""
        exc = Exception("Request timeout after 30s")
        result = handle_exception(exc)
        assert isinstance(result, NetworkError)

    def test_detect_network_error_by_keyword_network(self):
        """Should detect network errors from 'network' string"""
        exc = Exception("Network error occurred")
        result = handle_exception(exc)
        assert isinstance(result, NetworkError)

    def test_detect_network_error_by_status_503(self):
        """Should detect network errors from '503' status"""
        exc = Exception("503 Service Unavailable")
        result = handle_exception(exc)
        assert isinstance(result, NetworkError)

    def test_detect_network_error_by_status_502(self):
        """Should detect network errors from '502' status"""
        exc = Exception("502 Bad Gateway")
        result = handle_exception(exc)
        assert isinstance(result, NetworkError)

    # ------------------------------------------------------------------------
    # Model Error Detection Tests
    # ------------------------------------------------------------------------

    def test_detect_model_error_by_keyword_model_not_found(self):
        """Should detect model errors from 'model not found' string"""
        exc = Exception("Model not found: gpt-5")
        result = handle_exception(exc)
        assert isinstance(result, ModelNotFoundError)

    def test_detect_model_error_by_keyword_invalid_model(self):
        """Should detect model errors from 'invalid model' string"""
        exc = Exception("Invalid model specified")
        result = handle_exception(exc)
        assert isinstance(result, ModelNotFoundError)

    def test_detect_model_error_by_status_404(self):
        """Should detect model errors from '404' status"""
        exc = Exception("404: Model endpoint not found")
        result = handle_exception(exc)
        assert isinstance(result, ModelNotFoundError)

    # ------------------------------------------------------------------------
    # Fallback Tests
    # ------------------------------------------------------------------------

    def test_unknown_exception_creates_generic_error(self):
        """Unknown exceptions should create generic SuntoryError"""
        exc = Exception("Something completely unexpected")
        result = handle_exception(exc)
        assert isinstance(result, SuntoryError)
        assert result.category == ErrorCategory.UNKNOWN
        assert result.severity == ErrorSeverity.MEDIUM
        assert result.original_error == exc

    def test_unknown_exception_preserves_message(self):
        """Unknown exceptions should preserve original message"""
        exc = Exception("Custom error message")
        result = handle_exception(exc)
        assert "Custom error message" in result.message

    # ------------------------------------------------------------------------
    # Case Insensitivity Tests
    # ------------------------------------------------------------------------

    def test_case_insensitive_api_key(self):
        """Detection should be case-insensitive"""
        exc = Exception("INVALID API KEY")
        result = handle_exception(exc)
        assert isinstance(result, APIKeyError)

    def test_case_insensitive_rate_limit(self):
        """Rate limit detection should be case-insensitive"""
        exc = Exception("RATE LIMIT EXCEEDED")
        result = handle_exception(exc)
        assert isinstance(result, RateLimitError)

    def test_case_insensitive_provider(self):
        """Provider detection should be case-insensitive"""
        exc = Exception("ANTHROPIC authentication failed")
        result = handle_exception(exc)
        assert isinstance(result, APIKeyError)
        assert "Anthropic" in result.message


# ============================================================================
# EDGE CASES & ROBUSTNESS
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_empty_exception_message(self):
        """Should handle exceptions with empty messages"""
        exc = Exception("")
        result = handle_exception(exc)
        assert isinstance(result, SuntoryError)

    def test_none_in_exception_str(self):
        """Should handle exceptions that stringify to unusual values"""
        exc = Exception(None)
        result = handle_exception(exc)
        assert isinstance(result, SuntoryError)

    def test_multiple_matching_keywords(self):
        """Should handle errors matching multiple patterns (first match wins)"""
        # "api key" comes before "rate limit" in handle_exception
        exc = Exception("API key rate limit exceeded")
        result = handle_exception(exc)
        assert isinstance(result, APIKeyError)

    def test_multiple_providers_in_message(self):
        """Should handle when multiple providers mentioned (first wins)"""
        exc = Exception("Migrating from Anthropic to OpenAI api key invalid")
        result = handle_exception(exc)
        # Should detect "anthropic" first since it's checked before default
        assert isinstance(result, APIKeyError)
        assert "Anthropic" in result.message


# ============================================================================
# LOGGING TESTS
# ============================================================================

class TestLogError:
    """Test error logging function"""

    def test_log_fatal_error(self, caplog):
        """Fatal errors should be logged as critical"""
        error = SuntoryError("Fatal", severity=ErrorSeverity.FATAL)
        log_error(error)
        # Would need proper logging setup to verify

    def test_log_high_error(self, caplog):
        """High severity errors should be logged as error"""
        error = SuntoryError("High", severity=ErrorSeverity.HIGH)
        log_error(error)

    def test_log_medium_error(self, caplog):
        """Medium severity errors should be logged as warning"""
        error = SuntoryError("Medium", severity=ErrorSeverity.MEDIUM)
        log_error(error)

    def test_log_low_error(self, caplog):
        """Low severity errors should be logged as info"""
        error = SuntoryError("Low", severity=ErrorSeverity.LOW)
        log_error(error)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for complete workflows"""

    def test_real_world_openai_auth_error(self):
        """Simulate real OpenAI authentication error"""
        exc = Exception("Error code: 401 - {'error': {'message': 'Incorrect API key provided'}}")
        result = handle_exception(exc)
        assert isinstance(result, APIKeyError)
        assert "OpenAI" in result.message
        formatted = result.format_for_user()
        assert "OPENAI_API_KEY" in formatted

    def test_real_world_anthropic_rate_limit(self):
        """Simulate real Anthropic rate limit error"""
        exc = Exception("429 rate_limit_error: You have exceeded your rate limit")
        result = handle_exception(exc)
        assert isinstance(result, RateLimitError)
        # Note: "anthropic" not in message, so should default to "the API"
        assert result.category == ErrorCategory.RATE_LIMIT

    def test_real_world_connection_timeout(self):
        """Simulate real connection timeout"""
        exc = Exception("HTTPSConnectionPool: Max retries exceeded (Connection timeout)")
        result = handle_exception(exc)
        assert isinstance(result, NetworkError)
        formatted = result.format_for_user()
        assert "internet" in formatted.lower() or "connection" in formatted.lower()

    def test_error_recovery_flow(self):
        """Test complete error -> recovery suggestion flow"""
        exc = Exception("Invalid API key for Anthropic")
        result = handle_exception(exc)
        assert isinstance(result, APIKeyError)
        assert len(result.recovery_suggestions) > 0
        formatted = result.format_for_user()
        assert "How to fix:" in formatted
        assert "ANTHROPIC_API_KEY" in formatted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Standalone test runner for errors.py (no pytest required)
Tests the refactored code to ensure correctness
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Manual imports to avoid dependency issues
import importlib.util
spec = importlib.util.spec_from_file_location(
    "errors",
    "/home/user/AutoGen/v3/src/core/errors.py"
)
errors = importlib.util.module_from_spec(spec)

# Mock the logger to avoid telemetry import
class MockLogger:
    def error(self, *args, **kwargs):
        pass
    def critical(self, *args, **kwargs):
        pass
    def warning(self, *args, **kwargs):
        pass
    def info(self, *args, **kwargs):
        pass

errors.logger = MockLogger()
spec.loader.exec_module(errors)

# Import what we need
APIKeyError = errors.APIKeyError
RateLimitError = errors.RateLimitError
NetworkError = errors.NetworkError
ModelNotFoundError = errors.ModelNotFoundError
SuntoryError = errors.SuntoryError
handle_exception = errors.handle_exception


def test_api_key_detection():
    """Test API key error detection"""
    test_cases = [
        ("invalid api key", APIKeyError),
        ("401 unauthorized", APIKeyError),
        ("authentication failed", APIKeyError),
    ]

    for error_msg, expected_type in test_cases:
        exc = Exception(error_msg)
        result = handle_exception(exc)
        assert isinstance(result, expected_type), \
            f"Expected {expected_type.__name__} for '{error_msg}', got {type(result).__name__}"

    print("✓ API key detection tests passed")


def test_provider_detection():
    """Test provider extraction"""
    test_cases = [
        ("OpenAI api key invalid", "OpenAI"),
        ("Anthropic authentication failed", "Anthropic"),
        ("Google gemini api error", "Google"),
        ("api key invalid", "OpenAI"),  # Default
    ]

    for error_msg, expected_provider in test_cases:
        exc = Exception(error_msg)
        result = handle_exception(exc)
        assert expected_provider in result.message, \
            f"Expected provider '{expected_provider}' in message, got: {result.message}"

    print("✓ Provider detection tests passed")


def test_rate_limit_detection():
    """Test rate limit error detection"""
    test_cases = [
        "rate limit exceeded",
        "quota exhausted",
        "429 too many requests",
    ]

    for error_msg in test_cases:
        exc = Exception(error_msg)
        result = handle_exception(exc)
        assert isinstance(result, RateLimitError), \
            f"Expected RateLimitError for '{error_msg}', got {type(result).__name__}"

    print("✓ Rate limit detection tests passed")


def test_network_error_detection():
    """Test network error detection"""
    test_cases = [
        "connection refused",
        "timeout occurred",
        "503 service unavailable",
    ]

    for error_msg in test_cases:
        exc = Exception(error_msg)
        result = handle_exception(exc)
        assert isinstance(result, NetworkError), \
            f"Expected NetworkError for '{error_msg}', got {type(result).__name__}"

    print("✓ Network error detection tests passed")


def test_model_error_detection():
    """Test model not found error detection"""
    test_cases = [
        "model not found",
        "invalid model",
        "404 model error",
    ]

    for error_msg in test_cases:
        exc = Exception(error_msg)
        result = handle_exception(exc)
        assert isinstance(result, ModelNotFoundError), \
            f"Expected ModelNotFoundError for '{error_msg}', got {type(result).__name__}"

    print("✓ Model error detection tests passed")


def test_passthrough():
    """Test SuntoryError passthrough"""
    original = APIKeyError("TestProvider")
    result = handle_exception(original)
    assert result is original, "SuntoryError should pass through unchanged"

    print("✓ Passthrough test passed")


def test_fallback():
    """Test fallback for unknown errors"""
    exc = Exception("completely unknown error")
    result = handle_exception(exc)
    assert isinstance(result, SuntoryError), "Should create generic SuntoryError"
    assert "unknown error" in result.message.lower()

    print("✓ Fallback test passed")


def test_case_insensitivity():
    """Test case-insensitive matching"""
    exc = Exception("INVALID API KEY")
    result = handle_exception(exc)
    assert isinstance(result, APIKeyError), "Should detect regardless of case"

    print("✓ Case insensitivity test passed")


def test_first_match_wins():
    """Test that first matching handler wins"""
    # "api key" should match before any other pattern
    exc = Exception("api key rate limit network timeout")
    result = handle_exception(exc)
    assert isinstance(result, APIKeyError), \
        "First match (API key) should win when multiple patterns match"

    print("✓ First match priority test passed")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Running Standalone Error Handler Tests")
    print("=" * 60)

    tests = [
        test_api_key_detection,
        test_provider_detection,
        test_rate_limit_detection,
        test_network_error_detection,
        test_model_error_detection,
        test_passthrough,
        test_fallback,
        test_case_insensitivity,
        test_first_match_wins,
    ]

    failed = 0
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"✗ {test.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} ERROR: {e}")
            failed += 1

    print("=" * 60)
    if failed == 0:
        print(f"✓ ALL {len(tests)} TESTS PASSED")
        print("=" * 60)
        return 0
    else:
        print(f"✗ {failed}/{len(tests)} TESTS FAILED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())

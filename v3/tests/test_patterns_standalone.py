#!/usr/bin/env python3
"""
Standalone test suite for preference patterns
Tests only the pattern extraction logic without requiring full dependencies
"""

import os
import sys
import re
import html
import unicodedata
from pathlib import Path
from typing import Optional

# ============================================================================
# EMBEDDED IMPLEMENTATIONS (for standalone testing)
# ============================================================================

def sanitize_name(name: str) -> Optional[str]:
    """Sanitize name (simplified version for testing)"""
    if not name:
        return None

    # Remove ANSI codes
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    name = ansi_escape.sub('', name)

    # Remove control characters
    name = ''.join(
        ch for ch in name
        if unicodedata.category(ch)[0] != 'C' or ch in ['\n', '\t', '\r']
    )

    # Normalize Unicode
    name = unicodedata.normalize('NFKC', name)

    # HTML escape
    name = html.escape(name, quote=True)

    # Length validation
    if len(name) > 100:
        return None

    # Names should be alphanumeric with allowed special chars
    allowed_pattern = re.compile(r"^[a-zA-Z0-9\s\-'.&;#]+$")
    if not allowed_pattern.match(name):
        return None

    return name.strip()


def extract_gender_preference(user_message: str) -> Optional[str]:
    """Extract gender preference from user message"""
    message_lower = user_message.lower()

    # Explicit statements for male
    if any(phrase in message_lower for phrase in [
        "i am a sir", "i'm a sir", "call me sir",
        "i am male", "i'm male", "i am not a madam", "not madam"
    ]):
        return "male"

    # Explicit statements for female
    if any(phrase in message_lower for phrase in [
        "i am a madam", "i'm a madam", "call me madam",
        "i am female", "i'm female", "i am not a sir", "not sir"
    ]):
        return "female"

    return None


def extract_name(user_message: str, max_length: int = 100) -> Optional[str]:
    """Extract name from user message"""
    patterns = [
        r"(?:my name is|call me|i'?m) ((?:Master|Mister|Mr\.?|Miss|Ms\.?|Mrs\.?|Dr\.?|Professor|Prof\.?) [A-Z][a-z]+(?: [A-Z][a-z]+)*)",
        r"my name is ([A-Z][a-z]+(?: [A-Z][a-z]+)+)",
        r"(?:my name is|call me) ([A-Z][a-z]+)",
        r"my name is ([a-z]+)",
        r"call me ([a-z]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, user_message, re.IGNORECASE)
        if match:
            name = match.group(1).strip()

            # Avoid common false positives
            name_lower = name.lower()
            blacklist = ["a", "not", "the", "sir", "madam", "male", "female", "tired", "busy"]
            if name_lower in blacklist:
                continue

            # Length check
            if len(name) > max_length:
                continue

            # Capitalize if all lowercase
            if name.islower():
                name = name.capitalize()

            # Sanitize
            sanitized = sanitize_name(name)
            if sanitized:
                return sanitized

    return None


def extract_title_from_name(name: str) -> Optional[str]:
    """Extract title from name"""
    if not name:
        return None

    title_prefixes = [
        "Master", "Mister", "Mr.", "Mr",
        "Miss", "Ms.", "Ms", "Mrs.", "Mrs",
        "Dr.", "Dr", "Doctor",
        "Professor", "Prof.", "Prof"
    ]

    for title_prefix in title_prefixes:
        if name.startswith(title_prefix):
            return title_prefix.rstrip('.')

    return None


def might_contain_preferences(user_message: str) -> bool:
    """Check if message might contain preferences"""
    message_lower = user_message.lower()
    triggers = [
        "my name", "call me", "i am", "i'm", "i prefer", "i like", "i want",
        "formal", "casual", "professional", "concise", "detailed", "brief", "verbose",
        "timezone", "time zone", "located in",
        "master", "doctor", "professor", "mr", "ms", "mrs", "dr"
    ]
    return any(trigger in message_lower for trigger in triggers)


# ============================================================================
# TESTS
# ============================================================================

class TestGenderExtraction:
    """Test gender preference extraction"""

    def test_male_patterns(self):
        """Test all male gender pattern variations"""
        test_cases = [
            "I am a sir",
            "I'm a sir",
            "Call me sir",
            "I am male",
            "I'm male",
            "I am not a madam",
            "Not madam"
        ]

        for msg in test_cases:
            result = extract_gender_preference(msg)
            assert result == "male", f"Failed for: {msg}"

    def test_female_patterns(self):
        """Test all female gender pattern variations"""
        test_cases = [
            "I am a madam",
            "I'm a madam",
            "Call me madam",
            "I am female",
            "I'm female",
            "I am not a sir",
            "Not sir"
        ]

        for msg in test_cases:
            result = extract_gender_preference(msg)
            assert result == "female", f"Failed for: {msg}"

    def test_no_false_positives(self):
        """Ensure we don't match incorrectly"""
        test_cases = [
            "My boss is a sir",
            "What is a sir?",
            "Sir is a title",
            "I work with a madam",
            "Hello there"
        ]

        for msg in test_cases:
            result = extract_gender_preference(msg)
            assert result is None, f"False positive for: {msg}"


class TestNameExtraction:
    """Test name extraction"""

    def test_single_word_names(self):
        """Test single-word name extraction"""
        test_cases = [
            ("My name is Charles", "Charles"),
            ("Call me Alice", "Alice"),
            ("My name is john", "John"),  # Should capitalize
        ]

        for msg, expected in test_cases:
            result = extract_name(msg)
            if result:
                result_unescaped = html.unescape(result)
                assert result_unescaped == expected, f"Failed for: {msg}, got {result}"
            else:
                assert False, f"Failed to extract name from: {msg}"

    def test_multi_word_names(self):
        """Test multi-word name extraction"""
        test_cases = [
            ("Call me Master Charles", "Master Charles"),
            ("My name is Dr. Smith", "Dr. Smith"),
            ("Call me Professor Watson", "Professor Watson"),
        ]

        for msg, expected in test_cases:
            result = extract_name(msg)
            if result:
                result_unescaped = html.unescape(result)
                assert result_unescaped == expected, f"Failed for: {msg}, got {result}"
            else:
                assert False, f"Failed to extract name from: {msg}"

    def test_name_false_positives(self):
        """Ensure we avoid common false positives"""
        test_cases = [
            "I'm a sir",
            "I am not sure",
            "I'm tired",
        ]

        for msg in test_cases:
            result = extract_name(msg)
            assert result is None, f"False positive for: {msg}, got {result}"

    def test_name_length_validation(self):
        """Test that overly long names are rejected"""
        long_name = "A" * 101
        msg = f"My name is {long_name}"
        result = extract_name(msg)
        assert result is None, "Should reject 101-char name"


class TestTitleExtraction:
    """Test title extraction from names"""

    def test_title_extraction(self):
        """Test extracting titles from full names"""
        test_cases = [
            ("Master Charles", "Master"),
            ("Dr. Smith", "Dr"),
            ("Professor Watson", "Professor"),
            ("Mr. John", "Mr"),
            ("Charles", None),
        ]

        for name, expected_title in test_cases:
            result = extract_title_from_name(name)
            assert result == expected_title, f"Failed for: {name}, got {result}"


class TestHeuristics:
    """Test preference detection heuristics"""

    def test_might_contain_preferences(self):
        """Test fast heuristic for preference detection"""
        positive_cases = [
            "My name is Charles",
            "I prefer formal communication",
            "Call me Master Charles",
            "I am a sir",
        ]

        for msg in positive_cases:
            result = might_contain_preferences(msg)
            assert result is True, f"Should detect preferences in: {msg}"

        negative_cases = [
            "What's the weather like?",
            "Hello, how are you?",
            "Can you help me with Python?",
        ]

        for msg in negative_cases:
            result = might_contain_preferences(msg)
            assert result is False, f"Should not detect preferences in: {msg}"


def run_tests():
    """Run all tests"""
    print("=" * 80)
    print("🧪 RUNNING STANDALONE PREFERENCE PATTERN TESTS")
    print("=" * 80)
    print()

    test_classes = [
        TestGenderExtraction,
        TestNameExtraction,
        TestTitleExtraction,
        TestHeuristics,
    ]

    total_tests = 0
    passed_tests = 0
    failed_tests = []

    for test_class in test_classes:
        print(f"\n📋 {test_class.__name__}")
        print("-" * 80)

        test_instance = test_class()
        test_methods = [m for m in dir(test_instance) if m.startswith("test_")]

        for method_name in test_methods:
            total_tests += 1
            try:
                method = getattr(test_instance, method_name)
                method()
                print(f"  ✓ {method_name}")
                passed_tests += 1
            except AssertionError as e:
                print(f"  ✗ {method_name}: {e}")
                failed_tests.append((test_class.__name__, method_name, str(e)))
            except Exception as e:
                print(f"  ✗ {method_name}: Unexpected error: {e}")
                failed_tests.append((test_class.__name__, method_name, str(e)))

    print()
    print("=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests} ✓")
    print(f"Failed: {len(failed_tests)} ✗")

    if failed_tests:
        print()
        print("Failed tests:")
        for class_name, method_name, error in failed_tests:
            print(f"  - {class_name}.{method_name}")
            print(f"    {error}")

    print()

    if len(failed_tests) == 0:
        print("🎉 ALL TESTS PASSED! 🎉")
        return True
    else:
        print(f"❌ {len(failed_tests)} test(s) failed")
        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

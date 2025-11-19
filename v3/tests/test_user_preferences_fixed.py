#!/usr/bin/env python3
"""
Comprehensive test suite for User Preferences Manager (FIXED VERSION)
Tests extraction, persistence, updates, and edge cases
Uses proper package imports instead of dynamic module loading
"""

import os
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Now import using proper package structure
from src.alfred.preference_patterns import (
    extract_gender_preference,
    extract_name,
    extract_title_from_name,
    might_contain_preferences
)


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
            print(f"  ✓ '{msg}' → male")

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
            print(f"  ✓ '{msg}' → female")

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
            print(f"  ✓ '{msg}' → None (correctly rejected)")


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
            # Note: Sanitization may HTML-escape the name
            if result:
                # Unescape for comparison
                import html
                result_unescaped = html.unescape(result)
                assert result_unescaped == expected, f"Failed for: {msg}, got {result}"
                print(f"  ✓ '{msg}' → '{result_unescaped}'")
            else:
                assert False, f"Failed to extract name from: {msg}"

    def test_multi_word_names(self):
        """Test multi-word name extraction"""
        test_cases = [
            ("Call me Master Charles", "Master Charles"),
            ("My name is Dr. Smith", "Dr. Smith"),
            ("My name is Mr. John Doe", "Mr. John Doe"),
            ("Call me Professor Watson", "Professor Watson"),
        ]

        for msg, expected in test_cases:
            result = extract_name(msg)
            if result:
                import html
                result_unescaped = html.unescape(result)
                assert result_unescaped == expected, f"Failed for: {msg}, got {result}"
                print(f"  ✓ '{msg}' → '{result_unescaped}'")
            else:
                assert False, f"Failed to extract name from: {msg}"

    def test_name_false_positives(self):
        """Ensure we avoid common false positives"""
        test_cases = [
            "I'm a sir",  # Should not capture 'a'
            "I am not sure",  # Should not capture 'not'
            "I'm tired",  # Should not capture 'tired'
        ]

        for msg in test_cases:
            result = extract_name(msg)
            assert result is None, f"False positive for: {msg}, got {result}"
            print(f"  ✓ '{msg}' → None (correctly rejected)")

    def test_name_length_validation(self):
        """Test that overly long names are rejected"""
        # 101 character name should be rejected
        long_name = "A" * 101
        msg = f"My name is {long_name}"
        result = extract_name(msg)
        assert result is None, "Should reject 101-char name"
        print(f"  ✓ Rejected 101-character name")

    def test_name_security(self):
        """Test that malicious names are sanitized or rejected"""
        malicious_cases = [
            ("My name is <script>alert('XSS')</script>", None),  # Should be rejected or sanitized
            ("Call me Robert'; DROP TABLE users;--", None),  # SQL injection attempt
        ]

        for msg, expected in malicious_cases:
            result = extract_name(msg)
            if result:
                # If sanitized, should not contain dangerous characters
                assert '<script' not in result.lower(), f"XSS not sanitized: {result}"
                assert 'drop table' not in result.lower(), f"SQL injection not sanitized: {result}"
                print(f"  ✓ '{msg}' → sanitized to '{result}'")
            else:
                print(f"  ✓ '{msg}' → rejected (secure)")


class TestTitleExtraction:
    """Test title extraction from names"""

    def test_title_extraction(self):
        """Test extracting titles from full names"""
        test_cases = [
            ("Master Charles", "Master"),
            ("Dr. Smith", "Dr"),
            ("Professor Watson", "Professor"),
            ("Mr. John", "Mr"),
            ("Charles", None),  # No title
        ]

        for name, expected_title in test_cases:
            result = extract_title_from_name(name)
            assert result == expected_title, f"Failed for: {name}, got {result}"
            print(f"  ✓ '{name}' → title: {result}")


class TestHeuristics:
    """Test preference detection heuristics"""

    def test_might_contain_preferences(self):
        """Test fast heuristic for preference detection"""
        # Should trigger
        positive_cases = [
            "My name is Charles",
            "I prefer formal communication",
            "Call me Master Charles",
            "I'm in timezone America/New_York",
            "I am a sir",
        ]

        for msg in positive_cases:
            result = might_contain_preferences(msg)
            assert result is True, f"Should detect preferences in: {msg}"
            print(f"  ✓ '{msg}' → might contain preferences")

        # Should not trigger
        negative_cases = [
            "What's the weather like?",
            "Hello, how are you?",
            "Can you help me with Python?",
            "What is 2+2?",
        ]

        for msg in negative_cases:
            result = might_contain_preferences(msg)
            assert result is False, f"Should not detect preferences in: {msg}"
            print(f"  ✓ '{msg}' → no preferences detected")


def run_tests():
    """Run all tests"""
    print("=" * 80)
    print("🧪 RUNNING USER PREFERENCES TEST SUITE (FIXED)")
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
                print(f"✅ {method_name}")
                passed_tests += 1
            except AssertionError as e:
                print(f"❌ {method_name}: {e}")
                failed_tests.append((test_class.__name__, method_name, str(e)))
            except Exception as e:
                print(f"❌ {method_name}: Unexpected error: {e}")
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

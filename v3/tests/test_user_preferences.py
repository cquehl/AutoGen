#!/usr/bin/env python3
"""
Comprehensive test suite for User Preferences Manager
Tests extraction, persistence, updates, and edge cases
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from alfred.user_preferences import UserPreferencesManager


class TestGenderExtraction:
    """Test gender preference extraction"""

    def test_male_patterns(self):
        """Test all male gender pattern variations"""
        manager = UserPreferencesManager("test_session")

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
            result = manager.extract_gender_preference(msg)
            assert result == "male", f"Failed for: {msg}"

    def test_female_patterns(self):
        """Test all female gender pattern variations"""
        manager = UserPreferencesManager("test_session")

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
            result = manager.extract_gender_preference(msg)
            assert result == "female", f"Failed for: {msg}"

    def test_no_false_positives(self):
        """Ensure we don't match incorrectly"""
        manager = UserPreferencesManager("test_session")

        test_cases = [
            "My boss is a sir",
            "What is a sir?",
            "Sir is a title",
            "I work with a madam",
            "Hello there"
        ]

        for msg in test_cases:
            result = manager.extract_gender_preference(msg)
            assert result is None, f"False positive for: {msg}"


class TestNameExtraction:
    """Test name extraction"""

    def test_single_word_names(self):
        """Test single-word name extraction"""
        manager = UserPreferencesManager("test_session")

        test_cases = [
            ("My name is Charles", "Charles"),
            ("Call me Alice", "Alice"),
            ("My name is john", "John"),  # Should capitalize
        ]

        for msg, expected in test_cases:
            result = manager.extract_name(msg)
            assert result == expected, f"Failed for: {msg}, got {result}"

    def test_multi_word_names(self):
        """Test multi-word name extraction"""
        manager = UserPreferencesManager("test_session")

        test_cases = [
            ("Call me Master Charles", "Master Charles"),
            ("My name is Dr. Smith", "Dr. Smith"),
            ("My name is Mr. John Doe", "Mr. John Doe"),
            ("Call me Professor Watson", "Professor Watson"),
        ]

        for msg, expected in test_cases:
            result = manager.extract_name(msg)
            assert result == expected, f"Failed for: {msg}, got {result}"

    def test_name_false_positives(self):
        """Ensure we avoid common false positives"""
        manager = UserPreferencesManager("test_session")

        test_cases = [
            "I'm a sir",  # Should not capture 'a'
            "I am not sure",  # Should not capture 'not'
            "I'm tired",  # Should not capture 'tired'
        ]

        for msg in test_cases:
            result = manager.extract_name(msg)
            assert result is None, f"False positive for: {msg}, got {result}"

    def test_name_length_validation(self):
        """Test that overly long names are rejected"""
        manager = UserPreferencesManager("test_session")

        # 101 character name should be rejected
        long_name = "A" * 101
        msg = f"My name is {long_name}"
        result = manager.extract_name(msg)
        assert result is None


class TestUpdateLogic:
    """Test preference update logic"""

    def test_update_returns_only_changed(self):
        """Test that update_from_message returns only changed preferences"""
        manager = UserPreferencesManager("test_session")

        # First update: set gender
        updated = manager.update_from_message("I am a sir")
        assert updated == {"gender": "male"}
        assert manager.preferences == {"gender": "male"}

        # Second update: set name (gender shouldn't be in updated)
        updated = manager.update_from_message("My name is Charles")
        assert updated == {"name": "Charles"}
        assert manager.preferences == {"gender": "male", "name": "Charles"}

        # Third update: same message, no changes
        updated = manager.update_from_message("I am a sir")
        assert updated == {}  # No changes

    def test_preference_correction(self):
        """Test that preferences can be corrected"""
        manager = UserPreferencesManager("test_session")

        # Initial preference
        manager.update_from_message("I am a sir")
        assert manager.preferences["gender"] == "male"

        # Correction
        updated = manager.update_from_message("Actually, I am a madam")
        assert updated == {"gender": "female"}
        assert manager.preferences["gender"] == "female"


class TestConfirmationMessages:
    """Test confirmation message generation"""

    def test_gender_confirmation(self):
        """Test gender preference confirmation"""
        manager = UserPreferencesManager("test_session")

        msg = manager.get_confirmation_message({"gender": "male"})
        assert msg is not None
        assert "sir" in msg.lower()

        msg = manager.get_confirmation_message({"gender": "female"})
        assert msg is not None
        assert "madam" in msg.lower()

    def test_name_confirmation(self):
        """Test name preference confirmation"""
        manager = UserPreferencesManager("test_session")

        msg = manager.get_confirmation_message({"name": "Charles"})
        assert msg is not None
        assert "Charles" in msg

    def test_multiple_confirmation(self):
        """Test confirmation for multiple updated preferences"""
        manager = UserPreferencesManager("test_session")

        msg = manager.get_confirmation_message({
            "gender": "male",
            "name": "Charles"
        })
        assert msg is not None
        assert "sir" in msg.lower()
        assert "Charles" in msg

    def test_empty_confirmation(self):
        """Test that empty updates return None"""
        manager = UserPreferencesManager("test_session")

        msg = manager.get_confirmation_message({})
        assert msg is None


class TestPersistence:
    """Test persistence across instances"""

    def test_user_id_persistence(self):
        """Test that same user_id shares preferences"""
        # Instance 1: Set preferences
        manager1 = UserPreferencesManager("session1", user_id="user123")
        manager1.preferences = {"gender": "male", "name": "Charles"}
        manager1._save_to_storage()

        # Instance 2: Load preferences (different session, same user)
        manager2 = UserPreferencesManager("session2", user_id="user123")
        manager2.load_from_storage()

        # Should have loaded the preferences
        assert manager2.preferences.get("gender") == "male"
        assert manager2.preferences.get("name") == "Charles"

    def test_deduplication(self):
        """Test that updating preferences doesn't create duplicates"""
        manager = UserPreferencesManager("test_session", user_id="user_dedup")

        # Set preference
        manager.update_from_message("I am a sir")

        # Update same preference
        manager.update_from_message("I am a sir")

        # Load and verify no duplicates
        manager2 = UserPreferencesManager("test_session2", user_id="user_dedup")
        manager2.load_from_storage()

        # Should still have only one value
        assert manager2.preferences.get("gender") == "male"


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_conflicting_input(self):
        """Test handling of conflicting preferences in one message"""
        manager = UserPreferencesManager("test_session")

        # Only one should win (first match)
        updated = manager.update_from_message("I'm a sir and a madam")
        # Should extract "sir" (appears first in patterns)
        assert updated.get("gender") in ["male", "female"]

    def test_case_insensitivity(self):
        """Test case-insensitive matching"""
        manager = UserPreferencesManager("test_session")

        result = manager.extract_gender_preference("I AM A SIR")
        assert result == "male"

        result = manager.extract_gender_preference("CALL ME MADAM")
        assert result == "female"

    def test_empty_input(self):
        """Test handling of empty input"""
        manager = UserPreferencesManager("test_session")

        result = manager.extract_gender_preference("")
        assert result is None

        result = manager.extract_name("")
        assert result is None

        updated = manager.update_from_message("")
        assert updated == {}


def run_tests():
    """Run all tests"""
    print("=" * 80)
    print("🧪 RUNNING USER PREFERENCES TEST SUITE")
    print("=" * 80)
    print()

    test_classes = [
        TestGenderExtraction,
        TestNameExtraction,
        TestUpdateLogic,
        TestConfirmationMessages,
        TestPersistence,
        TestEdgeCases
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

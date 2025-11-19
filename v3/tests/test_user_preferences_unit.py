#!/usr/bin/env python3
"""
Unit tests for User Preferences Manager (extraction logic only)
Tests pattern matching without requiring full system initialization
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Import only the class we need
# We'll mock the dependencies to avoid full initialization
class MockVectorManager:
    """Mock vector manager for testing"""
    def get_or_create_collection(self, name):
        return self

    def delete(self, ids):
        pass

    def add_memory(self, **kwargs):
        pass

    def query_memory(self, **kwargs):
        return {"metadatas": [[]]}


# Monkey patch before import
sys.modules['core'] = type(sys)('core')
sys.modules['core'].get_logger = lambda name: MockLogger()
sys.modules['core'].get_vector_manager = lambda: MockVectorManager()

class MockLogger:
    """Mock logger for testing"""
    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass


# Import directly from the module file, not through the package
import importlib.util
spec = importlib.util.spec_from_file_location("user_preferences", "src/alfred/user_preferences.py")
user_prefs_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(user_prefs_module)
UserPreferencesManager = user_prefs_module.UserPreferencesManager


def test_gender_extraction():
    """Test gender extraction patterns"""
    print("Testing gender extraction...")

    manager = UserPreferencesManager("test")

    # Test male patterns
    male_cases = [
        "I am a sir",
        "I'm a sir",
        "Call me sir",
        "I am male",
        "I'm male",
        "I am not a madam"
    ]

    for msg in male_cases:
        result = manager.extract_gender_preference(msg)
        assert result == "male", f"❌ Failed for: '{msg}' (got {result})"
        print(f"  ✓ '{msg}' → male")

    # Test female patterns
    female_cases = [
        "I am a madam",
        "Call me madam",
        "I am female",
        "I'm female",
        "I am not a sir"
    ]

    for msg in female_cases:
        result = manager.extract_gender_preference(msg)
        assert result == "female", f"❌ Failed for: '{msg}' (got {result})"
        print(f"  ✓ '{msg}' → female")

    print("✅ Gender extraction tests passed")


def test_name_extraction():
    """Test name extraction patterns"""
    print("\nTesting name extraction...")

    manager = UserPreferencesManager("test")

    # Test cases: (message, expected_name)
    test_cases = [
        ("My name is Charles", "Charles"),
        ("Call me Alice", "Alice"),
        ("My name is john", "John"),  # Should capitalize
        ("Call me Master Charles", "Master Charles"),
        ("My name is Dr. Smith", "Dr. Smith"),
        ("My name is Mr. John Doe", "Mr. John Doe"),
        ("Call me Professor Watson", "Professor Watson"),
    ]

    for msg, expected in test_cases:
        result = manager.extract_name(msg)
        assert result == expected, f"❌ Failed for: '{msg}' (expected '{expected}', got '{result}')"
        print(f"  ✓ '{msg}' → '{expected}'")

    # Test false positives should return None
    false_positives = [
        "I'm a sir",
        "I am not sure",
        "I'm tired",
    ]

    for msg in false_positives:
        result = manager.extract_name(msg)
        assert result is None, f"❌ False positive for: '{msg}' (got '{result}')"
        print(f"  ✓ '{msg}' → None (correctly rejected)")

    print("✅ Name extraction tests passed")


def test_update_logic():
    """Test update logic returns only changed prefs"""
    print("\nTesting update logic...")

    manager = UserPreferencesManager("test")

    # First update: set gender
    updated = manager.update_from_message("I am a sir")
    assert updated == {"gender": "male"}, f"❌ Expected {{'gender': 'male'}}, got {updated}"
    print(f"  ✓ First update: {updated}")

    # Second update: set name (gender shouldn't be in updated)
    updated = manager.update_from_message("My name is Charles")
    assert updated == {"name": "Charles"}, f"❌ Expected {{'name': 'Charles'}}, got {updated}"
    print(f"  ✓ Second update: {updated}")

    # Both should be in preferences
    assert manager.preferences == {"gender": "male", "name": "Charles"}
    print(f"  ✓ Total preferences: {manager.preferences}")

    # Third update: same message, no changes
    updated = manager.update_from_message("I am a sir")
    assert updated == {}, f"❌ Expected empty dict, got {updated}"
    print(f"  ✓ No change update: {updated}")

    print("✅ Update logic tests passed")


def test_confirmation_messages():
    """Test confirmation message generation"""
    print("\nTesting confirmation messages...")

    manager = UserPreferencesManager("test")

    # Gender only
    msg = manager.get_confirmation_message({"gender": "male"})
    assert msg is not None
    assert "sir" in msg.lower()
    print(f"  ✓ Gender (male): '{msg}'")

    # Name only
    msg = manager.get_confirmation_message({"name": "Charles"})
    assert msg is not None
    assert "Charles" in msg
    print(f"  ✓ Name: '{msg}'")

    # Both
    msg = manager.get_confirmation_message({"gender": "male", "name": "Charles"})
    assert msg is not None
    assert "sir" in msg.lower() and "Charles" in msg
    print(f"  ✓ Both: '{msg}'")

    # Empty
    msg = manager.get_confirmation_message({})
    assert msg is None
    print(f"  ✓ Empty: None")

    print("✅ Confirmation message tests passed")


def test_input_validation():
    """Test input validation"""
    print("\nTesting input validation...")

    manager = UserPreferencesManager("test")

    # Very long name should be rejected
    long_name = "A" * 101
    result = manager.extract_name(f"My name is {long_name}")
    assert result is None, f"❌ Should reject 101-char name, got: {result}"
    print(f"  ✓ Rejected 101-character name")

    # 100 chars should be accepted
    ok_name = "A" * 100
    result = manager.extract_name(f"My name is {ok_name}")
    assert result == ok_name, f"❌ Should accept 100-char name"
    print(f"  ✓ Accepted 100-character name")

    print("✅ Input validation tests passed")


def run_all_tests():
    """Run all unit tests"""
    print("=" * 80)
    print("🧪 USER PREFERENCES UNIT TESTS")
    print("=" * 80)
    print()

    tests = [
        test_gender_extraction,
        test_name_extraction,
        test_update_logic,
        test_confirmation_messages,
        test_input_validation,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ TEST FAILED: {test_func.__name__}")
            print(f"   {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ TEST ERROR: {test_func.__name__}")
            print(f"   {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print()
    print("=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"Passed: {passed}/{len(tests)} ✓")
    print(f"Failed: {failed}/{len(tests)} ✗")

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! 🎉")
        return True
    else:
        print(f"\n❌ {failed} test(s) failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

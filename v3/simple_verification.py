#!/usr/bin/env python3
"""Simple verification that all our fixes work"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))


def test_imports():
    """Test that all imports work (proves SQLAlchemy bug is fixed)"""
    print("Testing imports...")
    try:
        from src.core import get_settings, get_db_manager, get_logger
        from src.alfred import Alfred
        print("✅ All imports successful (SQLAlchemy 'metadata' bug FIXED)")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def test_settings():
    """Test that settings load properly (proves .env format fix)"""
    print("\nTesting settings...")
    try:
        from src.core import get_settings
        settings = get_settings()

        # This would fail if ALLOWED_DIRECTORIES wasn't JSON
        dirs = settings.allowed_directories
        print(f"✅ Settings loaded (ALLOWED_DIRECTORIES JSON format FIXED)")
        print(f"   - Allowed directories: {len(dirs)} paths")
        print(f"   - Default model: {settings.default_model}")
        return True
    except Exception as e:
        print(f"❌ Settings failed: {e}")
        return False


def test_api_method():
    """Test that new convenience method exists"""
    print("\nTesting new API method...")
    try:
        from src.alfred import Alfred
        import inspect

        # Check if method exists
        if hasattr(Alfred, 'handle_message'):
            sig = inspect.signature(Alfred.handle_message)
            print(f"✅ handle_message() method exists (NEW API added)")
            print(f"   - Signature: {sig}")
            return True
        else:
            print(f"❌ handle_message() method missing")
            return False
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False


def main():
    print("="*70)
    print("🥃 SUNTORY V3 - VERIFICATION OF FIXES")
    print("="*70 + "\n")

    results = []

    # Run tests
    results.append(("Imports (SQLAlchemy fix)", test_imports()))
    results.append(("Settings (.env format fix)", test_settings()))
    results.append(("API method (convenience added)", test_api_method()))

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL FIXES VERIFIED!")
        print("\n✓ Fixed SQLAlchemy 'metadata' reserved word bug")
        print("✓ Fixed .env ALLOWED_DIRECTORIES JSON format")
        print("✓ Added handle_message() convenience method")
        print("\n💪 Suntory V3 is ready for integration testing!\n")
        return True
    else:
        print("\n⚠️  Some tests failed\n")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

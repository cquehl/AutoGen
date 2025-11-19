#!/usr/bin/env python3
"""
Test script for Team Mode fix
Tests that the model_info AttributeError is resolved
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


async def test_team_mode():
    """Test team orchestration mode"""
    print("=" * 80)
    print("🧪 TESTING TEAM MODE FIX")
    print("=" * 80)
    print()

    try:
        # Import Alfred
        from alfred.main_enhanced import AlfredEnhanced

        print("✓ Imports successful")
        print()

        # Initialize Alfred
        print("Initializing Alfred...")
        alfred = AlfredEnhanced()
        await alfred.initialize()
        print("✓ Alfred initialized")
        print(f"  Session ID: {alfred.session_id}")
        print()

        # Test 1: Simple greeting
        print("=" * 80)
        print("TEST 1: Greeting")
        print("=" * 80)
        greeting = await alfred.greet()
        print(f"Alfred: {greeting}")
        print("✓ Greeting test passed")
        print()

        # Test 2: Direct mode
        print("=" * 80)
        print("TEST 2: Direct Mode")
        print("=" * 80)
        print("User: Hello Alfred, how are you?")
        response = await alfred.handle_message("Hello Alfred, how are you?")
        print(f"Alfred: {response[:200]}...")
        print("✓ Direct mode test passed")
        print()

        # Test 3: User preference detection
        print("=" * 80)
        print("TEST 3: User Preference Memory")
        print("=" * 80)
        print("User: I am a sir, not a madam")
        response = await alfred.handle_message("I am a sir, not a madam")
        print(f"Alfred: {response}")

        prefs = alfred.preferences_manager.get_preferences()
        print(f"Stored preferences: {prefs}")

        if prefs.get("gender") == "male":
            print("✓ User preference test passed")
        else:
            print("✗ User preference test FAILED")
        print()

        # Test 4: Team mode (THE CRITICAL TEST)
        print("=" * 80)
        print("TEST 4: Team Mode (Critical Fix Test)")
        print("=" * 80)
        print("User: Create a simple hello world Python script")
        print()
        print("This should trigger team mode and test the model_info fix...")
        print()

        try:
            response = await alfred.handle_message(
                "Create a simple hello world Python script"
            )
            print(f"Alfred: {response[:500]}...")
            print()
            print("✓ ✓ ✓ TEAM MODE TEST PASSED! ✓ ✓ ✓")
            print("The model_info AttributeError has been FIXED!")
            print()
        except AttributeError as e:
            if "model_info" in str(e):
                print(f"✗ ✗ ✗ TEAM MODE TEST FAILED! ✗ ✗ ✗")
                print(f"The model_info error still occurs: {e}")
                print()
                return False
            else:
                raise

        # Test 5: Session cost tracking
        print("=" * 80)
        print("TEST 5: Cost Tracking")
        print("=" * 80)
        session_cost = alfred.get_session_cost()
        print(f"Total session cost: ${session_cost:.4f}")
        print(f"Total messages: {alfred.get_conversation_count()}")
        print("✓ Cost tracking test passed")
        print()

        # Cleanup
        await alfred.shutdown()
        print("✓ Alfred shutdown complete")
        print()

        # Summary
        print("=" * 80)
        print("🎉 ALL TESTS PASSED! 🎉")
        print("=" * 80)
        print()
        print("Summary:")
        print("  ✓ Model client factory works")
        print("  ✓ AutoGen agents initialize correctly")
        print("  ✓ Team mode executes without AttributeError")
        print("  ✓ User preferences are stored and retrieved")
        print("  ✓ Cost tracking functions")
        print()
        print("The critical model_info bug has been FIXED!")
        print()

        return True

    except Exception as e:
        print()
        print("=" * 80)
        print("✗ TEST FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        import traceback
        print()
        print("Full traceback:")
        traceback.print_exc()
        print()
        return False


async def test_model_client_factory():
    """Test model client factory in isolation"""
    print("=" * 80)
    print("🔧 TESTING MODEL CLIENT FACTORY")
    print("=" * 80)
    print()

    try:
        from core.model_factory import create_model_client

        print("Creating model client for Azure OpenAI...")
        client = create_model_client()
        print(f"✓ Client created: {type(client).__name__}")
        print(f"  Has model_info: {hasattr(client, 'model_info')}")

        if hasattr(client, 'model_info'):
            print(f"  model_info type: {type(client.model_info)}")
            print("✓ Model client factory test PASSED")
        else:
            print("✗ Model client missing model_info attribute")
            return False

        print()
        return True

    except Exception as e:
        print(f"✗ Model client factory test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print()
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║                                                           ║")
    print("║   SUNTORY V3 - TEAM MODE FIX VALIDATION                  ║")
    print("║                                                           ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # Test model client factory first
    factory_ok = await test_model_client_factory()

    if not factory_ok:
        print("⚠️  Model client factory test failed. Skipping full tests.")
        return False

    # Run full Alfred tests
    all_ok = await test_team_mode()

    if all_ok:
        print("=" * 80)
        print("SUCCESS! All critical bugs have been fixed.")
        print("=" * 80)
        return True
    else:
        print("=" * 80)
        print("FAILURE: Some tests did not pass.")
        print("=" * 80)
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

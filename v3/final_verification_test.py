#!/usr/bin/env python3
"""
Final verification test for V3 Suntory
Tests all fixed components
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.alfred import Alfred
from src.core import get_logger, get_settings

logger = get_logger(__name__)


async def main():
    print("\n" + "="*70)
    print("🥃 SUNTORY V3 - FINAL VERIFICATION TEST")
    print("="*70 + "\n")

    try:
        # Test 1: Settings
        print("1️⃣  Testing Settings...")
        settings = get_settings()
        print(f"   ✅ Settings loaded")
        print(f"   📍 Workspace: {settings.workspace_dir}")
        print(f"   🤖 Default model: {settings.default_model}")
        print(f"   📁 Allowed directories: {len(settings.allowed_directories)} paths")

        # Test 2: Database (checks for reserved word bug)
        print("\n2️⃣  Testing Database (reserved word fix)...")
        from src.core import get_db_manager
        db = await get_db_manager()
        print(f"   ✅ Database initialized (no 'metadata' reserved word error!)")

        # Test 3: Alfred initialization
        print("\n3️⃣  Testing Alfred initialization...")
        alfred = Alfred()
        await alfred.initialize()
        print(f"   ✅ Alfred initialized")
        print(f"   🆔 Session ID: {alfred.session_id}")

        # Test 4: New convenience method
        print("\n4️⃣  Testing new handle_message() method...")
        response = await alfred.handle_message("Hello!")
        print(f"   ✅ handle_message() works!")
        print(f"   📝 Response length: {len(response)} chars")
        print(f"   Preview: {response[:100]}...")

        # Test 5: Quick greeting
        print("\n5️⃣  Testing greeting generation...")
        greeting = await alfred.generate_greeting()
        print(f"   ✅ Greeting: {greeting[:80]}...")

        # Summary
        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED")
        print("="*70)
        print("\n🎉 Suntory V3 is fully operational!")
        print("\nFixed issues:")
        print("  ✓ SQLAlchemy 'metadata' reserved word bug")
        print("  ✓ .env JSON format for ALLOWED_DIRECTORIES")
        print("  ✓ Added handle_message() convenience method")
        print("\n💪 System ready for production testing!\n")

    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

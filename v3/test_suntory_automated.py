#!/usr/bin/env python3
"""
Automated test script for Suntory v3
Simulates user interactions and tests the system
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.alfred import Alfred
from src.core import get_logger, get_settings

logger = get_logger(__name__)


async def test_alfred_conversation():
    """Test Alfred with simulated conversation"""

    print("\n" + "="*60)
    print("🧪 SUNTORY V3 AUTOMATED TEST")
    print("="*60 + "\n")

    # Initialize Alfred
    print("▸ Initializing Alfred...")
    alfred = Alfred()
    await alfred.initialize()
    print("✓ Alfred initialized\n")

    # Test scenarios
    test_cases = [
        {
            "name": "Greeting Test",
            "input": "Hello Alfred!",
            "expected_keywords": ["alfred", "service", "assist"]
        },
        {
            "name": "Capabilities Query",
            "input": "What can you help me with?",
            "expected_keywords": ["mode", "direct", "team"]
        },
        {
            "name": "Simple Question (Direct Mode)",
            "input": "What is Python?",
            "expected_keywords": ["programming", "language"]
        },
        {
            "name": "Complex Task Detection",
            "input": "Build a REST API for user authentication",
            "expected_keywords": ["team", "specialist", "engineer"]
        }
    ]

    results = []

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}/{len(test_cases)}: {test_case['name']}")
        print(f"   Input: \"{test_case['input']}\"")
        print("-" * 60)

        try:
            # Send message to Alfred
            response = await alfred.handle_message(test_case["input"])

            # Display response
            print(f"\n   Response Preview:")
            preview = response[:200] + "..." if len(response) > 200 else response
            print(f"   {preview}\n")

            # Check for expected keywords
            response_lower = response.lower()
            found_keywords = [
                kw for kw in test_case["expected_keywords"]
                if kw.lower() in response_lower
            ]

            passed = len(found_keywords) > 0

            result = {
                "test": test_case["name"],
                "passed": passed,
                "found_keywords": found_keywords,
                "response_length": len(response)
            }
            results.append(result)

            status = "✅ PASS" if passed else "⚠️  PARTIAL"
            print(f"   Status: {status}")
            if found_keywords:
                print(f"   Keywords found: {', '.join(found_keywords)}")

        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
            results.append({
                "test": test_case["name"],
                "passed": False,
                "error": str(e)
            })

    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)

    passed = sum(1 for r in results if r.get("passed", False))
    total = len(results)

    for result in results:
        status = "✅" if result.get("passed", False) else "❌"
        print(f"{status} {result['test']}")
        if "error" in result:
            print(f"   Error: {result['error']}")

    print(f"\nPassed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")

    return results


async def test_system_components():
    """Test individual system components"""

    print("\n" + "="*60)
    print("🔧 COMPONENT TESTS")
    print("="*60 + "\n")

    components = {
        "Settings": lambda: get_settings(),
        "Logger": lambda: get_logger(__name__),
    }

    for name, initializer in components.items():
        try:
            component = initializer()
            print(f"✓ {name}: Initialized successfully")
        except Exception as e:
            print(f"✗ {name}: Failed - {str(e)}")


async def main():
    """Run all tests"""
    print("\n🥃 Suntory v3 - Autonomous Testing Suite\n")

    try:
        # Component tests
        await test_system_components()

        # Conversation tests
        results = await test_alfred_conversation()

        print("\n" + "="*60)
        print("🎉 TESTING COMPLETE")
        print("="*60 + "\n")

        return results

    except KeyboardInterrupt:
        print("\n\n⚠️  Testing interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Critical error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

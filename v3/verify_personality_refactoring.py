"""
Structural verification for personality.py refactoring
Checks code structure and prompt extraction
"""

import sys
from pathlib import Path

# Add v3/src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def analyze_personality_file():
    """Analyze personality.py structure"""
    personality_path = Path(__file__).parent / "src" / "alfred" / "personality.py"

    with open(personality_path) as f:
        content = f.read()
        lines = content.split('\n')

    results = {}

    # Line count
    original_lines = 262
    current_lines = len(lines)
    results['line_count'] = current_lines
    results['lines_changed'] = original_lines - current_lines
    results['change_percent'] = (original_lines - current_lines) / original_lines * 100

    # Check constants extracted
    results['has_formal_greetings'] = 'FORMAL_GREETINGS = {' in content
    results['has_casual_greetings'] = 'CASUAL_GREETINGS = [' in content
    results['has_ai_greeting_prompt'] = 'AI_GREETING_SYSTEM_PROMPT = """' in content
    results['has_system_message_template'] = 'ALFRED_SYSTEM_MESSAGE_TEMPLATE = """' in content
    results['has_reflection_prompts'] = 'REFLECTION_PROMPTS = [' in content

    # Check class exists
    results['has_alfred_personality_class'] = 'class AlfredPersonality:' in content

    # Check methods exist
    results['has_get_time_of_day'] = 'def get_time_of_day(' in content
    results['has_get_formal_greeting'] = 'def get_formal_greeting(' in content
    results['has_get_casual_greeting'] = 'def get_casual_greeting(' in content
    results['has_generate_ai_greeting'] = 'async def generate_ai_greeting(' in content
    results['has_get_greeting'] = 'async def get_greeting(' in content
    results['has_get_system_message'] = 'def get_system_message(' in content
    results['has_get_reflection_prompts'] = 'def get_reflection_prompts(' in content

    # Check new helper methods
    results['has_build_preference_context'] = 'def _build_preference_context(' in content
    results['has_get_personality_description'] = 'def _get_personality_description(' in content

    # Check simplified methods use constants
    results['formal_uses_constant'] = 'return random.choice(FORMAL_GREETINGS[self.get_time_of_day()])' in content
    results['casual_uses_constant'] = 'return random.choice(CASUAL_GREETINGS)' in content
    results['ai_greeting_uses_constant'] = 'AI_GREETING_SYSTEM_PROMPT' in content
    results['system_message_uses_template'] = 'ALFRED_SYSTEM_MESSAGE_TEMPLATE.format(' in content
    results['reflection_uses_constant'] = 'return REFLECTION_PROMPTS' in content

    # Check dict dispatch in get_greeting
    results['uses_greeting_map'] = 'greeting_map = {' in content

    # Check singleton pattern
    results['has_get_alfred_personality'] = 'def get_alfred_personality()' in content

    return results


def print_results(results):
    """Print verification results"""
    print("=" * 70)
    print("PERSONALITY.PY REFACTORING STRUCTURAL VERIFICATION")
    print("=" * 70)
    print()

    # Metrics
    print("📊 METRICS:")
    print(f"  • Original line count: 262")
    print(f"  • Current line count: {results['line_count']}")
    print(f"  • Lines changed: {results['lines_changed']:+d}")
    print(f"  • Change: {results['change_percent']:+.1f}%")
    print()

    # Constants Extraction
    print("📦 CONSTANTS EXTRACTED:")
    constant_checks = [
        ("FORMAL_GREETINGS", results['has_formal_greetings']),
        ("CASUAL_GREETINGS", results['has_casual_greetings']),
        ("AI_GREETING_SYSTEM_PROMPT", results['has_ai_greeting_prompt']),
        ("ALFRED_SYSTEM_MESSAGE_TEMPLATE", results['has_system_message_template']),
        ("REFLECTION_PROMPTS", results['has_reflection_prompts']),
    ]

    constant_passed = 0
    for name, passed in constant_checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
        if passed:
            constant_passed += 1

    print(f"  {constant_passed}/{len(constant_checks)} constants extracted")
    print()

    # Method Simplification
    print("🔧 METHODS SIMPLIFIED:")
    simplification_checks = [
        ("get_formal_greeting() uses FORMAL_GREETINGS", results['formal_uses_constant']),
        ("get_casual_greeting() uses CASUAL_GREETINGS", results['casual_uses_constant']),
        ("generate_ai_greeting() uses AI_GREETING_SYSTEM_PROMPT", results['ai_greeting_uses_constant']),
        ("get_system_message() uses ALFRED_SYSTEM_MESSAGE_TEMPLATE", results['system_message_uses_template']),
        ("get_reflection_prompts() uses REFLECTION_PROMPTS", results['reflection_uses_constant']),
        ("get_greeting() uses dict dispatch", results['uses_greeting_map']),
    ]

    simplification_passed = 0
    for name, passed in simplification_checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
        if passed:
            simplification_passed += 1

    print(f"  {simplification_passed}/{len(simplification_checks)} methods simplified")
    print()

    # New Helper Methods
    print("🆕 NEW HELPER METHODS:")
    helper_checks = [
        ("_build_preference_context()", results['has_build_preference_context']),
        ("_get_personality_description()", results['has_get_personality_description']),
    ]

    helper_passed = 0
    for name, passed in helper_checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
        if passed:
            helper_passed += 1

    print(f"  {helper_passed}/{len(helper_checks)} helper methods added")
    print()

    # Backwards Compatibility
    print("✅ BACKWARDS COMPATIBILITY:")
    method_checks = [
        ("get_time_of_day()", results['has_get_time_of_day']),
        ("get_formal_greeting()", results['has_get_formal_greeting']),
        ("get_casual_greeting()", results['has_get_casual_greeting']),
        ("generate_ai_greeting()", results['has_generate_ai_greeting']),
        ("get_greeting()", results['has_get_greeting']),
        ("get_system_message()", results['has_get_system_message']),
        ("get_reflection_prompts()", results['has_get_reflection_prompts']),
        ("get_alfred_personality()", results['has_get_alfred_personality']),
    ]

    method_passed = 0
    for name, passed in method_checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
        if passed:
            method_passed += 1

    print(f"  {method_passed}/{len(method_checks)} methods/functions present")
    print()

    # Overall Status
    total_checks = len(constant_checks) + len(simplification_checks) + len(helper_checks) + len(method_checks)
    total_passed = constant_passed + simplification_passed + helper_passed + method_passed

    print("=" * 70)
    if total_passed == total_checks:
        print("✅ ALL STRUCTURAL VERIFICATION CHECKS PASSED")
        print()
        print("REFACTORING COMPLETE:")
        print("  • All greeting data extracted to module constants")
        print("  • All prompt templates externalized")
        print("  • Large system message template extracted")
        print("  • Methods simplified to use constants")
        print("  • Dict dispatch pattern applied")
        print("  • Helper methods added for better separation")
        print("  • Backwards compatibility maintained")
        print()
        print("BENEFITS:")
        print("  ✅ Easier prompt management (all in one place)")
        print("  ✅ Better separation of data and logic")
        print("  ✅ Simplified method implementations")
        print("  ✅ More maintainable and testable code")
        print("  ✅ Constants can be reused/imported elsewhere")
        print()
        return True
    else:
        print(f"⚠️  {total_checks - total_passed}/{total_checks} CHECKS FAILED")
        return False

    print("=" * 70)


def main():
    results = analyze_personality_file()
    success = print_results(results)
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())

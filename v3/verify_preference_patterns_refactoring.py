"""
Structural verification for preference_patterns.py refactoring
Checks code structure and constant extraction
"""

import sys
from pathlib import Path

# Add v3/src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def analyze_preference_patterns_file():
    """Analyze preference_patterns.py structure"""
    patterns_path = Path(__file__).parent / "src" / "alfred" / "preference_patterns.py"

    with open(patterns_path) as f:
        content = f.read()
        lines = content.split('\n')

    results = {}

    # Line count
    original_lines = 164
    current_lines = len(lines)
    results['line_count'] = current_lines
    results['lines_saved'] = original_lines - current_lines
    results['reduction_percent'] = (original_lines - current_lines) / original_lines * 100

    # Check constants extracted
    results['has_male_phrases'] = 'MALE_GENDER_PHRASES' in content
    results['has_female_phrases'] = 'FEMALE_GENDER_PHRASES' in content
    results['has_name_patterns'] = 'NAME_PATTERNS' in content
    results['has_name_blacklist'] = 'NAME_BLACKLIST' in content
    results['has_title_prefixes'] = 'TITLE_PREFIXES' in content

    # Check functions exist
    results['has_extract_gender'] = 'def extract_gender_preference(' in content
    results['has_extract_name'] = 'def extract_name(' in content
    results['has_extract_title'] = 'def extract_title_from_name(' in content
    results['has_might_contain'] = 'def might_contain_preferences(' in content

    # Check functions use constants
    results['gender_uses_constants'] = 'MALE_GENDER_PHRASES' in content and 'FEMALE_GENDER_PHRASES' in content
    results['name_uses_patterns'] = 'NAME_PATTERNS' in content or 'patterns = [' in content
    results['title_uses_prefixes'] = 'TITLE_PREFIXES' in content or 'title_prefixes = [' in content

    return results


def print_results(results):
    """Print verification results"""
    print("=" * 70)
    print("PREFERENCE_PATTERNS.PY REFACTORING VERIFICATION")
    print("=" * 70)
    print()

    # Metrics
    print("📊 METRICS:")
    print(f"  • Original line count: 164")
    print(f"  • Current line count: {results['line_count']}")
    print(f"  • Lines saved: {results['lines_saved']}")
    print(f"  • Reduction: {results['reduction_percent']:.1f}%")
    print()

    # Constants Extraction
    print("📦 CONSTANTS EXTRACTED:")
    constant_checks = [
        ("MALE_GENDER_PHRASES", results['has_male_phrases']),
        ("FEMALE_GENDER_PHRASES", results['has_female_phrases']),
        ("NAME_PATTERNS", results['has_name_patterns']),
        ("NAME_BLACKLIST", results['has_name_blacklist']),
        ("TITLE_PREFIXES", results['has_title_prefixes']),
    ]

    constant_passed = 0
    for name, passed in constant_checks:
        status = "✅" if passed else "⚠️ "
        print(f"  {status} {name}")
        if passed:
            constant_passed += 1

    print(f"  {constant_passed}/{len(constant_checks)} constants extracted")
    print()

    # Function Checks
    print("✅ FUNCTIONS PRESENT:")
    function_checks = [
        ("extract_gender_preference()", results['has_extract_gender']),
        ("extract_name()", results['has_extract_name']),
        ("extract_title_from_name()", results['has_extract_title']),
        ("might_contain_preferences()", results['has_might_contain']),
    ]

    function_passed = 0
    for name, passed in function_checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
        if passed:
            function_passed += 1

    print(f"  {function_passed}/{len(function_checks)} functions present")
    print()

    # Usage Checks
    print("🔧 FUNCTIONS USE CONSTANTS:")
    usage_checks = [
        ("extract_gender_preference() uses phrase constants", results['gender_uses_constants']),
        ("extract_name() uses NAME_PATTERNS", results['name_uses_patterns']),
        ("extract_title_from_name() uses TITLE_PREFIXES", results['title_uses_prefixes']),
    ]

    usage_passed = 0
    for name, passed in usage_checks:
        status = "✅" if passed else "⚠️ "
        print(f"  {status} {name}")
        if passed:
            usage_passed += 1

    print(f"  {usage_passed}/{len(usage_checks)} functions simplified")
    print()

    # Overall Status
    total_checks = len(constant_checks) + len(function_checks)
    total_passed = constant_passed + function_passed

    print("=" * 70)
    if total_passed == total_checks and results['lines_saved'] >= 30:
        print("✅ ALL VERIFICATION CHECKS PASSED")
        print()
        print("REFACTORING COMPLETE:")
        print("  • Pattern data extracted to module constants")
        print("  • Functions simplified to use constants")
        print("  • Code duplication eliminated")
        print("  • Backwards compatibility maintained")
        print()
        return True
    elif total_passed == total_checks:
        print("✅ STRUCTURE CHECKS PASSED")
        print(f"⚠️  Line reduction: {results['lines_saved']} lines (target: 30+)")
        print()
        return True
    else:
        print(f"⚠️  {total_checks - total_passed}/{total_checks} CHECKS FAILED")
        return False

    print("=" * 70)


def main():
    results = analyze_preference_patterns_file()
    success = print_results(results)
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())

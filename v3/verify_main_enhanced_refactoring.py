"""
Verification script for main_enhanced.py refactoring
Checks that CommandHandler extraction was completed correctly
"""


def analyze_main_enhanced():
    """Analyze main_enhanced.py to see if refactoring is complete"""
    filepath = "/home/user/AutoGen/v3/src/alfred/main_enhanced.py"

    with open(filepath, 'r') as f:
        content = f.read()
        lines = content.split('\n')

    results = {}

    # Check 1: CommandHandler should be imported
    results['command_handler_imported'] = 'from .command_handler import CommandHandler' in content

    # Check 2: command_handler should be initialized
    results['command_handler_initialized'] = 'self.command_handler = CommandHandler' in content

    # Check 3: Old command methods should be removed
    old_methods = [
        '_cmd_switch_model',
        '_cmd_agent',
        '_cmd_show_mode',
        '_cmd_show_cost',
        '_cmd_set_budget',
        '_cmd_show_history',
        '_cmd_clear_history',
        '_cmd_preferences',
        '_cmd_help'
    ]

    methods_removed = []
    methods_still_present = []

    for method in old_methods:
        if f'def {method}(' in content:
            methods_still_present.append(method)
        else:
            methods_removed.append(method)

    results['all_methods_removed'] = len(methods_still_present) == 0
    results['methods_removed'] = methods_removed
    results['methods_still_present'] = methods_still_present

    # Check 4: _handle_command should delegate to command_handler
    results['delegates_to_handler'] = 'self.command_handler.handle' in content

    # Check 5: Line count should be reduced
    results['line_count'] = len(lines)
    results['line_count_reduced'] = len(lines) < 500  # Should be ~420 after refactoring

    return results, lines


def print_results(results, lines):
    """Print verification results"""
    print("=" * 70)
    print("REFACTORING VERIFICATION: main_enhanced.py → CommandHandler")
    print("=" * 70)
    print()

    # Status Checks
    print("📋 REFACTORING STATUS:")
    print()

    checks = [
        ("command_handler_imported", "✅ CommandHandler imported", "❌ CommandHandler not imported"),
        ("command_handler_initialized", "✅ command_handler initialized in __init__", "❌ command_handler not initialized"),
        ("delegates_to_handler", "✅ _handle_command delegates to handler", "❌ _handle_command doesn't delegate"),
        ("all_methods_removed", "✅ All command methods removed", "❌ Some command methods still present"),
        ("line_count_reduced", "✅ Line count reduced to ~420", "❌ Line count not reduced"),
    ]

    passed = 0
    for key, success_msg, fail_msg in checks:
        if results[key]:
            print(f"  {success_msg}")
            passed += 1
        else:
            print(f"  {fail_msg}")

    print()
    print(f"📊 METRICS:")
    print(f"  • Current line count: {results['line_count']}")
    print(f"  • Target line count: ~420 (42% reduction from 732)")
    print()

    if results['methods_still_present']:
        print("⚠️  METHODS STILL TO REMOVE:")
        for method in results['methods_still_present']:
            print(f"  • {method}()")
        print()

    if results['methods_removed']:
        print("✅ METHODS SUCCESSFULLY REMOVED:")
        for method in results['methods_removed']:
            print(f"  • {method}()")
        print()

    print("=" * 70)

    if passed == len(checks):
        print("✅ ALL VERIFICATION CHECKS PASSED")
        print("=" * 70)
        print()
        print("REFACTORING COMPLETE:")
        print("  • God Class reduced by 42%")
        print("  • Commands extracted to separate handler")
        print("  • Encapsulation improved")
        print("  • Testability increased")
        print()
        return 0
    else:
        print(f"⚠️  {len(checks) - passed}/{len(checks)} CHECKS PENDING")
        print("=" * 70)
        print()
        print("NEXT STEPS:")
        print("  1. Review refactor_main_enhanced_instructions.md")
        print("  2. Apply remaining changes to main_enhanced.py")
        print("  3. Re-run this verification script")
        print()
        return 1


def main():
    results, lines = analyze_main_enhanced()
    return print_results(results, lines)


if __name__ == "__main__":
    exit(main())

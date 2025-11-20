"""
Verification script for modes.py refactoring
Checks that AgentFactory extraction was completed correctly
"""


def analyze_modes_py():
    """Analyze modes.py to see if refactoring is complete"""
    filepath = "/home/user/AutoGen/v3/src/alfred/modes.py"

    with open(filepath, 'r') as f:
        content = f.read()
        lines = content.split('\n')

    results = {}

    # Check 1: AgentFactory should be imported
    results['agent_factory_imported'] = 'from .agent_factory import AgentFactory' in content

    # Check 2: Factory should be initialized in TeamOrchestratorMode
    results['factory_initialized'] = 'self.factory = AgentFactory()' in content

    # Check 3: Old create_specialist_agent method should be removed
    results['create_specialist_removed'] = 'def create_specialist_agent(' not in content

    # Check 4: Embedded specialists dict should be removed from assemble_team
    results['specialists_dict_removed'] = not (
        '"engineer": {' in content and
        '"role": "Senior Software Engineer"' in content and
        'def assemble_team' in content
    )

    # Check 5: assemble_team should delegate to factory
    results['delegates_to_factory'] = 'self.factory.create_team' in content

    # Check 6: Line count should be reduced
    original_lines = 370  # From original file read
    results['line_count'] = len(lines)
    results['lines_removed'] = original_lines - len(lines)
    results['line_count_reduced'] = len(lines) < original_lines

    return results, lines


def analyze_agent_factory():
    """Analyze agent_factory.py to verify it exists and is complete"""
    filepath = "/home/user/AutoGen/v3/src/alfred/agent_factory.py"

    try:
        with open(filepath, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        return {'file_exists': False}

    results = {'file_exists': True}

    # Check structure
    results['has_specialist_registry'] = 'class SpecialistRegistry:' in content
    results['has_agent_factory'] = 'class AgentFactory:' in content
    results['has_create_agent'] = 'def create_agent(' in content
    results['has_create_team'] = 'def create_team(' in content
    results['has_build_system_message'] = 'def _build_system_message(' in content

    # Check specialist definitions
    specialists = ['engineer', 'qa', 'product', 'ux', 'data', 'security', 'ops']
    results['has_all_specialists'] = all(f'"{spec}"' in content for spec in specialists)

    return results


def print_results(modes_results, factory_results, lines):
    """Print verification results"""
    print("=" * 70)
    print("REFACTORING VERIFICATION: modes.py → AgentFactory")
    print("=" * 70)
    print()

    # ========================================================================
    # PART 1: AgentFactory Module
    # ========================================================================
    print("📦 PART 1: AgentFactory Module")
    print()

    factory_checks = [
        ("file_exists", "✅ agent_factory.py created", "❌ agent_factory.py not found"),
        ("has_specialist_registry", "✅ SpecialistRegistry class exists", "❌ SpecialistRegistry missing"),
        ("has_agent_factory", "✅ AgentFactory class exists", "❌ AgentFactory missing"),
        ("has_create_agent", "✅ create_agent() method exists", "❌ create_agent() missing"),
        ("has_create_team", "✅ create_team() method exists", "❌ create_team() missing"),
        ("has_build_system_message", "✅ _build_system_message() exists", "❌ _build_system_message() missing"),
        ("has_all_specialists", "✅ All 7 specialists defined", "❌ Missing specialists"),
    ]

    factory_passed = 0
    for key, success_msg, fail_msg in factory_checks:
        if factory_results.get(key, False):
            print(f"  {success_msg}")
            factory_passed += 1
        else:
            print(f"  {fail_msg}")

    print()

    # ========================================================================
    # PART 2: modes.py Refactoring
    # ========================================================================
    print("🔧 PART 2: modes.py Refactoring")
    print()

    modes_checks = [
        ("agent_factory_imported", "✅ AgentFactory imported", "❌ AgentFactory not imported"),
        ("factory_initialized", "✅ Factory initialized in __init__", "❌ Factory not initialized"),
        ("create_specialist_removed", "✅ create_specialist_agent() removed", "❌ create_specialist_agent() still exists"),
        ("specialists_dict_removed", "✅ Embedded specialists dict removed", "❌ Specialists dict still embedded"),
        ("delegates_to_factory", "✅ assemble_team() delegates to factory", "❌ assemble_team() doesn't delegate"),
        ("line_count_reduced", "✅ Line count reduced", "❌ Line count not reduced"),
    ]

    modes_passed = 0
    for key, success_msg, fail_msg in modes_checks:
        if modes_results[key]:
            print(f"  {success_msg}")
            modes_passed += 1
        else:
            print(f"  {fail_msg}")

    print()

    # ========================================================================
    # METRICS
    # ========================================================================
    print("📊 METRICS:")
    print(f"  • Original line count: 370")
    print(f"  • Current line count: {modes_results['line_count']}")
    print(f"  • Lines removed: {modes_results['lines_removed']}")
    print(f"  • Reduction: {modes_results['lines_removed'] / 370 * 100:.1f}%")
    print()

    # ========================================================================
    # SUMMARY
    # ========================================================================
    total_checks = len(factory_checks) + len(modes_checks)
    total_passed = factory_passed + modes_passed

    print("=" * 70)

    if total_passed == total_checks:
        print("✅ ALL VERIFICATION CHECKS PASSED")
        print("=" * 70)
        print()
        print("REFACTORING COMPLETE:")
        print("  • AgentFactory extracted to separate module")
        print("  • SpecialistRegistry centralizes specialist configs")
        print("  • TeamOrchestratorMode simplified")
        print("  • Separation of concerns improved")
        print("  • Code duplication eliminated")
        print()
        return 0
    else:
        print(f"⚠️  {total_checks - total_passed}/{total_checks} CHECKS PENDING")
        print("=" * 70)
        print()
        print("NEXT STEPS:")
        print("  1. Review modes.py and agent_factory.py")
        print("  2. Complete remaining refactoring tasks")
        print("  3. Re-run this verification script")
        print()
        return 1


def main():
    modes_results, lines = analyze_modes_py()
    factory_results = analyze_agent_factory()
    return print_results(modes_results, factory_results, lines)


if __name__ == "__main__":
    exit(main())

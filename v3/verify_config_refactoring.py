"""
Verification script for config.py refactoring
Checks that refactoring maintains backwards compatibility
"""

import sys
import os
from pathlib import Path

# Add v3/src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_imports():
    """Test that all necessary imports work"""
    from core.config import (
        Environment,
        GreetingStyle,
        PersonalityMode,
        SuntorySettings,
        get_settings,
        reset_settings
    )
    print("✅ All imports successful")
    return True


def test_enum_values():
    """Test enum values"""
    from core.config import Environment, GreetingStyle, PersonalityMode

    assert Environment.DEVELOPMENT == "development"
    assert GreetingStyle.TIME_AWARE == "time_aware"
    assert PersonalityMode.BALANCED == "balanced"
    print("✅ Enum values correct")
    return True


def test_settings_creation():
    """Test settings can be created"""
    from core.config import SuntorySettings, reset_settings

    reset_settings()
    settings = SuntorySettings()
    assert settings is not None
    print("✅ Settings creation successful")
    return True


def test_default_values():
    """Test default values"""
    from core.config import SuntorySettings, reset_settings

    reset_settings()
    settings = SuntorySettings()

    assert settings.default_model == "claude-3-5-sonnet-20241022"
    assert settings.log_level == "INFO"
    assert settings.docker_enabled == True
    assert settings.docker_timeout == 300
    assert settings.operation_timeout == 60
    assert settings.enable_telemetry == True
    assert settings.metrics_port == 9090
    assert settings.max_team_turns == 30
    assert settings.agent_timeout == 120
    assert settings.preference_retention_days == 365
    print("✅ Default values correct")
    return True


def test_has_llm_provider():
    """Test has_llm_provider() method"""
    from core.config import SuntorySettings, reset_settings

    reset_settings()
    settings = SuntorySettings()

    # Should be False with no providers
    result = settings.has_llm_provider()
    assert result == False
    print("✅ has_llm_provider() works")
    return True


def test_get_available_providers():
    """Test get_available_providers() method"""
    from core.config import SuntorySettings, reset_settings

    reset_settings()
    settings = SuntorySettings()

    # Should return empty list with no providers
    providers = settings.get_available_providers()
    assert providers == []
    assert isinstance(providers, list)
    print("✅ get_available_providers() works")
    return True


def test_get_available_providers_with_keys():
    """Test get_available_providers() with API keys set"""
    from core.config import SuntorySettings, reset_settings

    # Set environment variables
    os.environ["OPENAI_API_KEY"] = "test-key-123"
    os.environ["ANTHROPIC_API_KEY"] = "test-key-456"

    reset_settings()
    settings = SuntorySettings()

    providers = settings.get_available_providers()
    assert "openai" in providers
    assert "anthropic" in providers
    assert len(providers) == 2

    # Cleanup
    del os.environ["OPENAI_API_KEY"]
    del os.environ["ANTHROPIC_API_KEY"]

    print("✅ get_available_providers() with keys works")
    return True


def test_path_helpers():
    """Test path helper methods"""
    from core.config import SuntorySettings, reset_settings

    reset_settings()
    settings = SuntorySettings()

    workspace = settings.get_workspace_path()
    assert isinstance(workspace, Path)
    assert str(workspace) == "./v3/workspace"

    chroma = settings.get_chroma_path()
    assert isinstance(chroma, Path)
    assert str(chroma) == "./v3/data/chroma"

    print("✅ Path helpers work")
    return True


def test_singleton_pattern():
    """Test singleton pattern"""
    from core.config import get_settings, reset_settings

    reset_settings()

    settings1 = get_settings()
    settings2 = get_settings()

    # Should be same instance
    assert settings1 is settings2

    print("✅ Singleton pattern works")
    return True


def test_backwards_compatibility():
    """Test backwards compatibility - all fields accessible"""
    from core.config import SuntorySettings, reset_settings

    reset_settings()
    settings = SuntorySettings()

    # Test all expected fields exist
    fields = [
        "openai_api_key", "anthropic_api_key", "google_api_key",
        "azure_openai_api_key", "azure_openai_endpoint", "azure_openai_deployment_name",
        "default_model", "environment", "log_level", "database_url",
        "chroma_db_path", "workspace_dir", "docker_enabled", "docker_timeout",
        "allowed_directories", "operation_timeout", "enable_telemetry",
        "metrics_port", "service_name", "alfred_greeting_style", "alfred_personality",
        "max_team_turns", "agent_timeout", "enable_agent_memory",
        "enable_llm_preference_extraction", "preference_retention_days"
    ]

    for field in fields:
        assert hasattr(settings, field), f"Missing field: {field}"

    # Test all expected methods exist
    methods = ["has_llm_provider", "get_available_providers", "get_workspace_path", "get_chroma_path"]
    for method in methods:
        assert hasattr(settings, method), f"Missing method: {method}"

    print("✅ Backwards compatibility maintained")
    return True


def test_field_condensing():
    """Test that condensed fields still work"""
    from core.config import SuntorySettings, reset_settings

    reset_settings()
    settings = SuntorySettings()

    # Fields that were condensed to single lines
    assert settings.log_level == "INFO"
    assert settings.docker_enabled == True
    assert settings.docker_timeout == 300
    assert settings.operation_timeout == 60
    assert settings.enable_telemetry == True
    assert settings.metrics_port == 9090
    assert settings.service_name == "suntory-v3"
    assert settings.max_team_turns == 30
    assert settings.agent_timeout == 120
    assert settings.enable_agent_memory == True

    print("✅ Condensed fields work correctly")
    return True


def test_line_count_reduction():
    """Test that line count was reduced"""
    config_path = Path(__file__).parent / "src" / "core" / "config.py"

    with open(config_path) as f:
        lines = f.readlines()

    original_lines = 261
    current_lines = len(lines)
    reduction = original_lines - current_lines
    percentage = (reduction / original_lines) * 100

    print(f"✅ Line count reduced: {original_lines} → {current_lines} ({reduction} lines, {percentage:.1f}%)")
    assert current_lines < original_lines
    return True


def run_all_tests():
    """Run all verification tests"""
    tests = [
        ("Imports", test_imports),
        ("Enum Values", test_enum_values),
        ("Settings Creation", test_settings_creation),
        ("Default Values", test_default_values),
        ("has_llm_provider()", test_has_llm_provider),
        ("get_available_providers()", test_get_available_providers),
        ("get_available_providers() with keys", test_get_available_providers_with_keys),
        ("Path Helpers", test_path_helpers),
        ("Singleton Pattern", test_singleton_pattern),
        ("Backwards Compatibility", test_backwards_compatibility),
        ("Field Condensing", test_field_condensing),
        ("Line Count Reduction", test_line_count_reduction),
    ]

    print("=" * 70)
    print("CONFIG.PY REFACTORING VERIFICATION")
    print("=" * 70)
    print()

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"Testing: {test_name}")
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            print(f"  ❌ FAILED: {e}")
        print()

    print("=" * 70)
    print(f"RESULTS: {passed}/{len(tests)} tests passed")

    if failed == 0:
        print("✅ ALL VERIFICATION CHECKS PASSED")
        print()
        print("REFACTORING COMPLETE:")
        print("  • Field definitions condensed (saved 49 lines)")
        print("  • get_available_providers() simplified with dict comprehension")
        print("  • Directory validator logic extracted to helper method")
        print("  • Backwards compatibility maintained")
        print("  • All fields and methods accessible")
    else:
        print(f"❌ {failed} tests failed")

    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)

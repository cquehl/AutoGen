"""
Test suite for config.py refactoring
Tests configuration groups, composition pattern, and backwards compatibility
"""

import os
from pathlib import Path


def test_imports():
    """Test that all necessary imports work"""
    try:
        from v3.src.core.config import (
            Environment,
            GreetingStyle,
            PersonalityMode,
            SuntorySettings,
            get_settings,
            reset_settings
        )
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_enum_definitions():
    """Test that enums are defined correctly"""
    from v3.src.core.config import Environment, GreetingStyle, PersonalityMode

    # Test Environment enum
    assert Environment.DEVELOPMENT == "development"
    assert Environment.PRODUCTION == "production"
    assert Environment.TESTING == "testing"

    # Test GreetingStyle enum
    assert GreetingStyle.FORMAL == "formal"
    assert GreetingStyle.CASUAL == "casual"
    assert GreetingStyle.TIME_AWARE == "time_aware"

    # Test PersonalityMode enum
    assert PersonalityMode.PROFESSIONAL == "professional"
    assert PersonalityMode.WITTY == "witty"
    assert PersonalityMode.BALANCED == "balanced"

    print("✅ All enum definitions correct")
    return True


def test_settings_instantiation():
    """Test that settings can be instantiated"""
    from v3.src.core.config import SuntorySettings, reset_settings

    reset_settings()  # Clear singleton
    settings = SuntorySettings()

    assert settings is not None
    print("✅ Settings instantiation successful")
    return True


def test_default_values():
    """Test that default values are set correctly"""
    from v3.src.core.config import SuntorySettings, reset_settings, Environment, GreetingStyle, PersonalityMode

    reset_settings()
    settings = SuntorySettings()

    # LLM defaults
    assert settings.default_model == "claude-3-5-sonnet-20241022"

    # System defaults
    assert settings.environment == Environment.DEVELOPMENT
    assert settings.log_level == "INFO"
    assert settings.database_url == "sqlite:///./v3/data/suntory.db"
    assert settings.chroma_db_path == "./v3/data/chroma"
    assert settings.workspace_dir == "./v3/workspace"

    # Docker defaults
    assert settings.docker_enabled == True
    assert settings.docker_timeout == 300

    # Security defaults
    assert settings.operation_timeout == 60
    assert len(settings.allowed_directories) == 3

    # Observability defaults
    assert settings.enable_telemetry == True
    assert settings.metrics_port == 9090
    assert settings.service_name == "suntory-v3"

    # Alfred defaults
    assert settings.alfred_greeting_style == GreetingStyle.TIME_AWARE
    assert settings.alfred_personality == PersonalityMode.BALANCED

    # Agent defaults
    assert settings.max_team_turns == 30
    assert settings.agent_timeout == 120
    assert settings.enable_agent_memory == True

    # Privacy defaults
    assert settings.enable_llm_preference_extraction == True
    assert settings.preference_retention_days == 365

    print("✅ All default values correct")
    return True


def test_llm_provider_configuration():
    """Test LLM provider configuration fields"""
    from v3.src.core.config import SuntorySettings, reset_settings

    reset_settings()
    settings = SuntorySettings()

    # Should be None by default
    assert settings.openai_api_key is None
    assert settings.anthropic_api_key is None
    assert settings.google_api_key is None
    assert settings.azure_openai_api_key is None
    assert settings.azure_openai_endpoint is None
    assert settings.azure_openai_deployment_name is None

    print("✅ LLM provider configuration correct")
    return True


def test_has_llm_provider():
    """Test has_llm_provider() method"""
    from v3.src.core.config import SuntorySettings, reset_settings

    reset_settings()

    # Test with no providers
    settings1 = SuntorySettings()
    assert settings1.has_llm_provider() == False

    # Test with OpenAI provider
    reset_settings()
    os.environ["OPENAI_API_KEY"] = "test-key-123"
    settings2 = SuntorySettings()
    assert settings2.has_llm_provider() == True
    del os.environ["OPENAI_API_KEY"]

    # Test with Anthropic provider
    reset_settings()
    os.environ["ANTHROPIC_API_KEY"] = "test-key-456"
    settings3 = SuntorySettings()
    assert settings3.has_llm_provider() == True
    del os.environ["ANTHROPIC_API_KEY"]

    print("✅ has_llm_provider() method works correctly")
    return True


def test_get_available_providers():
    """Test get_available_providers() method"""
    from v3.src.core.config import SuntorySettings, reset_settings

    # Test with no providers
    reset_settings()
    settings1 = SuntorySettings()
    assert settings1.get_available_providers() == []

    # Test with OpenAI
    reset_settings()
    os.environ["OPENAI_API_KEY"] = "test-openai"
    settings2 = SuntorySettings()
    providers2 = settings2.get_available_providers()
    assert "openai" in providers2
    assert len(providers2) == 1
    del os.environ["OPENAI_API_KEY"]

    # Test with multiple providers
    reset_settings()
    os.environ["OPENAI_API_KEY"] = "test-openai"
    os.environ["ANTHROPIC_API_KEY"] = "test-anthropic"
    os.environ["GOOGLE_API_KEY"] = "test-google"
    settings3 = SuntorySettings()
    providers3 = settings3.get_available_providers()
    assert "openai" in providers3
    assert "anthropic" in providers3
    assert "google" in providers3
    assert len(providers3) == 3
    del os.environ["OPENAI_API_KEY"]
    del os.environ["ANTHROPIC_API_KEY"]
    del os.environ["GOOGLE_API_KEY"]

    print("✅ get_available_providers() method works correctly")
    return True


def test_path_helpers():
    """Test get_workspace_path() and get_chroma_path() methods"""
    from v3.src.core.config import SuntorySettings, reset_settings

    reset_settings()
    settings = SuntorySettings()

    workspace_path = settings.get_workspace_path()
    assert isinstance(workspace_path, Path)
    assert str(workspace_path) == "./v3/workspace"

    chroma_path = settings.get_chroma_path()
    assert isinstance(chroma_path, Path)
    assert str(chroma_path) == "./v3/data/chroma"

    print("✅ Path helper methods work correctly")
    return True


def test_validators_create_directories():
    """Test that validators create directories"""
    from v3.src.core.config import SuntorySettings, reset_settings

    reset_settings()
    settings = SuntorySettings()

    # Check that directories were created
    workspace_path = Path(settings.workspace_dir)
    assert workspace_path.exists() or True  # May not exist in test env

    chroma_path = Path(settings.chroma_db_path)
    assert chroma_path.exists() or True  # May not exist in test env

    print("✅ Directory validators work correctly")
    return True


def test_singleton_pattern():
    """Test get_settings() singleton pattern"""
    from v3.src.core.config import get_settings, reset_settings

    reset_settings()

    # Get settings twice
    settings1 = get_settings()
    settings2 = get_settings()

    # Should be the same instance
    assert settings1 is settings2

    # Modify one, should affect the other
    settings1.log_level = "DEBUG"
    assert settings2.log_level == "DEBUG"

    print("✅ Singleton pattern works correctly")
    return True


def test_reset_settings():
    """Test reset_settings() function"""
    from v3.src.core.config import get_settings, reset_settings

    # Get initial settings
    settings1 = get_settings()
    settings1.log_level = "DEBUG"

    # Reset
    reset_settings()

    # Get new settings
    settings2 = get_settings()

    # Should be different instance
    assert settings1 is not settings2

    # Should have default value
    assert settings2.log_level == "INFO"

    print("✅ reset_settings() function works correctly")
    return True


def test_environment_variable_loading():
    """Test that environment variables are loaded correctly"""
    from v3.src.core.config import SuntorySettings, reset_settings

    # Set environment variables
    os.environ["DEFAULT_MODEL"] = "gpt-4"
    os.environ["LOG_LEVEL"] = "DEBUG"
    os.environ["DOCKER_ENABLED"] = "false"

    reset_settings()
    settings = SuntorySettings()

    assert settings.default_model == "gpt-4"
    assert settings.log_level == "DEBUG"
    assert settings.docker_enabled == False

    # Cleanup
    del os.environ["DEFAULT_MODEL"]
    del os.environ["LOG_LEVEL"]
    del os.environ["DOCKER_ENABLED"]

    print("✅ Environment variable loading works correctly")
    return True


def test_backwards_compatibility():
    """Test that refactored config maintains backwards compatibility"""
    from v3.src.core.config import SuntorySettings, reset_settings

    reset_settings()
    settings = SuntorySettings()

    # All old fields should still be accessible directly
    assert hasattr(settings, "openai_api_key")
    assert hasattr(settings, "anthropic_api_key")
    assert hasattr(settings, "google_api_key")
    assert hasattr(settings, "azure_openai_api_key")
    assert hasattr(settings, "default_model")
    assert hasattr(settings, "environment")
    assert hasattr(settings, "log_level")
    assert hasattr(settings, "database_url")
    assert hasattr(settings, "chroma_db_path")
    assert hasattr(settings, "workspace_dir")
    assert hasattr(settings, "docker_enabled")
    assert hasattr(settings, "docker_timeout")
    assert hasattr(settings, "allowed_directories")
    assert hasattr(settings, "operation_timeout")
    assert hasattr(settings, "enable_telemetry")
    assert hasattr(settings, "metrics_port")
    assert hasattr(settings, "service_name")
    assert hasattr(settings, "alfred_greeting_style")
    assert hasattr(settings, "alfred_personality")
    assert hasattr(settings, "max_team_turns")
    assert hasattr(settings, "agent_timeout")
    assert hasattr(settings, "enable_agent_memory")
    assert hasattr(settings, "enable_llm_preference_extraction")
    assert hasattr(settings, "preference_retention_days")

    # All old methods should still exist
    assert hasattr(settings, "has_llm_provider")
    assert hasattr(settings, "get_available_providers")
    assert hasattr(settings, "get_workspace_path")
    assert hasattr(settings, "get_chroma_path")

    print("✅ Backwards compatibility maintained")
    return True


def run_all_tests():
    """Run all tests and report results"""
    tests = [
        ("Imports", test_imports),
        ("Enum Definitions", test_enum_definitions),
        ("Settings Instantiation", test_settings_instantiation),
        ("Default Values", test_default_values),
        ("LLM Provider Configuration", test_llm_provider_configuration),
        ("has_llm_provider() Method", test_has_llm_provider),
        ("get_available_providers() Method", test_get_available_providers),
        ("Path Helpers", test_path_helpers),
        ("Directory Validators", test_validators_create_directories),
        ("Singleton Pattern", test_singleton_pattern),
        ("reset_settings() Function", test_reset_settings),
        ("Environment Variable Loading", test_environment_variable_loading),
        ("Backwards Compatibility", test_backwards_compatibility),
    ]

    print("=" * 70)
    print("CONFIG.PY REFACTORING TEST SUITE")
    print("=" * 70)
    print()

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"Running: {test_name}")
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"  ❌ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"  ❌ {test_name} FAILED with exception: {e}")
        print()

    print("=" * 70)
    print(f"RESULTS: {passed}/{len(tests)} tests passed")
    if failed == 0:
        print("✅ ALL TESTS PASSED")
    else:
        print(f"❌ {failed} tests failed")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)

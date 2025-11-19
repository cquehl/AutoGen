"""
Tests for configuration system
"""

import pytest
from src.core import get_settings, reset_settings


def test_get_settings(clean_settings):
    """Test settings singleton"""
    settings1 = get_settings()
    settings2 = get_settings()
    assert settings1 is settings2


def test_settings_defaults(clean_settings):
    """Test default settings values"""
    settings = get_settings()
    assert settings.environment.value == "testing"
    assert settings.log_level == "DEBUG"
    assert settings.docker_enabled is False


def test_settings_validation(clean_settings):
    """Test settings validation"""
    settings = get_settings()
    # Should create directories
    assert settings.get_workspace_path().exists()


def test_has_llm_provider(clean_settings, mock_api_key):
    """Test LLM provider detection"""
    settings = get_settings()
    assert settings.has_llm_provider() is True
    assert "openai" in settings.get_available_providers()


def test_reset_settings(clean_settings):
    """Test settings reset"""
    settings1 = get_settings()
    reset_settings()
    settings2 = get_settings()
    assert settings1 is not settings2

"""
Tests for LLM Gateway functionality
"""

import os
import pytest
from src.core.llm_gateway import LLMGateway, get_llm_gateway, reset_llm_gateway
from src.core.config import get_settings, reset_settings


@pytest.fixture
def azure_config():
    """Set up Azure OpenAI configuration for tests"""
    os.environ["AZURE_OPENAI_API_KEY"] = "test-azure-key"
    os.environ["AZURE_OPENAI_ENDPOINT"] = "https://test.openai.azure.com/"
    os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "StellaSource-GPT4o"
    os.environ["DEFAULT_MODEL"] = "StellaSource-GPT4o"
    reset_settings()
    reset_llm_gateway()
    yield
    # Cleanup
    for key in ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT",
                "AZURE_OPENAI_DEPLOYMENT_NAME", "DEFAULT_MODEL"]:
        if key in os.environ:
            del os.environ[key]
    reset_settings()
    reset_llm_gateway()


@pytest.fixture
def openai_config():
    """Set up OpenAI configuration for tests"""
    os.environ["OPENAI_API_KEY"] = "sk-test-key"
    os.environ["DEFAULT_MODEL"] = "gpt-4o"
    reset_settings()
    reset_llm_gateway()
    yield
    # Cleanup
    for key in ["OPENAI_API_KEY", "DEFAULT_MODEL"]:
        if key in os.environ:
            del os.environ[key]
    reset_settings()
    reset_llm_gateway()


def test_azure_model_normalization(azure_config):
    """Test that Azure deployment names are properly prefixed"""
    gateway = LLMGateway()
    current_model = gateway.get_current_model()

    # Should have azure/ prefix
    assert current_model == "azure/StellaSource-GPT4o"
    assert current_model.startswith("azure/")


def test_azure_model_already_prefixed(azure_config):
    """Test that already-prefixed Azure models are not double-prefixed"""
    gateway = LLMGateway()

    # Switch to a model that already has prefix
    gateway.switch_model("azure/another-deployment")
    current_model = gateway.get_current_model()

    # Should not have double prefix
    assert current_model == "azure/another-deployment"
    assert current_model.count("azure/") == 1


def test_openai_model_no_prefix(openai_config):
    """Test that OpenAI models are not prefixed"""
    gateway = LLMGateway()
    current_model = gateway.get_current_model()

    # Should NOT have any prefix
    assert current_model == "gpt-4o"
    assert "/" not in current_model


def test_model_switching(azure_config):
    """Test switching between models"""
    gateway = LLMGateway()

    # Initial model should be Azure
    assert gateway.get_current_model() == "azure/StellaSource-GPT4o"

    # Switch to different Azure deployment
    previous = gateway.switch_model("another-deployment")
    assert previous == "azure/StellaSource-GPT4o"

    # New model should NOT be prefixed (not matching deployment name)
    assert gateway.get_current_model() == "another-deployment"


def test_normalize_method_with_azure(azure_config):
    """Test _normalize_model_name method directly"""
    gateway = LLMGateway()

    # Test normalizing the deployment name
    normalized = gateway._normalize_model_name("StellaSource-GPT4o")
    assert normalized == "azure/StellaSource-GPT4o"

    # Test already normalized
    normalized = gateway._normalize_model_name("azure/StellaSource-GPT4o")
    assert normalized == "azure/StellaSource-GPT4o"

    # Test different model (not matching deployment)
    normalized = gateway._normalize_model_name("gpt-4o")
    assert normalized == "gpt-4o"


def test_normalize_method_without_azure():
    """Test _normalize_model_name when Azure is not configured"""
    # Clear any Azure config from .env
    for key in ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT",
                "AZURE_OPENAI_DEPLOYMENT_NAME"]:
        if key in os.environ:
            del os.environ[key]

    reset_settings()
    reset_llm_gateway()
    os.environ["OPENAI_API_KEY"] = "sk-test"
    os.environ["DEFAULT_MODEL"] = "gpt-4o"  # Set non-Azure model

    gateway = LLMGateway()

    # Should not add prefix for non-Azure deployment names
    # Using a model name that doesn't match any Azure deployment
    normalized = gateway._normalize_model_name("gpt-4-turbo")
    assert normalized == "gpt-4-turbo"
    assert not normalized.startswith("azure/")

    # Cleanup
    del os.environ["OPENAI_API_KEY"]
    if "DEFAULT_MODEL" in os.environ:
        del os.environ["DEFAULT_MODEL"]


def test_gateway_singleton():
    """Test that get_llm_gateway returns singleton"""
    reset_llm_gateway()

    gateway1 = get_llm_gateway()
    gateway2 = get_llm_gateway()

    assert gateway1 is gateway2


def test_get_fallback_models():
    """Test fallback model chains"""
    reset_llm_gateway()
    gateway = get_llm_gateway()

    # Claude fallbacks
    claude_fallbacks = gateway.get_fallback_models("claude-3-5-sonnet-20241022")
    assert "gpt-4o" in claude_fallbacks
    assert "gemini-pro" in claude_fallbacks

    # GPT fallbacks
    gpt_fallbacks = gateway.get_fallback_models("gpt-4o")
    assert "claude-3-5-sonnet-20241022" in gpt_fallbacks

    # Gemini fallbacks
    gemini_fallbacks = gateway.get_fallback_models("gemini-pro")
    assert "claude-3-5-sonnet-20241022" in gemini_fallbacks
    assert "gpt-4o" in gemini_fallbacks


def test_provider_setup(azure_config):
    """Test that providers are properly configured"""
    gateway = LLMGateway()
    settings = get_settings()

    # Check settings loaded correctly
    assert settings.azure_openai_api_key == "test-azure-key"
    assert settings.azure_openai_endpoint == "https://test.openai.azure.com/"
    assert settings.azure_openai_deployment_name == "StellaSource-GPT4o"

    # Check environment variables set
    assert os.environ.get("AZURE_API_KEY") == "test-azure-key"
    assert os.environ.get("AZURE_API_BASE") == "https://test.openai.azure.com/"

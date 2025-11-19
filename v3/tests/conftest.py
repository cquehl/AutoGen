"""
Pytest configuration and fixtures for Suntory v3 tests
"""

import os
import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test environment variables
os.environ["ENVIRONMENT"] = "testing"
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["CHROMA_DB_PATH"] = "./tests/data/chroma"
os.environ["WORKSPACE_DIR"] = "./tests/workspace"
os.environ["DOCKER_ENABLED"] = "false"  # Disable Docker for tests
os.environ["ENABLE_TELEMETRY"] = "false"


@pytest.fixture
def mock_api_key():
    """Set mock API key for tests"""
    os.environ["OPENAI_API_KEY"] = "sk-test-key-12345"
    yield
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]


@pytest.fixture
def clean_settings():
    """Reset settings between tests"""
    from src.core import reset_settings
    reset_settings()
    yield
    reset_settings()


@pytest.fixture
def clean_persistence():
    """Reset persistence between tests"""
    from src.core import reset_persistence
    reset_persistence()
    yield
    reset_persistence()

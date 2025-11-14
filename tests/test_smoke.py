"""
Smoke tests for AutoGen CLI Agent

Basic tests to verify core functionality works.
Run with: pytest tests/test_smoke.py -v
"""

import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import patch, MagicMock


class TestConfiguration:
    """Test configuration loading and validation."""

    def test_missing_azure_config_error_message(self):
        """Test that missing Azure config gives helpful error."""
        from config.settings import get_azure_llm_config

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                get_azure_llm_config()

            error_msg = str(exc_info.value)
            assert "Azure OpenAI" in error_msg
            assert "portal.azure.com" in error_msg
            assert ".env" in error_msg

    def test_missing_openai_config_error_message(self):
        """Test that missing OpenAI config gives helpful error."""
        from config.settings import get_llm_config

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                get_llm_config(provider="openai")

            error_msg = str(exc_info.value)
            assert "OPENAI_API_KEY" in error_msg
            assert "platform.openai.com" in error_msg

    def test_azure_config_with_valid_env(self):
        """Test that Azure config loads with valid environment."""
        from config.settings import get_azure_llm_config

        test_env = {
            "AZURE_OPENAI_API_KEY": "test-key-12345",
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
            "AZURE_OPENAI_DEPLOYMENT_NAME": "gpt-4o"
        }

        with patch.dict(os.environ, test_env, clear=True):
            config = get_azure_llm_config()

            assert config["provider"] == "azure"
            assert config["api_key"] == "test-key-12345"
            assert config["azure_endpoint"] == "https://test.openai.azure.com/"
            assert config["model"] == "gpt-4o"


class TestMemorySystem:
    """Test memory management functionality."""

    def test_memory_creation(self):
        """Test that memory manager can be created."""
        from memory_manager import MemoryManager

        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryManager(memory_dir=Path(tmpdir))
            assert memory is not None
            assert memory.memory_dir.exists()
            # Memory file only created when memories are added
            assert memory.memory_file == Path(tmpdir) / "memories.json"

    def test_add_and_retrieve_memory(self):
        """Test adding and retrieving memories."""
        from memory_manager import MemoryManager

        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryManager(memory_dir=Path(tmpdir))

            # Add a memory
            memory.add_memory("Test memory content", importance=5)

            # Retrieve memories
            memories = memory.get_memories()
            assert len(memories) == 1
            assert memories[0].content == "Test memory content"
            assert memories[0].importance == 5

    def test_memory_search(self):
        """Test memory search functionality."""
        from memory_manager import MemoryManager

        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryManager(memory_dir=Path(tmpdir))

            # Add some memories
            memory.add_memory("Python programming tips", importance=5)
            memory.add_memory("JavaScript best practices", importance=4)
            memory.add_memory("Python debugging guide", importance=3)

            # Search for Python
            results = memory.search_memories("Python")
            assert len(results) == 2
            assert all("Python" in r.content for r in results)

    def test_memory_pruning(self):
        """Test that memory is pruned when exceeding max entries."""
        from memory_manager import MemoryManager

        with tempfile.TemporaryDirectory() as tmpdir:
            # Set very low max_memories for testing
            memory = MemoryManager(memory_dir=Path(tmpdir), max_memories=3)

            # Add more memories than max
            for i in range(5):
                memory.add_memory(f"Memory {i}", importance=i)

            # Should only keep most important 3
            memories = memory.get_memories()
            assert len(memories) == 3


class TestWebToolsSecurity:
    """Test web tools security features."""

    def test_url_validation_blocks_file_scheme(self):
        """Test that file:// URLs are blocked."""
        from agents.magentic_one.tools.web_tools import _validate_url

        is_valid, error = _validate_url("file:///etc/passwd")
        assert not is_valid
        assert "Blocked URL scheme" in error

    def test_url_validation_blocks_localhost(self):
        """Test that localhost access is blocked."""
        from agents.magentic_one.tools.web_tools import _validate_url

        is_valid, error = _validate_url("http://localhost:8080")
        assert not is_valid
        assert "localhost is blocked" in error

    def test_url_validation_blocks_private_ips(self):
        """Test that private IP addresses are blocked."""
        from agents.magentic_one.tools.web_tools import _validate_url

        test_ips = [
            "http://127.0.0.1",
            "http://10.0.0.1",
            "http://172.16.0.1",
            "http://192.168.1.1",
        ]

        for url in test_ips:
            is_valid, error = _validate_url(url)
            assert not is_valid, f"Should block {url}"
            assert "private/internal IPs is blocked" in error

    def test_url_validation_allows_public_urls(self):
        """Test that public URLs are allowed."""
        from agents.magentic_one.tools.web_tools import _validate_url

        public_urls = [
            "https://google.com",
            "https://github.com",
            "https://example.com",
        ]

        for url in public_urls:
            is_valid, error = _validate_url(url)
            assert is_valid, f"Should allow {url}, got error: {error}"
            assert error is None


class TestDataTools:
    """Test data tools functionality."""

    @pytest.mark.asyncio
    async def test_write_and_read_file(self):
        """Test file writing and reading."""
        from agents.data_tools import write_file, read_file

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            content = "Hello, world!"

            # Write file
            result = await write_file(str(test_file), content)
            assert result["success"]
            assert test_file.exists()

            # Read file
            result = await read_file(str(test_file))
            assert result["success"]
            assert result["content"] == content

    @pytest.mark.asyncio
    async def test_write_csv(self):
        """Test CSV writing."""
        from agents.data_tools import write_csv

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.csv"
            data = [
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25},
            ]

            result = await write_csv(str(test_file), data)
            assert result["success"]
            assert test_file.exists()

            # Verify content
            content = test_file.read_text()
            assert "Alice" in content
            assert "Bob" in content


class TestCLIBasics:
    """Test CLI basic functionality."""

    def test_cli_import(self):
        """Test that CLI can be imported."""
        from cli import CLIAgent
        assert CLIAgent is not None

    def test_memory_manager_import(self):
        """Test that memory manager can be imported."""
        from memory_manager import MemoryManager
        assert MemoryManager is not None

    def test_weather_agents_import(self):
        """Test that agent factories can be imported."""
        from agents.weather_agents import (
            create_weather_agent_team,
            create_simple_assistant,
            create_data_team,
            create_design_team,
            create_magentic_team
        )
        assert all([
            create_weather_agent_team,
            create_simple_assistant,
            create_data_team,
            create_design_team,
            create_magentic_team
        ])


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])

"""
Test CLI functionality and user interaction.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from io import StringIO

from v2.cli import (
    process_query,
    extract_number_from_query,
    get_available_agents,
    get_available_teams,
    format_tool_result
)
from v2.core.base_tool import ToolResult


class TestCLIQueryProcessing:
    """Test query processing in the CLI."""

    @pytest.mark.asyncio
    async def test_capability_query_detection(self):
        """Should detect capability queries correctly."""
        # Test various phrasings
        queries = [
            "what can you do",
            "What are your capabilities",
            "list all agents",
            "show me the tools",
            "list capabilities"
        ]

        for query in queries:
            result = await process_query(query)
            assert result.get("response") is not None
            # Should trigger capability listing
            assert "alfred" in result["response"].lower() or "capabilities" in result["response"].lower()

    @pytest.mark.asyncio
    async def test_history_query_detection(self):
        """Should detect history queries correctly."""
        queries = [
            "show my history",
            "what did I do last",
            "show my last 10 actions",
            "view history"
        ]

        for query in queries:
            result = await process_query(query)
            assert result.get("response") is not None

    @pytest.mark.asyncio
    async def test_delegation_query_detection(self):
        """Should detect delegation requests."""
        # Mock container to provide teams
        with patch('v2.cli.get_container') as mock_container:
            mock_container.return_value.get_capability_service.return_value.get_teams.return_value = [
                {"name": "weather_team", "agents": ["weather"]}
            ]

            query = "delegate to weather_team"
            result = await process_query(query)
            assert result.get("response") is not None

    @pytest.mark.asyncio
    async def test_agent_switching_detection(self):
        """Should detect agent switching requests."""
        with patch('v2.cli.get_container') as mock_container:
            mock_container.return_value.get_capability_service.return_value.get_agents.return_value = [
                {"name": "weather_agent", "category": "weather"}
            ]

            query = "use agent weather_agent"
            result = await process_query(query)
            assert result.get("response") is not None
            assert result.get("switch_to_agent") == "weather_agent"

    @pytest.mark.asyncio
    async def test_invalid_query_handling(self):
        """Should handle unrecognized queries gracefully."""
        query = "do something random that doesn't match any pattern"
        result = await process_query(query)
        assert result.get("response") is not None
        # Should provide helpful suggestions
        assert "what I can do" in result["response"].lower()

    @pytest.mark.asyncio
    async def test_empty_query_handling(self):
        """Should handle empty queries."""
        result = await process_query("")
        assert result == {"response": ""}

        result = await process_query("   ")
        assert result == {"response": ""}

    @pytest.mark.asyncio
    async def test_long_query_handling(self):
        """Should handle overly long queries."""
        long_query = "a" * 20000  # Exceeds MAX_QUERY_LENGTH
        result = await process_query(long_query)
        assert "too long" in result["response"]

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Should handle errors gracefully."""
        # Mock to raise an exception
        with patch('v2.cli.get_container') as mock_container:
            mock_container.side_effect = RuntimeError("Container initialization failed")

            result = await process_query("what can you do")
            assert "unexpected issue" in result["response"].lower()


class TestNumberExtraction:
    """Test number extraction from queries."""

    def test_extract_numeric_digits(self):
        """Should extract numeric digits."""
        assert extract_number_from_query("show me 10 items") == 10
        assert extract_number_from_query("last 5 actions") == 5
        assert extract_number_from_query("give me 100") == 100

    def test_extract_word_numbers(self):
        """Should extract word numbers."""
        assert extract_number_from_query("show me ten items") == 10
        assert extract_number_from_query("last twenty actions") == 20
        assert extract_number_from_query("fifty results") == 50

    def test_default_value(self):
        """Should return default when no number found."""
        assert extract_number_from_query("show me items") == 5
        assert extract_number_from_query("show me items", default=10) == 10

    def test_first_number_priority(self):
        """Should use first number found."""
        assert extract_number_from_query("show 10 of 20 items") == 10


class TestToolResultFormatting:
    """Test formatting of tool results."""

    def test_format_success_result(self):
        """Should format successful results."""
        result = ToolResult.ok({"data": "test"})
        formatted = format_tool_result(result)
        assert "Alfred" in formatted
        assert "test" in formatted

    def test_format_error_result(self):
        """Should format error results."""
        result = ToolResult.error("Something went wrong")
        formatted = format_tool_result(result)
        assert "Alfred" in formatted
        assert "Something went wrong" in formatted

    def test_format_preformatted_result(self):
        """Should use pre-formatted display strings."""
        result = ToolResult.ok({"formatted": "Custom display"})
        formatted = format_tool_result(result)
        assert "Certainly" in formatted
        assert "Custom display" in formatted


class TestAvailableResources:
    """Test fetching available agents and teams."""

    def test_get_available_agents(self):
        """Should get list of available agents."""
        mock_container = Mock()
        mock_container.get_capability_service.return_value.get_agents.return_value = [
            {"name": "Alfred"},
            {"name": "Weather_Agent"}
        ]

        agents, names = get_available_agents(mock_container)
        assert len(agents) == 2
        assert "alfred" in names
        assert "weather_agent" in names

    def test_get_available_teams(self):
        """Should get list of available teams."""
        mock_container = Mock()
        mock_container.get_capability_service.return_value.get_teams.return_value = [
            {"name": "Weather_Team"},
            {"name": "Data_Team"}
        ]

        teams, names = get_available_teams(mock_container)
        assert len(teams) == 2
        assert "weather_team" in names
        assert "data_team" in names
"""
Tests for Alfred core functionality
"""

import pytest
from src.alfred import Alfred


@pytest.mark.asyncio
async def test_alfred_initialization(mock_api_key, clean_settings, clean_persistence):
    """Test Alfred initializes correctly"""
    alfred = Alfred()
    await alfred.initialize()

    assert alfred.session_id is not None
    assert len(alfred.conversation_history) == 0

    await alfred.shutdown()


@pytest.mark.asyncio
async def test_alfred_greeting(mock_api_key, clean_settings, clean_persistence):
    """Test Alfred generates greeting"""
    alfred = Alfred()
    await alfred.initialize()

    greeting = await alfred.greet()

    assert isinstance(greeting, str)
    assert len(greeting) > 0

    await alfred.shutdown()


@pytest.mark.asyncio
async def test_conversation_history(mock_api_key, clean_settings, clean_persistence):
    """Test conversation history tracking"""
    alfred = Alfred()
    await alfred.initialize()

    # Add messages
    await alfred._add_to_history("user", "Hello")
    await alfred._add_to_history("assistant", "Hi there")

    assert len(alfred.conversation_history) == 2
    assert alfred.conversation_history[0]["role"] == "user"
    assert alfred.conversation_history[1]["role"] == "assistant"

    await alfred.shutdown()


@pytest.mark.asyncio
async def test_command_help(mock_api_key, clean_settings, clean_persistence):
    """Test /help command"""
    alfred = Alfred()
    await alfred.initialize()

    response = await alfred.process_message("/help")

    assert "Commands" in response or "help" in response.lower()
    assert "/model" in response

    await alfred.shutdown()


@pytest.mark.asyncio
async def test_command_mode(mock_api_key, clean_settings, clean_persistence):
    """Test /mode command"""
    alfred = Alfred()
    await alfred.initialize()

    response = await alfred.process_message("/mode")

    assert "mode" in response.lower()

    await alfred.shutdown()

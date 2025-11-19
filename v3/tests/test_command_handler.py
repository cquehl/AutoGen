"""
Test suite for CommandHandler (extracted from main_enhanced.py)
TDD-first approach: Tests written BEFORE extracting command handler

Focus: Verify command handling can be extracted without breaking behavior
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch


# ============================================================================
# COMMAND HANDLER TESTS
# ============================================================================

class TestCommandHandlerExtraction:
    """Test that commands can be extracted into separate handler"""

    @pytest.mark.asyncio
    async def test_command_handler_exists(self):
        """CommandHandler class should exist"""
        from v3.src.alfred.command_handler import CommandHandler

        assert CommandHandler is not None
        assert callable(CommandHandler)

    @pytest.mark.asyncio
    async def test_command_handler_initialization(self):
        """CommandHandler should initialize with alfred reference"""
        from v3.src.alfred.command_handler import CommandHandler

        alfred_mock = Mock()
        handler = CommandHandler(alfred_mock)

        assert handler.alfred == alfred_mock

    @pytest.mark.asyncio
    async def test_handle_help_command(self):
        """Should handle /help command"""
        from v3.src.alfred.command_handler import CommandHandler

        alfred_mock = Mock()
        handler = CommandHandler(alfred_mock)

        result = await handler.handle("/help")

        assert isinstance(result, str)
        assert "ALFRED COMMAND REFERENCE" in result or "help" in result.lower()

    @pytest.mark.asyncio
    async def test_handle_unknown_command(self):
        """Should return error for unknown commands"""
        from v3.src.alfred.command_handler import CommandHandler

        alfred_mock = Mock()
        handler = CommandHandler(alfred_mock)

        result = await handler.handle("/unknowncommand")

        assert "Unknown command" in result or "unknown" in result.lower()

    @pytest.mark.asyncio
    async def test_handle_model_command_no_args(self):
        """Should show current model when no args provided"""
        from v3.src.alfred.command_handler import CommandHandler

        alfred_mock = Mock()
        alfred_mock.settings = Mock()
        alfred_mock.settings.get_available_providers = Mock(return_value=["openai", "anthropic"])

        handler = CommandHandler(alfred_mock)

        with patch('v3.src.alfred.command_handler.get_llm_gateway') as mock_gateway:
            mock_gateway.return_value.get_current_model.return_value = "gpt-4"
            result = await handler.handle("/model")

        assert "gpt-4" in result or "Current model" in result

    @pytest.mark.asyncio
    async def test_handle_cost_command(self):
        """Should show cost summary"""
        from v3.src.alfred.command_handler import CommandHandler

        alfred_mock = Mock()
        alfred_mock.cost_tracker = Mock()
        alfred_mock.cost_tracker.get_summary.return_value = "Total: $1.50"

        handler = CommandHandler(alfred_mock)

        result = await handler.handle("/cost")

        assert "$1.50" in result or "cost" in result.lower()

    @pytest.mark.asyncio
    async def test_handle_mode_command(self):
        """Should show current mode"""
        from v3.src.alfred.command_handler import CommandHandler

        alfred_mock = Mock()
        alfred_mock.current_mode = Mock()
        alfred_mock.current_mode.value = "direct"

        handler = CommandHandler(alfred_mock)

        result = await handler.handle("/mode")

        assert "mode" in result.lower() or "direct" in result.lower()

    @pytest.mark.asyncio
    async def test_handle_clear_command(self):
        """Should clear conversation history"""
        from v3.src.alfred.command_handler import CommandHandler

        alfred_mock = Mock()
        alfred_mock.conversation_history = ["msg1", "msg2"]

        handler = CommandHandler(alfred_mock)

        result = await handler.handle("/clear")

        assert len(alfred_mock.conversation_history) == 0 or "clear" in result.lower()


class TestCommandParsing:
    """Test command parsing logic"""

    @pytest.mark.asyncio
    async def test_parse_command_with_args(self):
        """Should parse command and arguments correctly"""
        from v3.src.alfred.command_handler import CommandHandler

        alfred_mock = Mock()
        handler = CommandHandler(alfred_mock)

        cmd, args = handler._parse_command("/model gpt-4")

        assert cmd == "/model"
        assert args == "gpt-4"

    @pytest.mark.asyncio
    async def test_parse_command_without_args(self):
        """Should parse command without arguments"""
        from v3.src.alfred.command_handler import CommandHandler

        alfred_mock = Mock()
        handler = CommandHandler(alfred_mock)

        cmd, args = handler._parse_command("/help")

        assert cmd == "/help"
        assert args == ""


class TestPreferencesCommandRefactored:
    """Test preferences command moved to CommandHandler"""

    @pytest.mark.asyncio
    async def test_preferences_view(self):
        """Should view current preferences"""
        from v3.src.alfred.command_handler import CommandHandler

        alfred_mock = Mock()
        alfred_mock.preferences_manager = Mock()
        alfred_mock.preferences_manager.get_preferences.return_value = {
            "gender": "male",
            "name": "Charles"
        }

        handler = CommandHandler(alfred_mock)

        result = await handler.handle("/preferences view")

        assert "Charles" in result or "male" in result or "sir" in result

    @pytest.mark.asyncio
    async def test_preferences_set(self):
        """Should set preference using public method (not private!)"""
        from v3.src.alfred.command_handler import CommandHandler

        alfred_mock = Mock()
        alfred_mock.preferences_manager = Mock()
        alfred_mock.preferences_manager.preferences = {}
        alfred_mock.preferences_manager.save = Mock()  # PUBLIC method, not _save_to_storage!

        handler = CommandHandler(alfred_mock)

        result = await handler.handle("/preferences set name=Alice")

        assert alfred_mock.preferences_manager.save.called
        assert alfred_mock.preferences_manager.preferences["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_preferences_reset(self):
        """Should clear preferences using public method"""
        from v3.src.alfred.command_handler import CommandHandler

        alfred_mock = Mock()
        alfred_mock.preferences_manager = Mock()
        alfred_mock.preferences_manager.clear = Mock()  # PUBLIC method!

        handler = CommandHandler(alfred_mock)

        result = await handler.handle("/preferences reset")

        assert alfred_mock.preferences_manager.clear.called


class TestEncapsulationFixes:
    """Test that encapsulation violations are fixed"""

    @pytest.mark.asyncio
    async def test_preferences_manager_has_public_save(self):
        """UserPreferencesManager should have public save() method"""
        from v3.src.alfred.user_preferences import UserPreferencesManager

        manager = UserPreferencesManager("session123", use_llm_extraction=False)

        # Should have public save method (not just _storage.save)
        assert hasattr(manager, "save")
        assert callable(manager.save)

    @pytest.mark.asyncio
    async def test_preferences_manager_has_public_clear(self):
        """UserPreferencesManager should have public clear() method"""
        from v3.src.alfred.user_preferences import UserPreferencesManager

        manager = UserPreferencesManager("session123", use_llm_extraction=False)

        # Should have public clear method (not just _delete_existing_preferences)
        assert hasattr(manager, "clear")
        assert callable(manager.clear)


class TestAlfredEnhancedDelegation:
    """Test that AlfredEnhanced delegates to CommandHandler"""

    @pytest.mark.asyncio
    async def test_alfred_has_command_handler(self):
        """AlfredEnhanced should have a command_handler instance"""
        from v3.src.alfred.main_enhanced import AlfredEnhanced

        alfred = AlfredEnhanced()

        assert hasattr(alfred, "command_handler")
        assert alfred.command_handler is not None

    @pytest.mark.asyncio
    async def test_handle_command_delegates(self):
        """_handle_command should delegate to command_handler.handle()"""
        from v3.src.alfred.main_enhanced import AlfredEnhanced

        alfred = AlfredEnhanced()
        alfred.command_handler = Mock()
        alfred.command_handler.handle = AsyncMock(return_value="Command result")

        result = await alfred._handle_command("/test")

        assert alfred.command_handler.handle.called
        assert result == "Command result"


class TestNoBreakingChanges:
    """Verify no breaking changes to public API"""

    @pytest.mark.asyncio
    async def test_public_methods_still_exist(self):
        """All original public methods should still exist"""
        from v3.src.alfred.main_enhanced import AlfredEnhanced

        alfred = AlfredEnhanced()

        # Public API methods
        assert hasattr(alfred, "initialize")
        assert hasattr(alfred, "greet")
        assert hasattr(alfred, "handle_message")
        assert hasattr(alfred, "process_message_streaming")
        assert hasattr(alfred, "process_message")
        assert hasattr(alfred, "shutdown")
        assert hasattr(alfred, "get_session_id")
        assert hasattr(alfred, "get_conversation_count")
        assert hasattr(alfred, "get_session_cost")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

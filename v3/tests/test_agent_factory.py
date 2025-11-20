"""
Test suite for AgentFactory and SpecialistRegistry extraction from modes.py
TDD approach: Tests written BEFORE implementation
"""

import pytest
from unittest.mock import Mock, MagicMock, patch


# ============================================================================
# SPECIALIST REGISTRY TESTS
# ============================================================================

class TestSpecialistRegistry:
    """Test SpecialistRegistry class"""

    def test_registry_has_all_specialists(self):
        """Registry should contain all 7 specialist types"""
        from v3.src.alfred.agent_factory import SpecialistRegistry

        specialists = SpecialistRegistry.SPECIALISTS

        # Should have these specialists
        expected_specialists = ["engineer", "qa", "product", "ux", "data", "security", "ops"]

        for specialist in expected_specialists:
            assert specialist in specialists, f"Missing specialist: {specialist}"

    def test_get_specialist_returns_config(self):
        """get_specialist should return specialist configuration"""
        from v3.src.alfred.agent_factory import SpecialistRegistry

        engineer_config = SpecialistRegistry.get_specialist("engineer")

        assert engineer_config is not None
        assert "role" in engineer_config
        assert "expertise" in engineer_config
        assert "Senior Software Engineer" in engineer_config["role"]

    def test_get_specialist_invalid_name(self):
        """get_specialist should return None for invalid name"""
        from v3.src.alfred.agent_factory import SpecialistRegistry

        result = SpecialistRegistry.get_specialist("invalid_specialist")

        assert result is None

    def test_get_all_names(self):
        """get_all_names should return list of specialist names"""
        from v3.src.alfred.agent_factory import SpecialistRegistry

        names = SpecialistRegistry.get_all_names()

        assert isinstance(names, list)
        assert len(names) == 7
        assert "engineer" in names
        assert "qa" in names


# ============================================================================
# AGENT FACTORY TESTS
# ============================================================================

class TestAgentFactory:
    """Test AgentFactory class"""

    def test_factory_initialization(self):
        """AgentFactory should initialize with registry"""
        from v3.src.alfred.agent_factory import AgentFactory

        factory = AgentFactory()

        assert factory is not None
        assert factory.registry is not None

    def test_factory_custom_registry(self):
        """AgentFactory should accept custom registry"""
        from v3.src.alfred.agent_factory import AgentFactory, SpecialistRegistry

        custom_registry = SpecialistRegistry()
        factory = AgentFactory(registry=custom_registry)

        assert factory.registry == custom_registry

    @patch('v3.src.alfred.agent_factory.create_model_client')
    @patch('v3.src.alfred.agent_factory.AssistantAgent')
    def test_create_agent(self, mock_assistant, mock_model_client):
        """Should create single agent from specialist name"""
        from v3.src.alfred.agent_factory import AgentFactory

        # Mock the model client
        mock_model_client.return_value = Mock()
        mock_assistant.return_value = Mock(name="ENGINEER")

        factory = AgentFactory()
        agent = factory.create_agent("engineer")

        # Should have called create_model_client
        assert mock_model_client.called

        # Should have created AssistantAgent with correct params
        assert mock_assistant.called
        call_args = mock_assistant.call_args
        assert call_args[1]["name"] == "ENGINEER"
        assert "Software" in call_args[1]["system_message"]

    @patch('v3.src.alfred.agent_factory.create_model_client')
    @patch('v3.src.alfred.agent_factory.AssistantAgent')
    def test_create_agent_with_model(self, mock_assistant, mock_model_client):
        """Should create agent with custom model"""
        from v3.src.alfred.agent_factory import AgentFactory

        mock_model_client.return_value = Mock()
        mock_assistant.return_value = Mock()

        factory = AgentFactory()
        agent = factory.create_agent("engineer", model="gpt-4")

        # Should have passed model to create_model_client
        mock_model_client.assert_called_with("gpt-4")

    def test_create_agent_invalid_specialist(self):
        """Should raise ValueError for invalid specialist name"""
        from v3.src.alfred.agent_factory import AgentFactory

        factory = AgentFactory()

        with pytest.raises(ValueError, match="Unknown specialist"):
            factory.create_agent("invalid_specialist")

    @patch('v3.src.alfred.agent_factory.create_model_client')
    @patch('v3.src.alfred.agent_factory.AssistantAgent')
    def test_create_team(self, mock_assistant, mock_model_client):
        """Should create multiple agents at once"""
        from v3.src.alfred.agent_factory import AgentFactory

        mock_model_client.return_value = Mock()
        mock_assistant.side_effect = [
            Mock(name="ENGINEER"),
            Mock(name="QA"),
            Mock(name="PRODUCT")
        ]

        factory = AgentFactory()
        agents = factory.create_team(["engineer", "qa", "product"])

        assert len(agents) == 3
        assert mock_assistant.call_count == 3

    def test_build_system_message(self):
        """Should build system message from template"""
        from v3.src.alfred.agent_factory import AgentFactory

        factory = AgentFactory()
        message = factory._build_system_message(
            name="ENGINEER",
            role="Senior Software Engineer",
            expertise="Software architecture, coding"
        )

        assert isinstance(message, str)
        assert "ENGINEER" in message
        assert "Senior Software Engineer" in message
        assert "Software architecture" in message
        assert "Your Expertise:" in message
        assert "Your Role in the Team:" in message


# ============================================================================
# TEAM ORCHESTRATOR INTEGRATION TESTS
# ============================================================================

class TestTeamOrchestratorIntegration:
    """Test that TeamOrchestratorMode uses AgentFactory correctly"""

    def test_team_orchestrator_has_factory(self):
        """TeamOrchestratorMode should have agent_factory attribute"""
        from v3.src.alfred.modes import TeamOrchestratorMode

        team_mode = TeamOrchestratorMode()

        assert hasattr(team_mode, "factory")
        assert team_mode.factory is not None

    @pytest.mark.asyncio
    @patch('v3.src.alfred.agent_factory.create_model_client')
    @patch('v3.src.alfred.agent_factory.AssistantAgent')
    async def test_assemble_team_uses_factory(self, mock_assistant, mock_model_client):
        """assemble_team should delegate to AgentFactory"""
        from v3.src.alfred.modes import TeamOrchestratorMode

        mock_model_client.return_value = Mock()
        mock_assistant.side_effect = [Mock(name="ENGINEER"), Mock(name="QA")]

        team_mode = TeamOrchestratorMode()
        agents = await team_mode.assemble_team("Build a web app")

        # Should have created agents via factory
        assert len(agents) > 0
        assert mock_assistant.called

    def test_create_specialist_agent_removed(self):
        """Old create_specialist_agent method should be removed"""
        from v3.src.alfred.modes import TeamOrchestratorMode

        team_mode = TeamOrchestratorMode()

        # Should NOT have this method anymore
        assert not hasattr(team_mode, "create_specialist_agent"), \
            "create_specialist_agent should be removed (moved to AgentFactory)"


# ============================================================================
# BACKWARDS COMPATIBILITY TESTS
# ============================================================================

class TestBackwardsCompatibility:
    """Ensure no breaking changes to public API"""

    def test_team_orchestrator_public_methods_exist(self):
        """TeamOrchestratorMode should maintain public API"""
        from v3.src.alfred.modes import TeamOrchestratorMode

        team_mode = TeamOrchestratorMode()

        # Public methods should still exist
        assert hasattr(team_mode, "assemble_team")
        assert hasattr(team_mode, "process")
        assert hasattr(team_mode, "_determine_agents_for_task")

    def test_get_team_mode_still_works(self):
        """get_team_mode() singleton function should still work"""
        from v3.src.alfred.modes import get_team_mode

        team_mode = get_team_mode()

        assert team_mode is not None
        assert hasattr(team_mode, "process")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

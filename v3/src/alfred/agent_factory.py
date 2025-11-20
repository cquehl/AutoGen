"""
Agent Factory for Suntory v3
Extracted from modes.py to reduce complexity and improve maintainability

Responsibilities:
- Maintain specialist agent configurations
- Create AutoGen AssistantAgent instances
- Batch create teams of specialists
"""

from typing import Dict, List, Optional

from autogen_agentchat.agents import AssistantAgent

from ..core import get_logger
from ..core.model_factory import create_model_client

logger = get_logger(__name__)


class SpecialistRegistry:
    """
    Registry of specialist agent configurations.

    Centralizes specialist definitions for easy maintenance and extension.
    """

    SPECIALISTS = {
        "engineer": {
            "role": "Senior Software Engineer",
            "expertise": "Software architecture, coding best practices, system design, debugging"
        },
        "qa": {
            "role": "QA Engineer",
            "expertise": "Test strategy, quality assurance, bug detection, test automation"
        },
        "product": {
            "role": "Product Manager",
            "expertise": "Requirements gathering, user stories, product vision, prioritization"
        },
        "ux": {
            "role": "UX Designer",
            "expertise": "User experience, interface design, usability, accessibility"
        },
        "data": {
            "role": "Data Scientist",
            "expertise": "Data analysis, ETL pipelines, statistical modeling, data visualization"
        },
        "security": {
            "role": "Security Auditor",
            "expertise": "Security vulnerabilities, threat modeling, secure coding, compliance"
        },
        "ops": {
            "role": "Operations Engineer",
            "expertise": "Infrastructure, deployment, monitoring, scalability, DevOps"
        }
    }

    @classmethod
    def get_specialist(cls, name: str) -> Optional[Dict[str, str]]:
        """
        Get specialist configuration by name.

        Args:
            name: Specialist name (e.g., "engineer", "qa")

        Returns:
            Specialist config dict or None if not found
        """
        return cls.SPECIALISTS.get(name)

    @classmethod
    def get_all_names(cls) -> List[str]:
        """
        Get all specialist names.

        Returns:
            List of specialist names
        """
        return list(cls.SPECIALISTS.keys())


class AgentFactory:
    """
    Factory for creating AutoGen specialist agents.

    Handles:
    - Creating individual specialist agents
    - Batch creating teams of agents
    - Building system messages from templates
    - Model client configuration
    """

    def __init__(self, registry: Optional[SpecialistRegistry] = None):
        """
        Initialize agent factory.

        Args:
            registry: Specialist registry (uses default if not provided)
        """
        self.registry = registry or SpecialistRegistry()

    def create_agent(
        self,
        name: str,
        model: Optional[str] = None
    ) -> AssistantAgent:
        """
        Create a single specialist agent.

        Args:
            name: Specialist name (e.g., "engineer", "qa")
            model: Optional LLM model to use

        Returns:
            Configured AssistantAgent

        Raises:
            ValueError: If specialist name is not found in registry
        """
        # Get specialist configuration
        config = self.registry.get_specialist(name)
        if not config:
            raise ValueError(
                f"Unknown specialist: {name}. "
                f"Available: {', '.join(self.registry.get_all_names())}"
            )

        # Build system message
        system_message = self._build_system_message(
            name=name.upper(),
            role=config["role"],
            expertise=config["expertise"]
        )

        # Create model client
        model_client = create_model_client(model)

        logger.debug(
            f"Creating agent {name.upper()}",
            model_client_type=type(model_client).__name__
        )

        # Create and return agent
        agent = AssistantAgent(
            name=name.upper(),
            model_client=model_client,
            system_message=system_message
        )

        return agent

    def create_team(
        self,
        agent_names: List[str],
        model: Optional[str] = None
    ) -> List[AssistantAgent]:
        """
        Create multiple agents at once (batch creation).

        Args:
            agent_names: List of specialist names
            model: Optional LLM model to use for all agents

        Returns:
            List of configured AssistantAgents
        """
        agents = []
        for name in agent_names:
            try:
                agent = self.create_agent(name, model=model)
                agents.append(agent)
            except ValueError as e:
                logger.warning(f"Skipping invalid specialist: {e}")
                continue

        logger.info(
            f"Created team of {len(agents)} specialists",
            agents=[a.name for a in agents]
        )

        return agents

    def _build_system_message(
        self,
        name: str,
        role: str,
        expertise: str
    ) -> str:
        """
        Build system message from template.

        Args:
            name: Agent name (uppercase, e.g., "ENGINEER")
            role: Agent role title
            expertise: Area of expertise description

        Returns:
            Formatted system message
        """
        return f"""You are {name}, a {role} specialist.

**Your Expertise:** {expertise}

**Your Role in the Team:**
- Provide expert guidance in your domain
- Collaborate with other specialists
- Deliver high-quality, actionable outputs
- Ask clarifying questions when needed
- Flag issues or concerns in your area

**Communication Style:**
- Clear and professional
- Domain-specific but accessible
- Collaborative and team-oriented

Focus on your area of expertise and coordinate with team members."""

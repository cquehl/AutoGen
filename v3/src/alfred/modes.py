"""
Suntory v3 - Alfred's Operating Modes
Direct Proxy and Team Orchestrator
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_core.models import ChatCompletionClient

from ..core import get_llm_gateway, get_logger, set_correlation_id
from ..core.model_factory import create_model_client

logger = get_logger(__name__)

# Team mode detection thresholds
COMPLEXITY_WORD_THRESHOLD = 50  # Words threshold for complex tasks
MAX_RECENT_MESSAGES = 3  # Number of recent messages to extract from team output


class AlfredMode(str, Enum):
    """Alfred's operating modes"""
    DIRECT = "direct"  # Direct proxy to LLM
    TEAM = "team"  # Team orchestrator


class DirectProxyMode:
    """
    Direct Proxy Mode: Alfred as intelligent middleware.

    Alfred acts as a senior engineer reviewing and enhancing user requests
    before sending to LLMs, then validating and formatting responses.
    """

    def __init__(self):
        self.llm_gateway = get_llm_gateway()

    async def process(
        self,
        user_message: str,
        context: Optional[List[Dict[str, str]]] = None,
        system_message: Optional[str] = None
    ) -> str:
        """
        Process user message in direct mode.

        Args:
            user_message: User's input
            context: Conversation context
            system_message: System message for the LLM

        Returns:
            Alfred's response
        """
        logger.info("Processing in Direct Proxy mode", message_length=len(user_message))

        # Build message history
        messages = []

        if system_message:
            messages.append({
                "role": "system",
                "content": system_message
            })

        # Add context if provided
        if context:
            messages.extend(context)

        # Add user message
        messages.append({
            "role": "user",
            "content": user_message
        })

        try:
            # Get response from LLM
            response = await self.llm_gateway.acomplete(
                messages=messages,
                temperature=0.7,
                max_tokens=2048
            )

            assistant_message = response.choices[0].message.content

            logger.info(
                "Direct mode response generated",
                response_length=len(assistant_message)
            )

            return assistant_message

        except Exception as e:
            logger.error(f"Direct mode failed: {e}")
            return f"I apologize, but I encountered an error: {str(e)}"

    def should_use_team_mode(self, message: str) -> bool:
        """
        Determine if message requires team orchestration.

        Args:
            message: User message

        Returns:
            True if team mode should be used
        """
        # Keywords that suggest complex tasks
        team_keywords = [
            "build", "create", "implement", "develop", "design",
            "analyze", "research", "investigate", "review",
            "test", "qa", "security", "audit",
            "data pipeline", "architecture", "system",
            "full stack", "end-to-end"
        ]

        message_lower = message.lower()

        # Check for team keywords
        for keyword in team_keywords:
            if keyword in message_lower:
                logger.info(f"Team mode triggered by keyword: {keyword}")
                return True

        # Check for explicit team request
        if "/team" in message_lower:
            logger.info("Team mode triggered by explicit request")
            return True

        # Check message complexity (word count as heuristic)
        if len(message.split()) > COMPLEXITY_WORD_THRESHOLD:
            logger.info(
                "Team mode triggered by message complexity",
                word_count=len(message.split()),
                threshold=COMPLEXITY_WORD_THRESHOLD
            )
            return True

        return False


class TeamOrchestratorMode:
    """
    Team Orchestrator Mode: Alfred manages specialist agents.

    Alfred assembles and coordinates specialist agents using AutoGen
    to tackle complex, multi-faceted tasks.
    """

    def __init__(self):
        self.llm_gateway = get_llm_gateway()

    def create_specialist_agent(
        self,
        name: str,
        role: str,
        expertise: str,
        model: Optional[str] = None
    ) -> AssistantAgent:
        """
        Create a specialist agent.

        Args:
            name: Agent name
            role: Agent role/title
            expertise: Area of expertise
            model: LLM model to use (model name string)

        Returns:
            Configured AssistantAgent
        """
        system_message = f"""You are {name}, a {role} specialist.

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

        # Create proper AutoGen ModelClient instead of passing string
        # If model is provided, use it; otherwise use default from settings
        model_client = create_model_client(model)

        logger.debug(
            f"Creating agent {name}",
            model_client_type=type(model_client).__name__
        )

        agent = AssistantAgent(
            name=name,
            model_client=model_client,
            system_message=system_message,
        )

        return agent

    async def assemble_team(
        self,
        task_type: str,
        custom_agents: Optional[List[str]] = None
    ) -> List[AssistantAgent]:
        """
        Assemble appropriate team for task.

        Args:
            task_type: Type of task (engineering, data, design, security, etc.)
            custom_agents: Custom list of agent roles

        Returns:
            List of specialist agents
        """
        logger.info(f"Assembling team for: {task_type}")

        agents = []

        # Define specialist roles
        specialists = {
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

        # Determine which specialists to include
        if custom_agents:
            agent_roles = custom_agents
        else:
            # Auto-select based on task type
            agent_roles = self._determine_agents_for_task(task_type)

        # Create agents
        for role_key in agent_roles:
            if role_key in specialists:
                spec = specialists[role_key]
                agent = self.create_specialist_agent(
                    name=role_key.upper(),
                    role=spec["role"],
                    expertise=spec["expertise"]
                )
                agents.append(agent)

        logger.info(
            f"Team assembled with {len(agents)} specialists",
            agents=[a.name for a in agents]
        )

        return agents

    def _determine_agents_for_task(self, task_type: str) -> List[str]:
        """Determine which agents to use based on task type"""
        task_lower = task_type.lower()

        # Predefined team compositions
        if "data" in task_lower or "analytics" in task_lower:
            return ["product", "data", "engineer"]

        if "security" in task_lower or "audit" in task_lower:
            return ["security", "engineer", "ops"]

        if "ui" in task_lower or "ux" in task_lower or "design" in task_lower:
            return ["product", "ux", "engineer"]

        if "deploy" in task_lower or "infrastructure" in task_lower:
            return ["ops", "engineer", "security"]

        if "test" in task_lower or "qa" in task_lower:
            return ["qa", "engineer"]

        # Default: full team for complex tasks
        return ["product", "engineer", "qa"]

    async def process(
        self,
        task_description: str,
        team_type: Optional[str] = None,
        max_turns: Optional[int] = None
    ) -> str:
        """
        Process task using team orchestration.

        Args:
            task_description: Description of the task
            team_type: Type of team to assemble
            max_turns: Maximum conversation turns

        Returns:
            Team's output
        """
        correlation_id = set_correlation_id()
        logger.info(
            "Processing in Team Orchestrator mode",
            correlation_id=correlation_id,
            task=task_description
        )

        # Assemble team
        team_agents = await self.assemble_team(team_type or task_description)

        # Create termination condition
        termination = TextMentionTermination("TERMINATE")

        # Create group chat
        team = RoundRobinGroupChat(
            participants=team_agents,
            termination_condition=termination,
            max_turns=max_turns or 30
        )

        try:
            # Run the team
            logger.info("Starting team collaboration", correlation_id=correlation_id)

            result = await team.run(task=task_description)

            # Extract final output
            final_output = self._extract_team_output(result)

            logger.info(
                "Team collaboration completed",
                correlation_id=correlation_id,
                turns=len(result.messages) if hasattr(result, 'messages') else 0
            )

            return final_output

        except AttributeError as e:
            # Specific handling for model_info errors
            error_msg = str(e)
            logger.error(
                f"Team orchestration failed: {error_msg}",
                correlation_id=correlation_id,
                error_type="AttributeError"
            )

            if "model_info" in error_msg:
                return (
                    "I apologize, but the team encountered a configuration issue with the AI models. "
                    "This has been logged for investigation. Please try using direct mode for now, "
                    "or contact support if this persists."
                )
            else:
                return f"I apologize, but the team encountered an error: {error_msg}"

        except Exception as e:
            import traceback
            logger.error(
                f"Team orchestration failed: {str(e)}\nTraceback:\n{traceback.format_exc()}",
                correlation_id=correlation_id
            )
            return (
                f"I apologize, but the team encountered an error: {str(e)}\n\n"
                "This has been logged. You may want to try:\n"
                "• Using a simpler request\n"
                "• Switching models with `/model <name>`\n"
                "• Asking me directly without team mode"
            )

    def _extract_team_output(self, result: Any) -> str:
        """Extract meaningful output from team result"""
        # Extract the final message or summary
        if hasattr(result, 'messages') and result.messages:
            # Get last few messages for context
            recent_messages = result.messages[-MAX_RECENT_MESSAGES:]
            output_parts = []

            for msg in recent_messages:
                if hasattr(msg, 'content'):
                    output_parts.append(f"{msg.source}: {msg.content}")

            return "\n\n".join(output_parts)

        return str(result)


# Singleton instances
_direct_mode: Optional[DirectProxyMode] = None
_team_mode: Optional[TeamOrchestratorMode] = None


def get_direct_mode() -> DirectProxyMode:
    """Get or create direct mode singleton"""
    global _direct_mode
    if _direct_mode is None:
        _direct_mode = DirectProxyMode()
    return _direct_mode


def get_team_mode() -> TeamOrchestratorMode:
    """Get or create team mode singleton"""
    global _team_mode
    if _team_mode is None:
        _team_mode = TeamOrchestratorMode()
    return _team_mode

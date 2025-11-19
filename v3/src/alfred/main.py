"""
Suntory v3 - Alfred Main Module
Core Alfred orchestration and conversation loop
"""

import asyncio
import uuid
from datetime import datetime
from typing import List, Optional

from ..core import (
    get_db_manager,
    get_logger,
    get_settings,
    get_vector_manager,
    set_correlation_id,
)
from .modes import AlfredMode, get_direct_mode, get_team_mode
from .personality import get_alfred_personality

logger = get_logger(__name__)


class Alfred:
    """
    Alfred - The Distinguished AI Concierge

    Main orchestrator for the Suntory System.
    Manages user interactions, delegates to appropriate modes,
    and maintains conversation state.
    """

    def __init__(self):
        self.settings = get_settings()
        self.personality = get_alfred_personality()
        self.direct_mode = get_direct_mode()
        self.team_mode = get_team_mode()

        # Session management
        self.session_id = str(uuid.uuid4())
        self.conversation_history: List[dict] = []
        self.current_mode = AlfredMode.DIRECT

        logger.info(
            "Alfred initialized",
            session_id=self.session_id,
            model=self.settings.default_model
        )

    async def initialize(self):
        """Initialize Alfred and required services"""
        logger.info("Initializing Alfred and services...")

        # Initialize database
        db = await get_db_manager()

        # Initialize vector store
        vector = get_vector_manager()

        # Log session start
        await db.add_conversation(
            session_id=self.session_id,
            role="system",
            content="Session started",
            metadata={
                "model": self.settings.default_model,
                "environment": self.settings.environment.value
            }
        )

        logger.info("Alfred ready", session_id=self.session_id)

    async def greet(self) -> str:
        """
        Generate and return Alfred's greeting.

        Returns:
            Greeting message
        """
        greeting = await self.personality.get_greeting()

        # Log greeting
        await self._add_to_history("assistant", greeting)

        return greeting

    async def process_message(
        self,
        user_message: str,
        force_mode: Optional[AlfredMode] = None
    ) -> str:
        """
        Process user message and generate response.

        Args:
            user_message: User's input
            force_mode: Force specific mode (optional)

        Returns:
            Alfred's response
        """
        correlation_id = set_correlation_id()

        logger.info(
            "Processing user message",
            correlation_id=correlation_id,
            message_length=len(user_message)
        )

        # Add to history
        await self._add_to_history("user", user_message)

        # Check for commands
        if user_message.startswith("/"):
            return await self._handle_command(user_message)

        # Determine mode
        if force_mode:
            mode = force_mode
        elif self.direct_mode.should_use_team_mode(user_message):
            mode = AlfredMode.TEAM
        else:
            mode = AlfredMode.DIRECT

        self.current_mode = mode

        logger.info(f"Using {mode.value} mode")

        # Process based on mode
        try:
            if mode == AlfredMode.DIRECT:
                response = await self._process_direct(user_message)
            else:
                response = await self._process_team(user_message)

            # Add response to history
            await self._add_to_history("assistant", response)

            return response

        except Exception as e:
            logger.error(f"Failed to process message: {e}", exc_info=True)
            error_response = (
                f"I apologize, but I encountered an error: {str(e)}. "
                "Shall we try rephrasing your request?"
            )
            await self._add_to_history("assistant", error_response)
            return error_response

    async def _process_direct(self, message: str) -> str:
        """Process message in direct mode"""
        system_message = self.personality.get_system_message()

        response = await self.direct_mode.process(
            user_message=message,
            context=self.conversation_history[-10:],  # Last 10 messages for context
            system_message=system_message
        )

        return response

    async def _process_team(self, message: str) -> str:
        """Process message in team orchestrator mode"""
        # Add preamble about team assembly
        preamble = (
            "Certainly. This appears to be a complex task. "
            "I'm assembling a team of specialists to handle this properly.\n\n"
        )

        # Process with team
        team_response = await self.team_mode.process(
            task_description=message,
            max_turns=self.settings.max_team_turns
        )

        return preamble + team_response

    async def _handle_command(self, command: str) -> str:
        """
        Handle special commands.

        Args:
            command: Command string (starts with /)

        Returns:
            Command response
        """
        logger.info(f"Handling command: {command}")

        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "/model":
            return await self._cmd_switch_model(args)
        elif cmd == "/team":
            # Force team mode for next message
            if args:
                return await self.process_message(args, force_mode=AlfredMode.TEAM)
            else:
                return "Please provide a task description. Example: /team Build a data pipeline"
        elif cmd == "/mode":
            return self._cmd_show_mode()
        elif cmd == "/history":
            return await self._cmd_show_history()
        elif cmd == "/help":
            return self._cmd_help()
        elif cmd == "/clear":
            return await self._cmd_clear_history()
        else:
            return f"Unknown command: {cmd}. Type /help for available commands."

    async def _cmd_switch_model(self, model_name: str) -> str:
        """Switch LLM model"""
        if not model_name:
            from ..core import get_llm_gateway
            gateway = get_llm_gateway()
            current = gateway.get_current_model()
            available = self.settings.get_available_providers()
            return (
                f"Current model: {current}\n"
                f"Available providers: {', '.join(available)}\n\n"
                "Usage: /model <model_name>\n"
                "Examples:\n"
                "  /model gpt-4o\n"
                "  /model claude-3-5-sonnet-20241022\n"
                "  /model gemini-pro"
            )

        try:
            from ..core import get_llm_gateway
            gateway = get_llm_gateway()
            previous = gateway.switch_model(model_name)
            return f"Switched from {previous} to {model_name}."
        except Exception as e:
            return f"Failed to switch model: {str(e)}"

    def _cmd_show_mode(self) -> str:
        """Show current mode"""
        return (
            f"Current mode: {self.current_mode.value}\n\n"
            "**Direct Mode**: Alfred handles queries directly\n"
            "**Team Mode**: Alfred assembles specialist team\n\n"
            "Use `/team <task>` to force team mode."
        )

    async def _cmd_show_history(self) -> str:
        """Show conversation history"""
        if not self.conversation_history:
            return "No conversation history yet."

        history_lines = ["**Recent Conversation:**\n"]

        for entry in self.conversation_history[-10:]:
            role = entry["role"].capitalize()
            content = entry["content"][:100]  # Truncate
            if len(entry["content"]) > 100:
                content += "..."
            history_lines.append(f"**{role}**: {content}")

        return "\n".join(history_lines)

    async def _cmd_clear_history(self) -> str:
        """Clear conversation history"""
        self.conversation_history.clear()
        return "Conversation history cleared. Starting fresh."

    def _cmd_help(self) -> str:
        """Show help message"""
        return """**Alfred Commands:**

**Model Management:**
  `/model` - Show current model and available options
  `/model <name>` - Switch to a different model
    Examples: gpt-4o, claude-3-5-sonnet-20241022, gemini-pro

**Mode Control:**
  `/mode` - Show current operating mode
  `/team <task>` - Force team orchestration mode

**History:**
  `/history` - Show recent conversation history
  `/clear` - Clear conversation history

**Help:**
  `/help` - Show this help message

**Tips:**
- Alfred automatically selects the best mode for your task
- Complex tasks trigger team mode automatically
- Use /model to switch between OpenAI, Claude, and Gemini
"""

    async def _add_to_history(self, role: str, content: str):
        """Add message to conversation history and database"""
        # Add to in-memory history
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

        # Add to database
        db = await get_db_manager()
        await db.add_conversation(
            session_id=self.session_id,
            role=role,
            content=content
        )

        # Store in vector memory if enabled
        if self.settings.enable_agent_memory:
            vector = get_vector_manager()
            vector.add_memory(
                collection_name=f"session_{self.session_id}",
                documents=[content],
                metadatas=[{
                    "role": role,
                    "timestamp": datetime.now().isoformat()
                }]
            )

    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Alfred shutting down", session_id=self.session_id)

        # Log session end
        db = await get_db_manager()
        await db.add_conversation(
            session_id=self.session_id,
            role="system",
            content="Session ended",
            metadata={"ended_at": datetime.now().isoformat()}
        )

    def get_session_id(self) -> str:
        """Get current session ID"""
        return self.session_id

    def get_conversation_count(self) -> int:
        """Get conversation message count"""
        return len(self.conversation_history)

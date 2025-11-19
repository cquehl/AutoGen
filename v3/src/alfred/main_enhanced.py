"""
Suntory v3 - Enhanced Alfred Main Module
Core Alfred orchestration with streaming, cost tracking, and error handling
"""

import asyncio
import uuid
from datetime import datetime
from typing import AsyncIterator, List, Optional

from ..core import (
    get_cost_tracker,
    get_db_manager,
    get_logger,
    get_settings,
    get_vector_manager,
    handle_exception,
    log_error,
    set_correlation_id,
    stream_completion,
    SuntoryError,
)
from .modes import AlfredMode, get_direct_mode, get_team_mode
from .personality import get_alfred_personality

logger = get_logger(__name__)


class AlfredEnhanced:
    """
    Enhanced Alfred - The Distinguished AI Concierge

    Production-grade features:
    - Streaming responses for real-time feedback
    - Comprehensive error handling with recovery
    - Cost tracking and budget enforcement
    - Better mode selection
    - Enhanced command set
    """

    def __init__(self):
        self.settings = get_settings()
        self.personality = get_alfred_personality()
        self.direct_mode = get_direct_mode()
        self.team_mode = get_team_mode()
        self.cost_tracker = get_cost_tracker()

        # Session management
        self.session_id = str(uuid.uuid4())
        self.conversation_history: List[dict] = []
        self.current_mode = AlfredMode.DIRECT

        logger.info(
            "Alfred Enhanced initialized",
            session_id=self.session_id,
            model=self.settings.default_model
        )

    async def initialize(self):
        """Initialize Alfred and required services"""
        logger.info("Initializing Alfred Enhanced and services...")

        try:
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

            logger.info("Alfred Enhanced ready", session_id=self.session_id)

        except Exception as e:
            error = handle_exception(e)
            log_error(error)
            raise error

    async def greet(self) -> str:
        """
        Generate and return Alfred's greeting.

        Returns:
            Greeting message
        """
        try:
            greeting = await self.personality.get_greeting()

            # Log greeting
            await self._add_to_history("assistant", greeting)

            return greeting

        except Exception as e:
            error = handle_exception(e)
            log_error(error)
            # Fallback to simple greeting
            return "Good day. Alfred at your service. How may I assist you?"

    async def process_message_streaming(
        self,
        user_message: str,
        force_mode: Optional[AlfredMode] = None
    ) -> AsyncIterator[str]:
        """
        Process user message with streaming response.

        Args:
            user_message: User's input
            force_mode: Force specific mode (optional)

        Yields:
            Response tokens as they arrive
        """
        correlation_id = set_correlation_id()

        logger.info(
            "Processing user message (streaming)",
            correlation_id=correlation_id,
            message_length=len(user_message)
        )

        try:
            # Add to history
            await self._add_to_history("user", user_message)

            # Check for commands (non-streaming)
            if user_message.startswith("/"):
                response = await self._handle_command(user_message)
                yield response
                return

            # Determine mode
            if force_mode:
                mode = force_mode
            elif self.direct_mode.should_use_team_mode(user_message):
                mode = AlfredMode.TEAM
            else:
                mode = AlfredMode.DIRECT

            self.current_mode = mode

            # Show mode selection
            if mode == AlfredMode.TEAM:
                yield "\n🤝 **Team Mode Activated** - Assembling specialists...\n\n"
            else:
                yield "\n💭 "

            # Process based on mode
            full_response = ""

            if mode == AlfredMode.DIRECT:
                async for token in self._process_direct_streaming(user_message):
                    full_response += token
                    yield token
            else:
                # Team mode doesn't stream yet (multi-agent complexity)
                response = await self._process_team(user_message)
                full_response = response
                yield response

            # Add response to history
            await self._add_to_history("assistant", full_response)

            # Show cost at end
            if self.cost_tracker.session_costs:
                last_cost = self.cost_tracker.session_costs[-1]
                yield f"\n\n{self.cost_tracker.format_cost_display(last_cost)}"

        except SuntoryError as e:
            log_error(e)
            yield "\n\n"
            yield e.format_for_user()

        except Exception as e:
            error = handle_exception(e)
            log_error(error)
            yield "\n\n"
            yield error.format_for_user()

    async def process_message(
        self,
        user_message: str,
        force_mode: Optional[AlfredMode] = None
    ) -> str:
        """
        Process user message (non-streaming fallback).

        Args:
            user_message: User's input
            force_mode: Force specific mode (optional)

        Returns:
            Alfred's response
        """
        # Collect streaming response
        response_parts = []
        async for token in self.process_message_streaming(user_message, force_mode):
            response_parts.append(token)

        return "".join(response_parts)

    async def _process_direct_streaming(self, message: str) -> AsyncIterator[str]:
        """Process message in direct mode with streaming"""
        system_message = self.personality.get_system_message()

        # Build message history
        messages = [{"role": "system", "content": system_message}]

        # Add context (last 10 messages)
        for entry in self.conversation_history[-10:]:
            if entry["role"] in ["user", "assistant"]:
                messages.append({
                    "role": entry["role"],
                    "content": entry["content"]
                })

        # Add current message
        messages.append({"role": "user", "content": message})

        # Stream response
        async for token in stream_completion(messages):
            yield token

    async def _process_team(self, message: str) -> str:
        """Process message in team orchestrator mode"""
        # Add preamble about team assembly
        preamble = (
            "Certainly. I'm coordinating a team of specialists for this task.\n\n"
        )

        # Process with team
        try:
            team_response = await self.team_mode.process(
                task_description=message,
                max_turns=self.settings.max_team_turns
            )

            return preamble + team_response

        except Exception as e:
            error = handle_exception(e)
            log_error(error)
            return preamble + error.format_for_user()

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

        try:
            if cmd == "/model":
                return await self._cmd_switch_model(args)
            elif cmd == "/team":
                if args:
                    # Trigger streaming with team mode
                    response_parts = []
                    async for token in self.process_message_streaming(args, force_mode=AlfredMode.TEAM):
                        response_parts.append(token)
                    return "".join(response_parts)
                else:
                    return "Please provide a task description. Example: /team Build a data pipeline"
            elif cmd == "/mode":
                return self._cmd_show_mode()
            elif cmd == "/cost":
                return self._cmd_show_cost()
            elif cmd == "/budget":
                return await self._cmd_set_budget(args)
            elif cmd == "/history":
                return await self._cmd_show_history()
            elif cmd == "/help":
                return self._cmd_help()
            elif cmd == "/clear":
                return await self._cmd_clear_history()
            else:
                return f"Unknown command: {cmd}. Type /help for available commands."

        except Exception as e:
            error = handle_exception(e)
            log_error(error)
            return error.format_for_user()

    async def _cmd_switch_model(self, model_name: str) -> str:
        """Switch LLM model"""
        if not model_name:
            from ..core import get_llm_gateway
            gateway = get_llm_gateway()
            current = gateway.get_current_model()
            available = self.settings.get_available_providers()
            return (
                f"**Current model:** {current}\n"
                f"**Available providers:** {', '.join(available)}\n\n"
                "**Usage:** `/model <model_name>`\n\n"
                "**Examples:**\n"
                "  • `/model gpt-4o` - Fast and capable\n"
                "  • `/model claude-3-5-sonnet-20241022` - Best for reasoning\n"
                "  • `/model gemini-pro` - Cost-effective"
            )

        try:
            from ..core import get_llm_gateway
            gateway = get_llm_gateway()
            previous = gateway.switch_model(model_name)
            return f"✓ Switched from {previous} to {model_name}."
        except Exception as e:
            error = handle_exception(e)
            return error.format_for_user()

    def _cmd_show_mode(self) -> str:
        """Show current mode"""
        return (
            f"**Current mode:** {self.current_mode.value}\n\n"
            "**Mode Descriptions:**\n"
            "  • **Direct Mode**: Alfred handles queries directly (fast)\n"
            "  • **Team Mode**: Specialist agents collaborate (thorough)\n\n"
            "Alfred automatically selects the best mode based on task complexity.\n"
            "Use `/team <task>` to force team mode."
        )

    def _cmd_show_cost(self) -> str:
        """Show cost summary"""
        return self.cost_tracker.get_summary()

    async def _cmd_set_budget(self, args: str) -> str:
        """Set budget limit"""
        if not args:
            return (
                "**Budget Management:**\n\n"
                "**Current limits:**\n"
                f"  • Daily: ${self.cost_tracker.daily_limit:.2f}\n"
                f"  • Monthly: ${self.cost_tracker.monthly_limit:.2f}\n\n"
                "**Usage:** `/budget <daily|monthly> <amount>`\n\n"
                "**Examples:**\n"
                "  • `/budget daily 5.00` - Set $5 daily limit\n"
                "  • `/budget monthly 50.00` - Set $50 monthly limit"
            )

        parts = args.split()
        if len(parts) != 2:
            return "Usage: `/budget <daily|monthly> <amount>`"

        period, amount_str = parts

        try:
            amount = float(amount_str)

            if period == "daily":
                self.cost_tracker.set_daily_limit(amount)
                return f"✓ Daily budget limit set to ${amount:.2f}"
            elif period == "monthly":
                self.cost_tracker.set_monthly_limit(amount)
                return f"✓ Monthly budget limit set to ${amount:.2f}"
            else:
                return f"Unknown period: {period}. Use 'daily' or 'monthly'."

        except ValueError:
            return f"Invalid amount: {amount_str}. Must be a number."

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
            timestamp = entry.get("timestamp", "")
            if timestamp:
                history_lines.append(f"**{role}** ({timestamp}): {content}")
            else:
                history_lines.append(f"**{role}**: {content}")

        return "\n".join(history_lines)

    async def _cmd_clear_history(self) -> str:
        """Clear conversation history"""
        self.conversation_history.clear()
        return "✓ Conversation history cleared. Starting fresh."

    def _cmd_help(self) -> str:
        """Show help message"""
        return """**Alfred Commands:**

**Model Management:**
  `/model` - Show current model and available options
  `/model <name>` - Switch to a different model

**Cost Management:**
  `/cost` - Show cost summary and breakdown
  `/budget` - Show current budget limits
  `/budget <daily|monthly> <amount>` - Set budget limit

**Mode Control:**
  `/mode` - Show current operating mode
  `/team <task>` - Force team orchestration mode

**History:**
  `/history` - Show recent conversation history
  `/clear` - Clear conversation history

**Help:**
  `/help` - Show this help message

**Tips:**
- Alfred streams responses in real-time
- Costs are displayed after each request
- Budget limits prevent overspending
- Complex tasks automatically trigger team mode
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
        try:
            db = await get_db_manager()
            await db.add_conversation(
                session_id=self.session_id,
                role=role,
                content=content
            )
        except Exception as e:
            logger.warning(f"Failed to save to database: {e}")

        # Store in vector memory if enabled
        if self.settings.enable_agent_memory:
            try:
                vector = get_vector_manager()
                vector.add_memory(
                    collection_name=f"session_{self.session_id}",
                    documents=[content],
                    metadatas=[{
                        "role": role,
                        "timestamp": datetime.now().isoformat()
                    }]
                )
            except Exception as e:
                logger.warning(f"Failed to save to vector store: {e}")

    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Alfred Enhanced shutting down", session_id=self.session_id)

        try:
            # Log session end
            db = await get_db_manager()
            await db.add_conversation(
                session_id=self.session_id,
                role="system",
                content="Session ended",
                metadata={
                    "ended_at": datetime.now().isoformat(),
                    "total_cost": self.cost_tracker.get_session_total()
                }
            )

            # Show final cost summary
            if self.cost_tracker.session_costs:
                logger.info(
                    "Session cost summary",
                    total_cost=self.cost_tracker.get_session_total(),
                    total_requests=len(self.cost_tracker.session_costs)
                )

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    def get_session_id(self) -> str:
        """Get current session ID"""
        return self.session_id

    def get_conversation_count(self) -> int:
        """Get conversation message count"""
        return len(self.conversation_history)

    def get_session_cost(self) -> float:
        """Get total cost for this session"""
        return self.cost_tracker.get_session_total()


# Alias for backward compatibility
Alfred = AlfredEnhanced

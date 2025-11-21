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
from .preference_errors import PreferenceStorageError
from .user_preferences import UserPreferencesManager, get_privacy_notice

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

        self.session_id = str(uuid.uuid4())
        self.conversation_history: List[dict] = []
        self.current_mode = AlfredMode.DIRECT

        self.preferences_manager = UserPreferencesManager(self.session_id)

        logger.info(
            "Alfred Enhanced initialized",
            session_id=self.session_id,
            model=self.settings.default_model
        )

    async def initialize(self):
        """Initialize Alfred and required services"""
        logger.info("Initializing Alfred Enhanced and services...")

        try:
            db = await get_db_manager()
            vector = get_vector_manager()
            self.preferences_manager.load_from_storage()

            await db.add_conversation(
                session_id=self.session_id,
                role="system",
                content="Session started",
                metadata={
                    "model": self.settings.default_model,
                    "environment": self.settings.environment.value
                }
            )

            logger.info(
                "Alfred Enhanced ready",
                session_id=self.session_id,
                user_preferences=self.preferences_manager.get_preferences()
            )

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
            await self._add_to_history("assistant", greeting)
            return greeting

        except Exception as e:
            error = handle_exception(e)
            log_error(error)
            return "Good day. Alfred at your service. How may I assist you?"

    async def handle_message(
        self,
        user_message: str,
        force_mode: Optional[AlfredMode] = None
    ) -> str:
        """
        Non-streaming convenience method for message processing.
        Useful for testing, API usage, and programmatic interactions.

        Args:
            user_message: User's input
            force_mode: Force specific mode (optional)

        Returns:
            Complete response as string
        """
        response = ""
        async for token in self.process_message_streaming(user_message, force_mode):
            response += token
        return response

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
            await self._add_to_history("user", user_message)

            try:
                updated_prefs = await self.preferences_manager.update_from_message_async(user_message)
                if updated_prefs:
                    # Acknowledge preference update (only show what changed)
                    confirmation = self.preferences_manager.get_confirmation_message(
                        updated_prefs
                    )
                    if confirmation:
                        yield confirmation + "\n\n"
            except PreferenceStorageError as e:
                # Storage failed - warn user but continue
                logger.error(f"Preference storage error: {e}")
                yield f"\n{e.format_for_user()}\n\n"

            if user_message.startswith("/"):
                response = await self._handle_command(user_message)
                yield response
                return

            if force_mode:
                mode = force_mode
            elif self.direct_mode.should_use_team_mode(user_message):
                mode = AlfredMode.TEAM
            else:
                mode = AlfredMode.DIRECT

            self.current_mode = mode

            if mode == AlfredMode.TEAM:
                yield "\n🤝 **Team Mode Activated** - Assembling specialists...\n\n"
            else:
                yield "\n💭 "

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

            await self._add_to_history("assistant", full_response)

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
        response_parts = []
        async for token in self.process_message_streaming(user_message, force_mode):
            response_parts.append(token)

        return "".join(response_parts)

    async def _process_direct_streaming(self, message: str) -> AsyncIterator[str]:
        """Process message in direct mode with streaming"""
        user_prefs = self.preferences_manager.get_preferences()
        system_message = self.personality.get_system_message(user_prefs)

        messages = [{"role": "system", "content": system_message}]

        # Add context (last 10 messages)
        for entry in self.conversation_history[-10:]:
            if entry["role"] in ["user", "assistant"]:
                messages.append({
                    "role": entry["role"],
                    "content": entry["content"]
                })

        messages.append({"role": "user", "content": message})

        async for token in stream_completion(messages):
            yield token

    async def _process_team(self, message: str) -> str:
        """Process message in team orchestrator mode"""
        preamble = (
            "Certainly. I'm coordinating a team of specialists for this task.\n\n"
        )

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
            elif cmd == "/agent":
                return self._cmd_agent(args)
            elif cmd == "/team":
                if args:
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
            elif cmd == "/preferences":
                return await self._cmd_preferences(args)
            elif cmd == "/privacy":
                return get_privacy_notice()
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

    def _cmd_agent(self, args: str) -> str:
        """Show available agents or agent details"""
        from ..interface.autocomplete import SuntoryCompleter

        if not args:
            result = "**Available Agents:**\n\n"
            result += "**Specialist Agents:**\n"
            for agent in ["engineer", "qa", "product", "ux", "data", "security", "ops"]:
                desc = SuntoryCompleter.AGENTS[agent]
                result += f"  • `{agent}` - {desc}\n"

            result += "\n**Magentic-One Agents:**\n"
            for agent in ["web_surfer", "file_surfer", "coder", "terminal"]:
                desc = SuntoryCompleter.AGENTS[agent]
                result += f"  • `{agent}` - {desc}\n"

            result += "\n**Usage:**\n"
            result += "  • `/agent <name>` - Get details about specific agent\n"
            result += "  • Type `/agent ` and press Tab for autocomplete\n"
            result += "  • Use `/team <task>` to activate team orchestration mode\n"

            return result
        else:
            agent_name = args.strip().lower()
            if agent_name in SuntoryCompleter.AGENTS:
                desc = SuntoryCompleter.AGENTS[agent_name]

                category = "Magentic-One" if agent_name in ["web_surfer", "file_surfer", "coder", "terminal"] else "Specialist"

                return (
                    f"**Agent: {agent_name}**\n"
                    f"**Category:** {category}\n\n"
                    f"{desc}\n\n"
                    f"✓ Available for team mode orchestration\n"
                    f"✓ Use `/team <your task>` to activate"
                )
            else:
                return f"Unknown agent: `{agent_name}`\n\nUse `/agent` to see all available agents."

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

    async def _cmd_preferences(self, args: str) -> str:
        """
        Manage user preferences.

        Subcommands:
          /preferences view - Show current preferences
          /preferences set <key>=<value> - Manually set a preference
          /preferences reset - Clear all preferences
        """
        if not args:
            args = "view"  # Default to view

        parts = args.split(maxsplit=1)
        subcmd = parts[0].lower()

        if subcmd == "view":
            prefs = self.preferences_manager.get_preferences()
            if not prefs:
                return "**No preferences set yet.**\n\nTell me how you'd like to be addressed!"

            result = "**Your Preferences:**\n\n"
            pref_labels = {
                "gender": "Address as",
                "name": "Name",
                "formality": "Formality",
                "title": "Title",
                "timezone": "Timezone",
                "communication_style": "Style"
            }

            for key, value in prefs.items():
                label = pref_labels.get(key, key.title())
                # Format gender as sir/madam
                if key == "gender":
                    display_value = "sir" if value == "male" else "madam" if value == "female" else value
                else:
                    display_value = value
                result += f"  • **{label}:** {display_value}\n"

            result += "\n**Commands:**\n"
            result += "  • `/preferences set <key>=<value>` - Update a preference\n"
            result += "  • `/preferences reset` - Clear all preferences\n"

            return result

        elif subcmd == "set":
            if len(parts) < 2:
                return (
                    "**Usage:** `/preferences set <key>=<value>`\n\n"
                    "**Examples:**\n"
                    "  • `/preferences set gender=male`\n"
                    "  • `/preferences set name=Charles`\n"
                    "  • `/preferences set formality=formal`\n\n"
                    "**Valid keys:**\n"
                    "  • `gender` (male/female/non-binary)\n"
                    "  • `name` (any name)\n"
                    "  • `formality` (casual/formal/very_formal)\n"
                    "  • `title` (Mr./Dr./Professor/etc.)\n"
                    "  • `communication_style` (concise/detailed/balanced)"
                )

            # Parse key=value
            try:
                key_value = parts[1]
                if "=" not in key_value:
                    return "Invalid format. Use: `/preferences set key=value`"

                key, value = key_value.split("=", 1)
                key = key.strip()
                value = value.strip()

                # Validate key
                valid_keys = ["gender", "name", "formality", "title", "timezone", "communication_style"]
                if key not in valid_keys:
                    return f"Invalid key '{key}'. Valid keys: {', '.join(valid_keys)}"

                # FIX: Sanitize value before storing - security issue
                from ..alfred.input_sanitization import sanitize_preference_value
                sanitized_value = sanitize_preference_value(value, max_length=100)
                if not sanitized_value:
                    return f"Invalid value for '{key}'. Please check your input and avoid special characters."

                # Update preference with sanitized value
                old_value = self.preferences_manager.preferences.get(key)
                self.preferences_manager.preferences[key] = sanitized_value
                self.preferences_manager._save_to_storage()

                if old_value:
                    return f"✓ Updated **{key}** from '{old_value}' to '{sanitized_value}'"
                else:
                    return f"✓ Set **{key}** to '{sanitized_value}'"

            except Exception as e:
                return f"Error setting preference: {e}"

        elif subcmd == "reset":
            self.preferences_manager.preferences.clear()
            try:
                self.preferences_manager._delete_existing_preferences()
                return "✓ All preferences cleared. Tell me how you'd like to be addressed!"
            except Exception as e:
                return f"✓ Preferences cleared from memory (storage cleanup failed: {e})"

        else:
            return f"Unknown subcommand '{subcmd}'. Use: view, set, or reset"

    def _cmd_help(self) -> str:
        """Show help message"""
        return """**◆ ALFRED COMMAND REFERENCE**

**🤖 Agent Management:**
  `/agent` - List all available agents (11 specialists)
  `/agent <name>` - Get details about a specific agent
  `/team <task>` - Force team orchestration mode for complex tasks

**🧠 Model Management:**
  `/model` - Show current model and available providers
  `/model <name>` - Switch to a different LLM model

**💰 Cost Management:**
  `/cost` - Show detailed cost summary and breakdown
  `/budget` - Display current budget limits
  `/budget <daily|monthly> <amount>` - Set spending limits

**👤 Preferences & Privacy:**
  `/preferences` - View your current preferences
  `/preferences set <key>=<value>` - Set a preference manually
  `/preferences reset` - Clear all preferences
  `/privacy` - View privacy notice and data handling policy

**⚙️ Mode & History:**
  `/mode` - Show current operating mode (Direct/Team)
  `/history` - View recent conversation history
  `/clear` - Clear conversation history and start fresh

**❓ Help:**
  `/help` - Show this command reference

**💡 Pro Tips:**
  • **Autocomplete:** Press Tab while typing commands to see suggestions
  • **Streaming:** Responses stream in real-time for faster feedback
  • **Cost Tracking:** See API costs after each request automatically
  • **Smart Routing:** Complex tasks auto-trigger team mode
  • **Double Ctrl-C:** Press Ctrl-C twice to exit gracefully
  • **Budget Safety:** Set limits to prevent surprise API bills
  • **Preferences:** Tell me how you want to be addressed naturally, or use `/preferences`

**📚 Examples:**
  `/model gpt-4o` - Switch to GPT-4 Omni
  `/agent engineer` - View Software Engineer agent details
  `/team Build a REST API with authentication` - Activate team mode
  `/budget daily 5.00` - Set $5 daily spending limit
  `/preferences set name=Master Charles` - Set your preferred name

**Need more help?** Just ask Alfred naturally - "What can you do?" or "How does team mode work?"
"""

    async def _add_to_history(self, role: str, content: str):
        """Add message to conversation history and database"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

        try:
            db = await get_db_manager()
            await db.add_conversation(
                session_id=self.session_id,
                role=role,
                content=content
            )
        except Exception as e:
            logger.warning(f"Failed to save to database: {e}")

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

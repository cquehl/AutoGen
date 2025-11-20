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
from .command_handler import CommandHandler
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

        # Session management
        self.session_id = str(uuid.uuid4())
        self.conversation_history: List[dict] = []
        self.current_mode = AlfredMode.DIRECT

        # User preferences manager
        self.preferences_manager = UserPreferencesManager(self.session_id)

        # Command handler (extracted for separation of concerns)
        self.command_handler = CommandHandler(self)

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

            # Load user preferences from previous sessions
            self.preferences_manager.load_from_storage()

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

            # Log greeting
            await self._add_to_history("assistant", greeting)

            return greeting

        except Exception as e:
            error = handle_exception(e)
            log_error(error)
            # Fallback to simple greeting
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
            # Add to history
            await self._add_to_history("user", user_message)

            # Update user preferences from message (async version with LLM extraction)
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
        # Get user preferences and inject into system message
        user_prefs = self.preferences_manager.get_preferences()
        system_message = self.personality.get_system_message(user_prefs)

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
        Handle special commands (delegated to CommandHandler).

        Args:
            command: Command string (starts with /)

        Returns:
            Command response
        """
        logger.info(f"Handling command: {command}")

        try:
            return await self.command_handler.handle(command)
        except Exception as e:
            error = handle_exception(e)
            log_error(error)
            return error.format_for_user()

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

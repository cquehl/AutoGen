"""
Command Handler for Alfred Enhanced
Extracted from main_enhanced.py to reduce God Class complexity

This module handles all /command processing, allowing AlfredEnhanced
to focus on message orchestration and streaming.
"""

from typing import Tuple
from .user_preferences import get_privacy_notice


class CommandHandler:
    """
    Handles all command processing for Alfred.

    Responsibilities:
    - Parse command strings
    - Dispatch to appropriate command handlers
    - Format command responses
    - Maintain clean separation from AlfredEnhanced orchestration
    """

    def __init__(self, alfred):
        """
        Initialize command handler.

        Args:
            alfred: Reference to AlfredEnhanced instance for context access
        """
        self.alfred = alfred

    def _parse_command(self, command: str) -> Tuple[str, str]:
        """
        Parse command into command name and arguments.

        Args:
            command: Full command string (e.g., "/model gpt-4")

        Returns:
            Tuple of (command, arguments)
        """
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        return cmd, args

    async def handle(self, command: str) -> str:
        """
        Handle command execution.

        Args:
            command: Command string (starts with /)

        Returns:
            Command response
        """
        cmd, args = self._parse_command(command)

        # Dispatch table (cleaner than if/elif chain)
        handlers = {
            "/model": self.model_command,
            "/agent": self.agent_command,
            "/team": self.team_command,
            "/mode": self.mode_command,
            "/cost": self.cost_command,
            "/budget": self.budget_command,
            "/history": self.history_command,
            "/preferences": self.preferences_command,
            "/privacy": self.privacy_command,
            "/help": self.help_command,
            "/clear": self.clear_command,
        }

        handler = handlers.get(cmd)
        if not handler:
            return f"Unknown command: {cmd}. Type /help for available commands."

        return await handler(args)

    # ========================================================================
    # COMMAND IMPLEMENTATIONS
    # ========================================================================

    async def model_command(self, args: str) -> str:
        """Handle /model command"""
        if not args:
            from ..core import get_llm_gateway
            gateway = get_llm_gateway()
            current = gateway.get_current_model()
            available = self.alfred.settings.get_available_providers()
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
            from ..core import get_llm_gateway, handle_exception
            gateway = get_llm_gateway()
            previous = gateway.switch_model(args)
            return f"✓ Switched from {previous} to {args}."
        except Exception as e:
            from ..core import handle_exception
            error = handle_exception(e)
            return error.format_for_user()

    def agent_command(self, args: str) -> str:
        """Handle /agent command"""
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

    async def team_command(self, args: str) -> str:
        """Handle /team command"""
        if args:
            # Trigger streaming with team mode
            from .modes import AlfredMode
            response_parts = []
            async for token in self.alfred.process_message_streaming(args, force_mode=AlfredMode.TEAM):
                response_parts.append(token)
            return "".join(response_parts)
        else:
            return "Please provide a task description. Example: /team Build a data pipeline"

    def mode_command(self, args: str) -> str:
        """Handle /mode command"""
        return (
            f"**Current mode:** {self.alfred.current_mode.value}\n\n"
            "**Mode Descriptions:**\n"
            "  • **Direct Mode**: Alfred handles queries directly (fast)\n"
            "  • **Team Mode**: Specialist agents collaborate (thorough)\n\n"
            "Alfred automatically selects the best mode based on task complexity.\n"
            "Use `/team <task>` to force team mode."
        )

    def cost_command(self, args: str) -> str:
        """Handle /cost command"""
        return self.alfred.cost_tracker.get_summary()

    async def budget_command(self, args: str) -> str:
        """Handle /budget command"""
        if not args:
            return (
                "**Budget Management:**\n\n"
                "**Current limits:**\n"
                f"  • Daily: ${self.alfred.cost_tracker.daily_limit:.2f}\n"
                f"  • Monthly: ${self.alfred.cost_tracker.monthly_limit:.2f}\n\n"
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
                self.alfred.cost_tracker.set_daily_limit(amount)
                return f"✓ Daily budget limit set to ${amount:.2f}"
            elif period == "monthly":
                self.alfred.cost_tracker.set_monthly_limit(amount)
                return f"✓ Monthly budget limit set to ${amount:.2f}"
            else:
                return f"Unknown period: {period}. Use 'daily' or 'monthly'."

        except ValueError:
            return f"Invalid amount: {amount_str}. Must be a number."

    async def history_command(self, args: str) -> str:
        """Handle /history command"""
        if not self.alfred.conversation_history:
            return "No conversation history yet."

        history_lines = ["**Recent Conversation:**\n"]

        for entry in self.alfred.conversation_history[-10:]:
            role = entry["role"].capitalize()
            content = entry["content"][:100]
            if len(entry["content"]) > 100:
                content += "..."
            timestamp = entry.get("timestamp", "")
            if timestamp:
                history_lines.append(f"**{role}** ({timestamp}): {content}")
            else:
                history_lines.append(f"**{role}**: {content}")

        return "\n".join(history_lines)

    async def clear_command(self, args: str) -> str:
        """Handle /clear command"""
        self.alfred.conversation_history.clear()
        return "✓ Conversation history cleared. Starting fresh."

    async def preferences_command(self, args: str) -> str:
        """Handle /preferences command"""
        if not args:
            args = "view"

        parts = args.split(maxsplit=1)
        subcmd = parts[0].lower()

        if subcmd == "view":
            prefs = self.alfred.preferences_manager.get_preferences()
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
                    "  • `/preferences set name=Charles`\n\n"
                    "**Valid keys:**\n"
                    "  • `gender` (male/female/non-binary)\n"
                    "  • `name` (any name)\n"
                    "  • `formality` (casual/formal/very_formal)"
                )

            try:
                key_value = parts[1]
                if "=" not in key_value:
                    return "Invalid format. Use: `/preferences set key=value`"

                key, value = key_value.split("=", 1)
                key = key.strip()
                value = value.strip()

                valid_keys = ["gender", "name", "formality", "title", "timezone", "communication_style"]
                if key not in valid_keys:
                    return f"Invalid key '{key}'. Valid keys: {', '.join(valid_keys)}"

                # Update preference using public API
                old_value = self.alfred.preferences_manager.preferences.get(key)
                self.alfred.preferences_manager.preferences[key] = value
                self.alfred.preferences_manager.save()  # Use public method!

                if old_value:
                    return f"✓ Updated **{key}** from '{old_value}' to '{value}'"
                else:
                    return f"✓ Set **{key}** to '{value}'"

            except Exception as e:
                return f"Error setting preference: {e}"

        elif subcmd == "reset":
            self.alfred.preferences_manager.clear()  # Use public method!
            return "✓ All preferences cleared. Tell me how you'd like to be addressed!"

        else:
            return f"Unknown subcommand '{subcmd}'. Use: view, set, or reset"

    def privacy_command(self, args: str) -> str:
        """Handle /privacy command"""
        return get_privacy_notice()

    def help_command(self, args: str) -> str:
        """Handle /help command"""
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
  • **Autocomplete:** Press Tab while typing commands
  • **Streaming:** Responses stream in real-time
  • **Cost Tracking:** See API costs after each request
  • **Smart Routing:** Complex tasks auto-trigger team mode
  • **Budget Safety:** Set limits to prevent surprise bills

**📚 Examples:**
  `/model gpt-4o` - Switch to GPT-4 Omni
  `/agent engineer` - View Software Engineer agent
  `/team Build a REST API` - Activate team mode
  `/budget daily 5.00` - Set $5 daily limit
  `/preferences set name=Charles` - Set your name

**Need more help?** Just ask Alfred naturally!
"""

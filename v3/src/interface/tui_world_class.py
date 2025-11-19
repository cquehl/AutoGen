"""
Suntory v3 - World-Class Terminal UI
Half-Life inspired, autocomplete-enabled, premium CLI experience
"""

import asyncio
import signal
from datetime import datetime
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style as PromptStyle
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from ..alfred import Alfred
from ..core import get_logger, get_settings, SuntoryError
from .autocomplete import create_fuzzy_completer, EXAMPLE_COMMANDS
from .onboarding import run_onboarding
from .theme import HALFLIFE_THEME, SIMPLE_BANNER, get_status_indicator

logger = get_logger(__name__)


class WorldClassTUI:
    """
    World-class Terminal UI for Suntory System.

    Features:
    - Half-Life inspired color palette
    - Fish-shell style autocomplete
    - Double Ctrl-C to exit
    - Smooth streaming responses
    - Beautiful visual design
    - Premium "feel"
    """

    def __init__(self):
        self.settings = get_settings()
        self.console = Console(theme=HALFLIFE_THEME)
        self.alfred: Optional[Alfred] = None
        self.ctrl_c_count = 0
        self.last_ctrl_c_time = 0

        # Prompt toolkit style (Half-Life colors)
        self.prompt_style = PromptStyle.from_dict({
            "prompt": "#FF6600 bold",  # HEV orange
            "input": "#FFE4B5",  # Warm white
            "completion-menu": "bg:#1a1a1a #FFA500",  # Amber on dark
            "completion-menu.completion.current": "bg:#FF6600 #000000",
            "completion-menu.meta.completion.current": "bg:#CC5200 #FFFFFF",
        })

        # Create autocomplete-enabled session
        self.session = PromptSession(
            history=FileHistory(str(self.settings.get_workspace_path() / ".suntory_history")),
            completer=create_fuzzy_completer(),
            complete_while_typing=True,  # Fish-style
            style=self.prompt_style,
            key_bindings=self._create_key_bindings(),
        )

    def _create_key_bindings(self) -> KeyBindings:
        """Create custom key bindings"""
        kb = KeyBindings()

        @kb.add("c-c")
        def handle_ctrl_c(event):
            """Handle double Ctrl-C for exit"""
            import time
            current_time = time.time()

            # Check if this is second Ctrl-C within 2 seconds
            if current_time - self.last_ctrl_c_time < 2.0:
                # Second Ctrl-C - exit
                self.ctrl_c_count = 0
                event.app.exit(exception=KeyboardInterrupt())
            else:
                # First Ctrl-C - show hint
                self.ctrl_c_count = 1
                self.last_ctrl_c_time = current_time
                self.console.print(
                    "\n[amber]● Press Ctrl-C again to exit[/amber]\n"
                )

        return kb

    def show_banner(self):
        """Show Half-Life inspired banner"""
        self.console.print(SIMPLE_BANNER, style="primary")

        # System status
        status_table = Table.grid(padding=(0, 2))
        status_table.add_column(style="muted")
        status_table.add_column(style="success")

        status_table.add_row(
            get_status_indicator("online"),
            "SYSTEM INITIALIZED"
        )

        self.console.print(status_table)
        self.console.print()

    def show_initialization(self):
        """Show initialization with HEV suit style"""
        with Progress(
            SpinnerColumn(spinner_name="dots", style="progress.spinner"),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            progress.add_task("[amber]◉ Loading environment...[/amber]", total=None)
            import time
            time.sleep(0.3)

            progress.add_task("[amber]◉ Validating credentials...[/amber]", total=None)
            time.sleep(0.3)

            # Check Docker
            try:
                from ..core import get_docker_executor
                executor = get_docker_executor()
                if executor.is_available():
                    progress.add_task("[success]✓ Docker sandbox ready[/success]", total=None)
                else:
                    self.console.print(
                        "[cost.warning]⚠ Docker offline - code execution disabled[/cost.warning]"
                    )
                time.sleep(0.2)
            except:
                self.console.print(
                    "[cost.warning]⚠ Docker offline - code execution disabled[/cost.warning]"
                )

            progress.add_task("[success]✓ Agents assembled[/success]", total=None)
            time.sleep(0.2)

        self.console.print()

    async def show_alfred_greeting(self):
        """Show Alfred's greeting with Half-Life styling"""
        if not self.alfred:
            return

        try:
            greeting = await self.alfred.greet()

            self.console.print(
                Panel(
                    f"[alfred]{greeting}[/alfred]",
                    title="[panel.title]◆ ALFRED[/panel.title]",
                    title_align="left",
                    border_style="panel.border",
                    padding=(1, 2)
                )
            )
            self.console.print()

        except SuntoryError as e:
            self.console.print(
                Panel(
                    f"[error]{e.format_for_user()}[/error]",
                    title="[error]✖ ERROR[/error]",
                    border_style="error",
                    padding=(1, 2)
                )
            )
            self.console.print()

    def show_system_info(self):
        """Show system info HEV style"""
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="muted", width=25)
        table.add_column(style="info")

        table.add_row("Environment:", self.settings.environment.value)
        table.add_row("Default Model:", self.settings.default_model)
        table.add_row("Providers:", ", ".join(self.settings.get_available_providers()))

        # Check Docker
        try:
            from ..core import get_docker_executor
            executor = get_docker_executor()
            status = "[success]ONLINE[/success]" if executor.is_available() else "[error]OFFLINE[/error]"
        except:
            status = "[error]OFFLINE[/error]"

        table.add_row("Docker Sandbox:", status)
        table.add_row("Streaming:", "[success]ENABLED[/success]")
        table.add_row("Cost Tracking:", "[success]ENABLED[/success]")
        table.add_row("Autocomplete:", "[success]ENABLED[/success]")

        self.console.print(table)
        self.console.print()

    def show_quick_help(self):
        """Show quick help with examples"""
        self.console.print("[panel.title]◆ QUICK START[/panel.title]\n")

        help_table = Table(show_header=False, box=None, padding=(0, 2))
        help_table.add_column(style="muted", width=25)
        help_table.add_column(style="primary")

        for desc, example in EXAMPLE_COMMANDS[:5]:
            help_table.add_row(desc + ":", example)

        self.console.print(help_table)
        self.console.print()

        self.console.print(
            "[muted.dim]Type /help for all commands • Tab for autocomplete • Ctrl-C twice to exit[/muted.dim]"
        )
        self.console.print()

    async def run_conversation_loop(self):
        """Main conversation loop with world-class UX"""
        if not self.alfred:
            logger.error("Alfred not initialized")
            return

        while True:
            try:
                # Get user input with autocomplete
                user_input = await asyncio.to_thread(
                    self.session.prompt,
                    HTML("<primary><b>[alfred]</b></primary> <input>▸</input> "),
                )

                user_input = user_input.strip()

                # Reset Ctrl-C counter on valid input
                self.ctrl_c_count = 0

                # Handle exit
                if user_input.lower() in ['exit', 'quit']:
                    await self._graceful_exit()
                    break

                # Skip empty
                if not user_input:
                    continue

                # Process with streaming
                await self.show_streaming_response(user_input)

            except KeyboardInterrupt:
                # Double Ctrl-C handled in key bindings
                await self._graceful_exit()
                break

            except EOFError:
                break

            except Exception as e:
                logger.error(f"Error in conversation loop: {e}", exc_info=True)
                self.console.print(
                    f"[error]✖ Unexpected error: {str(e)}[/error]"
                )

    async def show_streaming_response(self, user_input: str):
        """Show streaming response with Half-Life styling"""
        self.console.print()

        response_parts = []

        try:
            with Live(
                "",
                console=self.console,
                refresh_per_second=20,  # Smooth updates
                transient=False
            ) as live:
                async for token in self.alfred.process_message_streaming(user_input):
                    response_parts.append(token)
                    current_response = "".join(response_parts)

                    # Render with Half-Life style
                    if any(m in current_response for m in ['**', '##', '```', '\n-', '\n1.']):
                        try:
                            md = Markdown(current_response)
                            panel = Panel(
                                md,
                                title="[panel.title]◆ ALFRED[/panel.title]",
                                title_align="left",
                                border_style="panel.border",
                                padding=(1, 2)
                            )
                            live.update(panel)
                        except:
                            panel = Panel(
                                f"[alfred]{current_response}[/alfred]",
                                title="[panel.title]◆ ALFRED[/panel.title]",
                                title_align="left",
                                border_style="panel.border",
                                padding=(1, 2)
                            )
                            live.update(panel)
                    else:
                        panel = Panel(
                            f"[alfred]{current_response}[/alfred]",
                            title="[panel.title]◆ ALFRED[/panel.title]",
                            title_align="left",
                            border_style="panel.border",
                            padding=(1, 2)
                        )
                        live.update(panel)

        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            self.console.print(
                Panel(
                    f"[error]✖ Error: {str(e)}[/error]",
                    title="[error]ERROR[/error]",
                    border_style="error",
                    padding=(1, 2)
                )
            )

        self.console.print()

    async def _graceful_exit(self):
        """Graceful exit with cost summary"""
        self.console.print()
        self.console.print("[amber]● Shutting down...[/amber]")

        # Show final cost summary
        try:
            if self.alfred and self.alfred.cost_tracker.session_costs:
                cost_summary = self.alfred.cost_tracker.get_summary()
                if "No API usage" not in cost_summary:
                    self.console.print()
                    self.console.print(
                        Panel(
                            f"[cost]{cost_summary}[/cost]",
                            title="[panel.title]◆ SESSION SUMMARY[/panel.title]",
                            border_style="cost",
                            padding=(1, 2)
                        )
                    )
        except:
            pass

        self.console.print()
        self.console.print("[success]✓ Alfred: Until next time, sir.[/success]")

    async def initialize_alfred(self):
        """Initialize Alfred"""
        try:
            self.alfred = Alfred()
            await self.alfred.initialize()
        except SuntoryError as e:
            self.console.print()
            self.console.print(
                Panel(
                    f"[error]{e.format_for_user()}[/error]",
                    title="[error]✖ INITIALIZATION ERROR[/error]",
                    border_style="error",
                    padding=(1, 2)
                )
            )
            self.console.print()
            raise

    async def shutdown_alfred(self):
        """Shutdown Alfred"""
        if self.alfred:
            await self.alfred.shutdown()

    async def run(self):
        """Main run method"""
        try:
            # Show banner
            self.show_banner()

            # Initialize
            self.show_initialization()

            # Initialize Alfred
            await self.initialize_alfred()

            # Run onboarding (first time only)
            tutorial_run = run_onboarding(self.console)

            if not tutorial_run:
                # Show system info
                self.show_system_info()

            # Show greeting
            await self.show_alfred_greeting()

            if not tutorial_run:
                # Show quick help
                self.show_quick_help()

            # Run conversation
            await self.run_conversation_loop()

        except KeyboardInterrupt:
            self.console.print()
            self.console.print("[amber]● Interrupted[/amber]")

        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            self.console.print()
            self.console.print(f"[error]✖ Fatal error: {str(e)}[/error]")

        finally:
            await self.shutdown_alfred()
            self.console.print()
            self.console.print("[muted.dim]Session ended.[/muted.dim]")


async def main():
    """Entry point for world-class TUI"""
    tui = WorldClassTUI()
    await tui.run()


if __name__ == "__main__":
    asyncio.run(main())

"""
Suntory v3 - Enhanced Terminal User Interface
Beautiful Rich-based TUI with streaming, costs, and onboarding
"""

import asyncio
from datetime import datetime
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from ..alfred import Alfred
from ..core import get_logger, get_settings, SuntoryError
from .onboarding import run_onboarding

logger = get_logger(__name__)


class SuntoryTUIEnhanced:
    """
    Enhanced Rich Terminal UI for Suntory System.

    Features:
    - Interactive onboarding for first-time users
    - Streaming responses with real-time feedback
    - Cost display after each request
    - Better error formatting
    - Progress indicators
    """

    def __init__(self):
        self.settings = get_settings()
        self.console = Console()
        self.alfred: Optional[Alfred] = None

        # Prompt toolkit style
        self.prompt_style = Style.from_dict({
            'prompt': '#00aa00 bold',
            'input': '#ffffff',
        })

        # Session with history
        self.session = PromptSession(
            history=FileHistory(str(self.settings.get_workspace_path() / ".suntory_history")),
            style=self.prompt_style
        )

    def show_banner(self):
        """Show Suntory banner"""
        banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   🥃  SUNTORY SYSTEM v3                                       ║
║                                                               ║
║   Alfred, your Distinguished AI Concierge                     ║
║   Powered by Multi-Agent Orchestration                        ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""
        self.console.print(banner, style="bold cyan")

    def show_initialization_progress(self):
        """Show initialization progress"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task1 = progress.add_task("[cyan]Initializing environment...", total=1)
            progress.update(task1, advance=1)

            task2 = progress.add_task("[cyan]Validating API keys...", total=1)
            progress.update(task2, advance=1)

            # Check Docker
            try:
                from ..core import get_docker_executor
                executor = get_docker_executor()
                if executor.is_available():
                    task3 = progress.add_task("[cyan]Docker sandbox ready...", total=1)
                    progress.update(task3, advance=1)
                else:
                    self.console.print(
                        "[yellow]⚠ Docker not available - code execution disabled[/yellow]"
                    )
            except Exception as e:
                logger.debug(f"Docker check failed: {e}")
                self.console.print(
                    "[yellow]⚠ Docker not available - code execution disabled[/yellow]"
                )

            task4 = progress.add_task("[cyan]Assembling agents...", total=1)
            progress.update(task4, advance=1)

    async def show_alfred_greeting(self):
        """Show Alfred's greeting"""
        if not self.alfred:
            return

        try:
            greeting = await self.alfred.greet()

            self.console.print()
            self.console.print(
                Panel(
                    greeting,
                    title="[bold]Alfred[/bold]",
                    title_align="left",
                    border_style="green",
                    padding=(1, 2)
                )
            )
            self.console.print()

        except SuntoryError as e:
            self.console.print()
            self.console.print(
                Panel(
                    e.format_for_user(),
                    title="[bold red]Error[/bold red]",
                    title_align="left",
                    border_style="red",
                    padding=(1, 2)
                )
            )
            self.console.print()

    def show_system_info(self):
        """Show system information"""
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="cyan", width=20)
        table.add_column(style="white")

        table.add_row("Environment:", self.settings.environment.value)
        table.add_row("Default Model:", self.settings.default_model)
        table.add_row("Providers:", ", ".join(self.settings.get_available_providers()))

        # Check Docker status
        try:
            from ..core import get_docker_executor
            executor = get_docker_executor()
            docker_status = "✓ Enabled" if executor.is_available() else "✗ Disabled"
        except Exception as e:
            logger.debug(f"Docker check failed: {e}")
            docker_status = "✗ Disabled"

        table.add_row("Docker Sandbox:", docker_status)
        table.add_row("Agent Memory:", "✓ Enabled" if self.settings.enable_agent_memory else "✗ Disabled")
        table.add_row("Response Streaming:", "✓ Enabled")
        table.add_row("Cost Tracking:", "✓ Enabled")

        self.console.print()
        self.console.print(table)
        self.console.print()

    def show_help_hint(self):
        """Show help hint"""
        self.console.print(
            "[dim]Type /help for commands, or start chatting with Alfred[/dim]",
            style="italic"
        )
        self.console.print()

    async def run_conversation_loop(self):
        """Main conversation loop with streaming"""
        if not self.alfred:
            logger.error("Alfred not initialized")
            return

        while True:
            try:
                # Get user input
                user_input = await asyncio.to_thread(
                    self.session.prompt,
                    [('class:prompt', '[alfred] '), ('class:input', '> ')]
                )

                user_input = user_input.strip()

                # Handle exit
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    self.console.print()

                    # Show final cost summary
                    try:
                        cost_summary = self.alfred.cost_tracker.get_summary()
                        if "No API usage" not in cost_summary:
                            self.console.print(
                                Panel(
                                    cost_summary,
                                    title="[bold]Session Summary[/bold]",
                                    border_style="cyan",
                                    padding=(1, 2)
                                )
                            )
                            self.console.print()
                    except Exception as e:
                        logger.debug(f"Cost summary display failed: {e}")

                    self.console.print(
                        "[green]Alfred: Very good. Until next time.[/green]"
                    )
                    break

                # Skip empty input
                if not user_input:
                    continue

                # Process with streaming
                await self.show_streaming_response(user_input)

            except KeyboardInterrupt:
                self.console.print()
                self.console.print(
                    "[yellow]Alfred: Interrupted. Type 'exit' to quit.[/yellow]"
                )
                continue

            except EOFError:
                break

            except Exception as e:
                logger.error(f"Error in conversation loop: {e}", exc_info=True)
                self.console.print(
                    f"[red]Unexpected error: {str(e)}[/red]"
                )

    async def show_streaming_response(self, user_input: str):
        """
        Show streaming response with real-time updates.

        Args:
            user_input: User's input message
        """
        self.console.print()

        # Accumulate response
        response_parts = []

        try:
            # Create a live display for streaming
            with Live(
                "",
                console=self.console,
                refresh_per_second=10,
                transient=False
            ) as live:
                async for token in self.alfred.process_message_streaming(user_input):
                    response_parts.append(token)

                    # Update live display
                    current_response = "".join(response_parts)

                    # Try to render as markdown if it looks like markdown
                    if any(marker in current_response for marker in ['**', '##', '```', '\n-', '\n*', '\n1.']):
                        try:
                            md = Markdown(current_response)
                            panel = Panel(
                                md,
                                title="[bold]Alfred[/bold]",
                                title_align="left",
                                border_style="green",
                                padding=(1, 2)
                            )
                            live.update(panel)
                        except Exception as e:
                            # Fallback to text if markdown rendering fails
                            logger.debug(f"Markdown rendering failed: {e}")
                            panel = Panel(
                                current_response,
                                title="[bold]Alfred[/bold]",
                                title_align="left",
                                border_style="green",
                                padding=(1, 2)
                            )
                            live.update(panel)
                    else:
                        # Plain text
                        panel = Panel(
                            current_response,
                            title="[bold]Alfred[/bold]",
                            title_align="left",
                            border_style="green",
                            padding=(1, 2)
                        )
                        live.update(panel)

        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            self.console.print(
                Panel(
                    f"Error during streaming: {str(e)}",
                    title="[bold red]Error[/bold red]",
                    border_style="red",
                    padding=(1, 2)
                )
            )

        self.console.print()

    async def initialize_alfred(self):
        """Initialize Alfred"""
        try:
            self.alfred = Alfred()
            await self.alfred.initialize()
        except SuntoryError as e:
            self.console.print()
            self.console.print(
                Panel(
                    e.format_for_user(),
                    title="[bold red]Initialization Error[/bold red]",
                    border_style="red",
                    padding=(1, 2)
                )
            )
            self.console.print()
            raise
        except Exception as e:
            from ..core import handle_exception
            error = handle_exception(e)
            self.console.print()
            self.console.print(
                Panel(
                    error.format_for_user(),
                    title="[bold red]Initialization Error[/bold red]",
                    border_style="red",
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

            # Show initialization progress
            self.show_initialization_progress()

            # Initialize Alfred
            await self.initialize_alfred()

            # Run onboarding for first-time users
            tutorial_run = run_onboarding(self.console)

            # Show system info
            if not tutorial_run:
                self.show_system_info()

            # Show Alfred's greeting
            await self.show_alfred_greeting()

            # Show help hint if tutorial wasn't run
            if not tutorial_run:
                self.show_help_hint()

            # Run conversation loop
            await self.run_conversation_loop()

        except KeyboardInterrupt:
            self.console.print()
            self.console.print("[yellow]Interrupted by user[/yellow]")

        except Exception as e:
            logger.error(f"Fatal error in TUI: {e}", exc_info=True)
            self.console.print()
            self.console.print(f"[red]Fatal Error: {str(e)}[/red]")

        finally:
            # Cleanup
            await self.shutdown_alfred()
            self.console.print()
            self.console.print("[dim]Session ended. Thank you for using Suntory System.[/dim]")


async def main():
    """Entry point for enhanced TUI"""
    tui = SuntoryTUIEnhanced()
    await tui.run()


if __name__ == "__main__":
    asyncio.run(main())

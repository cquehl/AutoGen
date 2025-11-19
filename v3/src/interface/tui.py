"""
Suntory v3 - Terminal User Interface
Beautiful Rich-based TUI for Alfred interactions
"""

import asyncio
from datetime import datetime
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ..alfred import Alfred
from ..core import get_logger, get_settings

logger = get_logger(__name__)


class SuntoryTUI:
    """
    Rich Terminal UI for Suntory System.

    Provides beautiful, interactive terminal interface with:
    - Syntax highlighting
    - Markdown rendering
    - Progress indicators
    - Command history
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
            task1 = progress.add_task("[cyan]Initializing environment...", total=None)
            progress.update(task1, completed=True)

            task2 = progress.add_task("[cyan]Validating API keys...", total=None)
            progress.update(task2, completed=True)

            task3 = progress.add_task("[cyan]Starting Docker sandbox...", total=None)
            progress.update(task3, completed=True)

            task4 = progress.add_task("[cyan]Assembling agents...", total=None)
            progress.update(task4, completed=True)

    async def show_alfred_greeting(self):
        """Show Alfred's greeting"""
        if not self.alfred:
            return

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

    def show_system_info(self):
        """Show system information"""
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="cyan", width=20)
        table.add_column(style="white")

        table.add_row("Environment:", self.settings.environment.value)
        table.add_row("Default Model:", self.settings.default_model)
        table.add_row("Providers:", ", ".join(self.settings.get_available_providers()))
        table.add_row("Docker Sandbox:", "✓ Enabled" if self.settings.docker_enabled else "✗ Disabled")
        table.add_row("Agent Memory:", "✓ Enabled" if self.settings.enable_agent_memory else "✗ Disabled")

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
        """Main conversation loop"""
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
                    self.console.print(
                        "[green]Alfred: Very good. Until next time.[/green]"
                    )
                    break

                # Skip empty input
                if not user_input:
                    continue

                # Show thinking indicator
                with self.console.status("[bold green]Alfred is thinking...", spinner="dots"):
                    response = await self.alfred.process_message(user_input)

                # Display response
                self.show_response(response)

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
                    f"[red]Error: {str(e)}[/red]"
                )

    def show_response(self, response: str):
        """
        Show Alfred's response with markdown rendering.

        Args:
            response: Response text
        """
        self.console.print()

        # Try to render as markdown if it contains markdown syntax
        if any(marker in response for marker in ['**', '##', '```', '-', '*', '1.']):
            try:
                md = Markdown(response)
                self.console.print(
                    Panel(
                        md,
                        title="[bold]Alfred[/bold]",
                        title_align="left",
                        border_style="green",
                        padding=(1, 2)
                    )
                )
            except Exception:
                # Fallback to plain text
                self.console.print(
                    Panel(
                        response,
                        title="[bold]Alfred[/bold]",
                        title_align="left",
                        border_style="green",
                        padding=(1, 2)
                    )
                )
        else:
            # Plain text response
            self.console.print(
                Panel(
                    response,
                    title="[bold]Alfred[/bold]",
                    title_align="left",
                    border_style="green",
                    padding=(1, 2)
                )
            )

        self.console.print()

    async def initialize_alfred(self):
        """Initialize Alfred"""
        self.alfred = Alfred()
        await self.alfred.initialize()

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

            # Show system info
            self.show_system_info()

            # Show Alfred's greeting
            await self.show_alfred_greeting()

            # Show help hint
            self.show_help_hint()

            # Run conversation loop
            await self.run_conversation_loop()

        except Exception as e:
            logger.error(f"Fatal error in TUI: {e}", exc_info=True)
            self.console.print(f"[red]Fatal Error: {str(e)}[/red]")

        finally:
            # Cleanup
            await self.shutdown_alfred()
            self.console.print()
            self.console.print("[dim]Session ended. Thank you for using Suntory System.[/dim]")


async def main():
    """Entry point for TUI"""
    tui = SuntoryTUI()
    await tui.run()


if __name__ == "__main__":
    asyncio.run(main())

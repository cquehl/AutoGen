#!/usr/bin/env python3
"""
AutoGen CLI Agent - A Claude-style CLI interface for your AutoGen backend.

Usage:
    autogen-cli                          # Interactive mode
    autogen-cli "What's the weather?"    # Single-shot mode
    autogen-cli --team weather           # Use specific agent team
    autogen-cli --history                # Show conversation history
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional
import argparse
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner
from rich.prompt import Prompt
from rich import print as rprint

from config.settings import get_llm_config
from agents.weather_agents import create_weather_agent_team, create_simple_assistant
from autogen_agentchat.ui import Console as AutogenConsole
from autogen_agentchat.messages import ChatMessage


class CLIAgent:
    """Main CLI Agent class - manages the interactive session."""

    def __init__(
        self,
        team_name: str = "default",
        model_provider: str = "azure",
        save_history: bool = True,
        verbose: bool = False
    ):
        self.console = Console()
        self.team_name = team_name
        self.model_provider = model_provider
        self.save_history = save_history
        self.verbose = verbose
        self.history_file = Path.home() / ".autogen_cli" / "history.jsonl"

        # Ensure history directory exists
        if self.save_history:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)

    def print_banner(self):
        """Display welcome banner."""
        banner = """
# 🤖 AutoGen CLI Agent

Powered by your custom AutoGen backend with Azure OpenAI.
Type your message or command. Type 'exit', 'quit', or press Ctrl+C to leave.
Type '/help' for available commands.
        """
        self.console.print(Panel(Markdown(banner), border_style="blue"))

    def print_help(self):
        """Show help message."""
        help_text = """
## Available Commands

- `/help` - Show this help message
- `/clear` - Clear the screen
- `/history` - Show conversation history
- `/team [name]` - Switch agent team (weather, simple, custom)
- `/config` - Show current configuration
- `/exit` or `exit` - Exit the CLI
- `TERMINATE` - End the current conversation

## Agent Teams

- **weather** - Multi-agent team with weather, joke, and executive agents
- **simple** - Single assistant agent for general tasks
- **custom** - Define your own agent configuration

Type any message to chat with the agents!
        """
        self.console.print(Panel(Markdown(help_text), title="Help", border_style="green"))

    def print_config(self, config: dict):
        """Display current configuration."""
        config_text = f"""
## Current Configuration

- **Team**: {self.team_name}
- **Model Provider**: {config.get('provider', 'unknown')}
- **Model**: {config.get('model', 'unknown')}
- **History Saving**: {self.save_history}
- **Verbose Mode**: {self.verbose}
        """
        self.console.print(Panel(Markdown(config_text), title="Configuration", border_style="yellow"))

    async def run_interactive(self):
        """Run the CLI in interactive mode."""
        self.print_banner()

        # Get LLM configuration
        try:
            llm_config = get_llm_config(provider=self.model_provider)
        except Exception as e:
            self.console.print(f"[red]Error loading configuration: {e}[/red]")
            return

        # Create agent team
        self.console.print(f"[cyan]Initializing {self.team_name} agent team...[/cyan]")

        try:
            if self.team_name == "weather":
                team = await create_weather_agent_team(llm_config)
            elif self.team_name == "simple":
                team = await create_simple_assistant(llm_config)
            else:
                team = await create_weather_agent_team(llm_config)  # default
        except Exception as e:
            self.console.print(f"[red]Error creating agent team: {e}[/red]")
            return

        self.console.print("[green]✓ Agents ready![/green]\n")

        # Main interaction loop
        loop = asyncio.get_event_loop()

        while True:
            try:
                # Get user input
                user_input = await loop.run_in_executor(
                    None,
                    Prompt.ask,
                    "[bold blue]You[/bold blue]"
                )

                if not user_input.strip():
                    continue

                # Handle commands
                if user_input.strip().lower() in ['exit', 'quit', '/exit']:
                    self.console.print("[yellow]Goodbye! 👋[/yellow]")
                    break

                if user_input.strip() == '/help':
                    self.print_help()
                    continue

                if user_input.strip() == '/clear':
                    self.console.clear()
                    self.print_banner()
                    continue

                if user_input.strip() == '/config':
                    self.print_config(llm_config)
                    continue

                if user_input.strip().startswith('/team'):
                    parts = user_input.split()
                    if len(parts) > 1:
                        self.team_name = parts[1]
                        self.console.print(f"[cyan]Switching to {self.team_name} team...[/cyan]")
                        # Recreate team
                        if self.team_name == "weather":
                            team = await create_weather_agent_team(llm_config)
                        elif self.team_name == "simple":
                            team = await create_simple_assistant(llm_config)
                        self.console.print("[green]✓ Team switched![/green]")
                    continue

                # Save to history
                if self.save_history:
                    self._save_to_history("user", user_input)

                # Process with agents
                self.console.print()  # blank line

                try:
                    # Use the existing Console for streaming output
                    await AutogenConsole(team.run_stream(task=user_input))
                except Exception as e:
                    self.console.print(f"[red]Error during agent execution: {e}[/red]")
                    if self.verbose:
                        import traceback
                        self.console.print(f"[red]{traceback.format_exc()}[/red]")

                self.console.print()  # blank line after response

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use 'exit' or '/exit' to quit.[/yellow]")
            except EOFError:
                self.console.print("\n[yellow]Goodbye! 👋[/yellow]")
                break
            except Exception as e:
                self.console.print(f"[red]Unexpected error: {e}[/red]")
                if self.verbose:
                    import traceback
                    self.console.print(f"[red]{traceback.format_exc()}[/red]")

    async def run_single_shot(self, query: str):
        """Run a single query and exit."""
        try:
            llm_config = get_llm_config(provider=self.model_provider)
        except Exception as e:
            self.console.print(f"[red]Error loading configuration: {e}[/red]")
            return

        # Create agent team
        if self.team_name == "weather":
            team = await create_weather_agent_team(llm_config)
        elif self.team_name == "simple":
            team = await create_simple_assistant(llm_config)
        else:
            team = await create_weather_agent_team(llm_config)

        # Run query
        self.console.print(f"[bold blue]Query:[/bold blue] {query}\n")

        try:
            await AutogenConsole(team.run_stream(task=query))
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
            if self.verbose:
                import traceback
                self.console.print(f"[red]{traceback.format_exc()}[/red]")

    def _save_to_history(self, role: str, content: str):
        """Save message to history file."""
        import json

        entry = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content,
            "team": self.team_name
        }

        with open(self.history_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')

    def show_history(self, limit: int = 20):
        """Display conversation history."""
        import json

        if not self.history_file.exists():
            self.console.print("[yellow]No history found.[/yellow]")
            return

        self.console.print(Panel("[bold]Recent Conversation History[/bold]", border_style="magenta"))

        with open(self.history_file, 'r') as f:
            lines = f.readlines()

        for line in lines[-limit:]:
            try:
                entry = json.loads(line)
                timestamp = entry['timestamp'][:19]  # trim microseconds
                role = entry['role']
                content = entry['content'][:100]  # truncate long messages

                if role == "user":
                    self.console.print(f"[blue]{timestamp}[/blue] [bold blue]You:[/bold blue] {content}")
                else:
                    self.console.print(f"[blue]{timestamp}[/blue] [bold green]Agent:[/bold green] {content}")
            except:
                continue


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="AutoGen CLI Agent - A Claude-style interface for your AutoGen backend",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'query',
        nargs='?',
        help='Single query to execute (omit for interactive mode)'
    )

    parser.add_argument(
        '--team',
        '-t',
        default='weather',
        choices=['weather', 'simple', 'custom'],
        help='Agent team to use (default: weather)'
    )

    parser.add_argument(
        '--provider',
        '-p',
        default='azure',
        choices=['azure', 'openai', 'google'],
        help='Model provider (default: azure)'
    )

    parser.add_argument(
        '--no-history',
        action='store_true',
        help='Disable conversation history saving'
    )

    parser.add_argument(
        '--history',
        action='store_true',
        help='Show conversation history and exit'
    )

    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose output'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='AutoGen CLI Agent 1.0.0'
    )

    args = parser.parse_args()

    # Create CLI agent
    cli_agent = CLIAgent(
        team_name=args.team,
        model_provider=args.provider,
        save_history=not args.no_history,
        verbose=args.verbose
    )

    # Show history if requested
    if args.history:
        cli_agent.show_history()
        return

    # Run in appropriate mode
    if args.query:
        # Single-shot mode
        asyncio.run(cli_agent.run_single_shot(args.query))
    else:
        # Interactive mode
        asyncio.run(cli_agent.run_interactive())


if __name__ == '__main__':
    main()

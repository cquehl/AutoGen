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
from agents.weather_agents import (
    create_weather_agent_team,
    create_simple_assistant,
    create_data_team
)
from autogen_agentchat.ui import Console as AutogenConsole
from autogen_agentchat.messages import ChatMessage
from memory_manager import MemoryManager


class CLIAgent:
    """Main CLI Agent class - manages the interactive session."""

    def __init__(
        self,
        team_name: str = "default",
        model_provider: str = "azure",
        save_history: bool = True,
        verbose: bool = False,
        resume: bool = False
    ):
        self.console = Console()
        self.team_name = team_name
        self.model_provider = model_provider
        self.save_history = save_history
        self.verbose = verbose
        self.resume = resume
        self.history_file = Path.home() / ".autogen_cli" / "history.jsonl"

        # Initialize memory manager
        self.memory = MemoryManager(
            max_memories=100,
            max_context_memories=10
        )

        # Ensure history directory exists
        if self.save_history:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)

    def print_banner(self):
        """Display welcome banner."""
        session_info = ""
        if self.resume and self.memory.get_last_session():
            last = self.memory.get_last_session()
            session_info = f"\n💾 **Resumed session from {last.start_time.split('T')[0]}**"

        banner = f"""
# 🤖 AutoGen CLI Agent

Powered by your custom AutoGen backend with Azure OpenAI.{session_info}
Type your message or command. Type 'exit', 'quit', or press Ctrl+C to leave.
Type '/help' for available commands.
        """
        self.console.print(Panel(Markdown(banner), border_style="blue"))

    def print_help(self):
        """Show help message."""
        help_text = """
## Available Commands

**Basic:**
- `/help` - Show this help message
- `/clear` - Clear the screen
- `/history` - Show conversation history
- `/team [name]` - Switch agent team (weather, simple, custom)
- `/config` - Show current configuration
- `/exit` or `exit` - Exit the CLI

**Memory Commands:**
- `/remember [text]` - Save something to long-term memory
- `/memories` - Show all stored memories
- `/search [query]` - Search through memories
- `/forget [id]` - Delete a specific memory
- `/clear-memory` - Delete all memories

## Agent Teams

- **weather** - Multi-agent team with weather, joke, and executive agents
- **simple** - Single assistant agent for general tasks
- **data** - Data analyst with database and file access tools
- **custom** - Define your own agent configuration

## Tips

- Use `-r` or `--resume` when starting to continue with previous context
- Memories are automatically loaded for context in conversations
- Use `/remember` to store important information between sessions

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
        # Start session
        self.memory.start_session(team=self.team_name)

        # Show banner
        self.print_banner()

        # Show loaded context if resuming
        if self.resume:
            context_memories = self.memory.get_context_memories()
            if context_memories:
                self.console.print(f"[cyan]💭 Loaded {len(context_memories)} memories from previous sessions[/cyan]\n")

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
            elif self.team_name == "data":
                team = await create_data_team(llm_config)
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
                        elif self.team_name == "data":
                            team = await create_data_team(llm_config)
                        self.console.print("[green]✓ Team switched![/green]")
                    continue

                # Memory commands
                if user_input.strip().startswith('/remember'):
                    text = user_input[10:].strip()  # Remove '/remember '
                    if text:
                        memory = self.memory.add_memory(text, importance=8)
                        self.console.print(f"[green]✓ Saved to memory (ID: {memory.id})[/green]")
                    else:
                        self.console.print("[yellow]Usage: /remember [text to remember][/yellow]")
                    continue

                if user_input.strip() == '/memories':
                    memories = self.memory.get_memories()
                    if not memories:
                        self.console.print("[yellow]No memories stored yet.[/yellow]")
                    else:
                        self.console.print(Panel(f"[bold]{len(memories)} Stored Memories[/bold]", border_style="magenta"))
                        for mem in memories[-20:]:  # Show last 20
                            date = mem.timestamp.split('T')[0]
                            self.console.print(f"[dim]{mem.id}[/dim] [{date}] {mem.content[:80]}...")
                    continue

                if user_input.strip().startswith('/search'):
                    query = user_input[8:].strip()  # Remove '/search '
                    if query:
                        results = self.memory.search_memories(query)
                        if not results:
                            self.console.print("[yellow]No matching memories found.[/yellow]")
                        else:
                            self.console.print(Panel(f"[bold]Found {len(results)} memories[/bold]", border_style="magenta"))
                            for mem in results:
                                date = mem.timestamp.split('T')[0]
                                self.console.print(f"[dim]{mem.id}[/dim] [{date}] {mem.content}")
                    else:
                        self.console.print("[yellow]Usage: /search [query][/yellow]")
                    continue

                if user_input.strip().startswith('/forget'):
                    mem_id = user_input[8:].strip()  # Remove '/forget '
                    if mem_id:
                        if self.memory.delete_memory(mem_id):
                            self.console.print(f"[green]✓ Deleted memory {mem_id}[/green]")
                        else:
                            self.console.print(f"[red]Memory {mem_id} not found[/red]")
                    else:
                        self.console.print("[yellow]Usage: /forget [memory_id][/yellow]")
                    continue

                if user_input.strip() == '/clear-memory':
                    confirm = await loop.run_in_executor(
                        None,
                        Prompt.ask,
                        "[yellow]Delete ALL memories? (yes/no)[/yellow]"
                    )
                    if confirm.lower() == 'yes':
                        self.memory.clear_all_memories()
                        self.console.print("[green]✓ All memories cleared[/green]")
                    else:
                        self.console.print("[yellow]Cancelled[/yellow]")
                    continue

                # Save to history
                if self.save_history:
                    self._save_to_history("user", user_input)

                # Increment message count
                self.memory.increment_message_count()

                # Process with agents
                self.console.print()  # blank line

                try:
                    # Inject memory context if resuming
                    context_prefix = ""
                    if self.resume:
                        context_prefix = self.memory.format_memories_for_context()

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
        elif self.team_name == "data":
            team = await create_data_team(llm_config)
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
        choices=['weather', 'simple', 'data', 'custom'],
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
        '--resume',
        '-r',
        action='store_true',
        help='Resume with previous session context'
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
        verbose=args.verbose,
        resume=args.resume
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

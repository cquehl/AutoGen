#!/usr/bin/env python3
"""
Yamazaki V2 - Interactive CLI

Interactive command-line interface for chatting with agents.
"""

import asyncio
import sys
import signal
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich import print as rprint

from autogen_agentchat.messages import TextMessage
from autogen_agentchat.ui import Console as AutogenConsole

from .core import get_container


console = Console()


def print_banner():
    """Print welcome banner"""
    banner = """
🥃 🥃 🥃 🥃 🥃 🥃 🥃 🥃 🥃 🥃 🥃 🥃 🥃 🥃 🥃 🥃 🥃 🥃 🥃 🥃

   YAMAZAKI V2 - Interactive CLI
   Smooth, refined, production-ready

🥃 🥃 🥃 🥃 🥃 🥃 🥃 🥃 🥃 🥃 🥃 🥃 🥃 🥃 🥃 🥃 🥃 🥃 🥃 🥃
    """
    console.print(banner, style="bold cyan")


def show_help():
    """Show available commands"""
    help_text = """
[bold cyan]Available Commands:[/bold cyan]

  [bold]/help[/bold]       - Show this help message
  [bold]/agents[/bold]     - List all available agents
  [bold]/tools[/bold]      - List all available tools
  [bold]/info[/bold]       - Show system information
  [bold]/clear[/bold]      - Clear the screen
  [bold]/exit[/bold]       - Exit the CLI
  [bold]/quit[/bold]       - Exit the CLI

[bold cyan]How to Use:[/bold cyan]

  1. Just type your question or request
  2. The system will select the best agent for your task
  3. Use /agents to see what each agent can do

[bold cyan]Examples:[/bold cyan]

  • "What's the weather in Seattle?"
  • "What can you do?"
  • "List all available agents"
    """
    console.print(Panel(help_text, title="Help", border_style="cyan"))


def show_agents():
    """Show all registered agents"""
    container = get_container()
    registry = container.get_agent_registry()
    agents = registry.list_agents()

    if not agents:
        console.print("[yellow]No agents registered yet[/yellow]")
        return

    table = Table(title="Available Agents", border_style="cyan")
    table.add_column("Name", style="bold cyan")
    table.add_column("Category", style="green")
    table.add_column("Description", style="white")
    table.add_column("Version", style="yellow")

    for metadata in agents:
        table.add_row(
            metadata["name"],
            metadata["category"],
            metadata["description"],
            metadata["version"]
        )

    console.print(table)


def show_tools():
    """Show all registered tools"""
    container = get_container()
    registry = container.get_tool_registry()
    tools = registry.list_tools()

    if not tools:
        console.print("[yellow]No tools registered yet[/yellow]")
        return

    table = Table(title="Available Tools", border_style="cyan")
    table.add_column("Name", style="bold cyan")
    table.add_column("Category", style="green")
    table.add_column("Description", style="white")

    for metadata in tools:
        table.add_row(
            metadata["name"],
            metadata["category"],
            metadata["description"]
        )

    console.print(table)


def show_info():
    """Show system information"""
    container = get_container()
    settings = container.settings

    info_text = f"""
[bold cyan]System Information:[/bold cyan]

  [bold]Environment:[/bold] {settings.environment}
  [bold]Default Provider:[/bold] {settings.default_provider.value}
  [bold]Database:[/bold] {settings.database.url}
  [bold]Log Level:[/bold] {settings.observability.log_level}
  [bold]Security Audit:[/bold] {'Enabled' if settings.security.enable_audit_log else 'Disabled'}

[bold cyan]Agents:[/bold cyan] {len(container.get_agent_registry().list_agents())} registered
[bold cyan]Tools:[/bold cyan] {len(container.get_tool_registry().list_tools())} registered
    """
    console.print(Panel(info_text, title="System Info", border_style="cyan"))


async def process_query(query: str) -> str:
    """
    Process user query by selecting appropriate agent and running it.

    Args:
        query: User's question or request

    Returns:
        Agent's response
    """
    container = get_container()
    factory = container.get_agent_factory()

    # Simple agent selection logic
    # In a real implementation, you'd use an orchestrator agent
    query_lower = query.lower()

    if any(word in query_lower for word in ["weather", "forecast", "temperature", "rain"]):
        agent_name = "weather"
    elif any(word in query_lower for word in ["database", "query", "data", "sql", "analyze"]):
        agent_name = "data_analyst"
    else:
        # Default to orchestrator for general queries
        agent_name = "orchestrator"

    try:
        # Create agent
        agent = factory.create(agent_name)

        # For now, just return a helpful message
        # In full implementation, you'd actually run the agent with a team
        return f"[Agent: {agent_name}] I would help you with: {query}\n\n(Note: Full agent execution will be implemented in the next version)"

    except Exception as e:
        return f"[red]Error: {str(e)}[/red]"


async def interactive_loop():
    """Main interactive loop"""
    print_banner()

    console.print("\n[bold green]Welcome to Yamazaki V2![/bold green]")
    console.print("Type [bold]/help[/bold] for available commands, or just ask me anything!\n")
    console.print("[dim]Tip: Press Ctrl+C to exit[/dim]\n")

    # Initialize container
    container = get_container()
    obs = container.get_observability_manager()
    obs.initialize()

    try:
        while True:
            try:
                # Get user input using input() instead of rich Prompt to handle Ctrl+C properly
                console.print("\n[bold cyan]You[/bold cyan]: ", end="")
                user_input = input()

                # Strip whitespace early
                user_input = user_input.strip() if user_input else ""

                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    cmd = user_input.lower().strip()

                    if cmd in ["/exit", "/quit"]:
                        console.print("\n[bold yellow]Goodbye! 👋[/bold yellow]\n")
                        break
                    elif cmd == "/help":
                        show_help()
                    elif cmd == "/agents":
                        show_agents()
                    elif cmd == "/tools":
                        show_tools()
                    elif cmd == "/info":
                        show_info()
                    elif cmd == "/clear":
                        console.clear()
                        print_banner()
                    else:
                        console.print(f"[red]Unknown command: {cmd}[/red]")
                        console.print("Type [bold]/help[/bold] for available commands")
                else:
                    # Process as query
                    with console.status("[bold green]Thinking...[/bold green]"):
                        response = await process_query(user_input)

                    console.print(f"\n[bold green]Yamazaki[/bold green]: {response}")

            except KeyboardInterrupt:
                console.print("\n\n[bold yellow]Interrupted. Exiting...[/bold yellow]")
                break
            except EOFError:
                console.print("\n\n[bold yellow]Goodbye! 👋[/bold yellow]")
                break

    finally:
        # Cleanup
        await container.dispose()


def main():
    """Entry point"""
    try:
        asyncio.run(interactive_loop())
    except KeyboardInterrupt:
        console.print("\n\n[bold yellow]Goodbye! 👋[/bold yellow]\n")
        sys.exit(0)


if __name__ == "__main__":
    main()

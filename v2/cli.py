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
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║         YAMAZAKI V2 - Alfred Concierge Service            ║
║         Smooth, refined, production-ready                  ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


def print_alfred_greeting():
    """Print Alfred's initial greeting"""
    greeting = """[bold white]Alfred:[/bold white] Good day, sir. Alfred at your service.
How may I assist you today?

[dim]I oversee the Yamazaki system and can help you with:
  • Explaining available capabilities (/help)
  • Showing your recent actions (just ask!)
  • Delegating tasks to specialist teams[/dim]
"""
    console.print(greeting)


def show_help():
    """Show available commands"""
    help_text = """
[bold cyan]Available Commands:[/bold cyan]

  [bold]/help[/bold]         - Show this help message
  [bold]/agents[/bold]       - List all available agents
  [bold]/tools[/bold]        - List all available tools
  [bold]/teams[/bold]        - List all available teams
  [bold]/info[/bold]         - Show system information
  [bold]/call_alfred[/bold]  - Return to Alfred (use during team interactions)
  [bold]/clear[/bold]        - Clear the screen
  [bold]/exit[/bold]         - Exit the CLI
  [bold]/quit[/bold]         - Exit the CLI

[bold cyan]How to Use:[/bold cyan]

  1. Alfred is your primary interface - just ask him anything!
  2. He can explain capabilities, show history, and delegate to teams
  3. When delegated to a team, use /call_alfred to return to Alfred
  4. Use /agents and /tools to see what's available

[bold cyan]Examples:[/bold cyan]

  • "What can you do?"
  • "What were my last actions?"
  • "Analyze the weather in Seattle"
  • "Show me available teams"
    """
    console.print(Panel(help_text, title="Alfred's Help", border_style="cyan"))


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


def show_teams():
    """Show all configured teams"""
    try:
        container = get_container()
        factory = container.get_agent_factory()
        team_names = factory.list_available_teams()

        if not team_names:
            console.print("[yellow]No teams configured yet[/yellow]")
            return

        capability_service = container.get_capability_service()
        teams = capability_service.get_teams()

        if not teams:
            console.print("[yellow]No team details available[/yellow]")
            return

        table = Table(title="Available Teams", border_style="cyan")
        table.add_column("Name", style="bold cyan")
        table.add_column("Agents", style="green")
        table.add_column("Max Turns", style="yellow")

        for team in teams:
            table.add_row(
                team.get("name", "Unknown"),
                ", ".join(team.get("agents", [])),
                str(team.get("max_turns", "N/A"))
            )

        console.print(table)
    except Exception as e:
        console.print(f"[red]Error loading teams: {str(e)}[/red]")


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


async def process_query(query: str, agent_name: str = "alfred") -> str:
    """
    Process user query using specified agent (defaults to Alfred).

    Args:
        query: User's question or request
        agent_name: Name of agent to use (default: alfred)

    Returns:
        Agent's response
    """
    container = get_container()
    factory = container.get_agent_factory()

    try:
        # Create the agent
        agent = factory.create(agent_name)

        # For now, return a helpful message indicating Alfred is the interface
        # In full implementation, you'd run the agent with AutoGen's streaming
        if agent_name == "alfred":
            return f"""[bold white]Alfred:[/bold white] Certainly, sir. Regarding: "{query}"

[dim]I understand your request. However, my conversational capabilities are currently being enhanced.
In the meantime, I remain at your service through these commands:[/dim]

[bold cyan]Immediate Actions:[/bold cyan]
  • [bold]/agents[/bold] - View all available agents
  • [bold]/tools[/bold] - View all available tools
  • [bold]/teams[/bold] - View configured teams
  • [bold]/info[/bold] - System information

[bold cyan]Available Capabilities:[/bold cyan]
  • Weather forecasting via [green]weather_team[/green]
  • Data analysis via [green]data_team[/green]
  • Complex multi-agent workflows via [green]magentic_one[/green]

[dim]The full conversational interface will be available shortly, sir.[/dim]
"""
        else:
            return f"""[bold white]{agent_name.title()}:[/bold white] Task received: {query}

[dim](Agent execution framework is being configured. You'll soon be able to interact
with agents directly for task completion.)[/dim]"""

    except Exception as e:
        if agent_name == "alfred":
            return f"""[bold white]Alfred:[/bold white] My apologies, sir. I've encountered an unexpected issue:

[red]{str(e)}[/red]

[dim]Please try again, or use /help to see available commands.[/dim]"""
        else:
            return f"[bold white]{agent_name.title()}:[/bold white] [red]Error: {str(e)}[/red]"


async def interactive_loop():
    """Main interactive loop"""
    print_banner()
    print_alfred_greeting()

    console.print("\n[dim]Type [bold]/help[/bold] for available commands, or just ask Alfred anything![/dim]")
    console.print("[dim]Tip: Press Ctrl+C to exit[/dim]\n")

    # Initialize container
    container = get_container()
    obs = container.get_observability_manager()
    obs.initialize()

    # Current agent mode (alfred is default)
    current_agent = "alfred"

    try:
        while True:
            try:
                # Show prompt based on current agent
                if current_agent == "alfred":
                    console.print("\n[bold cyan]You[/bold cyan]: ", end="")
                else:
                    console.print(f"\n[bold cyan]You[/bold cyan] [dim](via {current_agent})[/dim]: ", end="")

                user_input = input()

                # Strip whitespace early
                user_input = user_input.strip() if user_input else ""

                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    cmd = user_input.lower().strip()

                    if cmd in ["/exit", "/quit"]:
                        console.print("\n[bold white]Alfred:[/bold white] Very good, sir. Until next time. 👋\n")
                        break
                    elif cmd == "/help":
                        show_help()
                    elif cmd == "/agents":
                        show_agents()
                    elif cmd == "/tools":
                        show_tools()
                    elif cmd == "/teams":
                        show_teams()
                    elif cmd == "/info":
                        show_info()
                    elif cmd == "/call_alfred":
                        if current_agent != "alfred":
                            current_agent = "alfred"
                            console.print("\n[bold white]Alfred:[/bold white] Welcome back, sir. How may I assist you further?")
                        else:
                            console.print("\n[bold white]Alfred:[/bold white] I'm already here, sir. At your service.")
                    elif cmd == "/clear":
                        console.clear()
                        print_banner()
                        if current_agent == "alfred":
                            print_alfred_greeting()
                    else:
                        console.print(f"[red]Unknown command: {cmd}[/red]")
                        console.print("Type [bold]/help[/bold] for available commands")
                else:
                    # Process as query using current agent
                    with console.status("[bold green]Thinking...[/bold green]"):
                        response = await process_query(user_input, current_agent)

                    console.print(f"\n{response}")

            except KeyboardInterrupt:
                console.print("\n\n[bold white]Alfred:[/bold white] Interrupted. Very good, sir. Exiting...")
                break
            except EOFError:
                console.print("\n\n[bold white]Alfred:[/bold white] Until next time, sir. 👋")
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

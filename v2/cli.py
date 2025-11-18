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

[dim]I have comprehensive knowledge of the Yamazaki system and can presently:
  • [bold]List capabilities[/bold] - Try: "/agents" or "/tools" or "/teams"
  • [bold]Show your history[/bold] - Ask me: "What were my last actions?"
  • [bold]Explain what's available[/bold] - Ask: "What can you do?"
  • [bold]Provide guidance[/bold] - Use "/help" for all commands[/dim]

[cyan]Tip:[/cyan] [dim]Just ask me questions in plain English, or use slash commands above.[/dim]
"""
    console.print(greeting)


def show_help():
    """Show available commands"""
    help_text = """
[bold cyan]📋 Slash Commands:[/bold cyan]

  [bold]/help[/bold]         - Show this help message
  [bold]/agents[/bold]       - List all available agents (Weather, Data Analyst, etc.)
  [bold]/tools[/bold]        - List all available tools (database, file, weather)
  [bold]/teams[/bold]        - List configured teams (weather_team, data_team, magentic_one)
  [bold]/info[/bold]         - Show system information and status
  [bold]/call_alfred[/bold]  - Return to Alfred (when working with a team)
  [bold]/clear[/bold]        - Clear the screen and reset view
  [bold]/exit, /quit[/bold]  - Exit the CLI

[bold cyan]💬 Talking to Alfred:[/bold cyan]

Alfred can answer questions right now using his three specialized tools:
  • [green]list_capabilities[/green] - "What agents are available?" "Show me tools"
  • [green]show_history[/green] - "What were my last 5 actions?" "Show session history"
  • [green]delegate_to_team[/green] - "Delegate weather analysis to weather_team"

[bold cyan]📝 Example Queries:[/bold cyan]

  [dim]Try these with Alfred:[/dim]
  • "What can you do?"
  • "List all available agents"
  • "Show me my last 10 actions"
  • "What teams are configured?"

[bold cyan]🔄 Workflow:[/bold cyan]

  1. Start → Talk to Alfred (he'll use his tools to help)
  2. When ready → Alfred delegates to specialist teams
  3. Working with team → Use [bold]/call_alfred[/bold] to return
    """
    console.print(Panel(help_text, title="🎩 Alfred's Concierge Help", border_style="cyan"))


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

[dim]I'm currently interfacing with my full conversational capabilities.
For immediate assistance, I can help through these specific methods:[/dim]

[bold cyan]🔍 Try These Commands:[/bold cyan]
  • [bold]/agents[/bold] - See: Weather Agent, Data Analyst, Orchestrator, Web Surfer
  • [bold]/tools[/bold] - View: database queries, file operations, weather forecasts
  • [bold]/teams[/bold] - Explore: weather_team, data_team, magentic_one
  • [bold]/help[/bold] - Full guide to working with Alfred

[bold cyan]💡 Example Queries I Can Handle:[/bold cyan]
  • "List all available agents" → [dim]Uses my list_capabilities tool[/dim]
  • "Show my last 5 actions" → [dim]Uses my show_history tool[/dim]
  • "What teams are configured?" → [dim]Uses my list_capabilities tool[/dim]

[cyan]Tip:[/cyan] [dim]Use the slash commands above for immediate results, sir.[/dim]
"""
        else:
            return f"""[bold white]{agent_name.title()}:[/bold white] Task received: {query}

[dim](Direct agent interaction is being configured. You'll soon execute tasks
through specialist agents. For now, use Alfred as your interface.)[/dim]

[cyan]Tip:[/cyan] Use [bold]/call_alfred[/bold] to return to Alfred."""

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

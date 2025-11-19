#!/usr/bin/env python3
"""
Yamazaki V2 - Interactive CLI

Interactive command-line interface for chatting with agents.
"""

import asyncio
import sys
import signal

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .core import get_container
from .core.base_tool import ToolResult

import logging

# Constants
DEFAULT_AGENT = "alfred"
MAX_QUERY_LENGTH = 10000

console = Console()
logger = logging.getLogger(__name__)


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
    greeting = """[bold white]Alfred:[/bold white] Good day. Alfred at your service.
How may I assist you today?

[dim]I have comprehensive knowledge of the Yamazaki system and am ready to help:
  • [bold]Ask in plain English[/bold] - "What can you do?" "Show my last actions"
  • [bold]View system info[/bold] - Use "/agents" "/tools" or "/teams"
  • [bold]Switch agents[/bold] - "Use agent weather_agent" or /use_agent <name>
  • [bold]Get guidance[/bold] - Type "/help" for all commands[/dim]

[cyan]Tip:[/cyan] [dim]I now understand natural language queries. Just ask me anything![/dim]
"""
    console.print(greeting)


def show_help():
    """Show available commands"""
    help_text = """
[bold cyan]📋 Slash Commands:[/bold cyan]

  [bold]/help[/bold]              - Show this help message
  [bold]/agents[/bold]            - List all available agents (Weather, Data Analyst, etc.)
  [bold]/tools[/bold]             - List all available tools (database, file, weather)
  [bold]/teams[/bold]             - List configured teams (weather_team, data_team, magentic_one)
  [bold]/use_agent <name>[/bold]  - Switch to a specific agent explicitly
  [bold]/call_alfred[/bold]       - Return to Alfred (when working with another agent)
  [bold]/info[/bold]              - Show system information and status
  [bold]/clear[/bold]             - Clear the screen and reset view
  [bold]/exit, /quit[/bold]       - Exit the CLI

[bold cyan]💬 Talking to Alfred:[/bold cyan]

Alfred now responds to natural language! He uses his three specialized tools:
  • [green]list_capabilities[/green] - Shows agents, tools, teams
  • [green]show_history[/green] - Displays recent actions and session history
  • [green]delegate_to_team[/green] - Hands off tasks to specialist teams

[bold cyan]📝 Example Queries:[/bold cyan]

  [dim]These actually work now - try them![/dim]
  • "What can you do?" → [dim]Lists all capabilities[/dim]
  • "List all available agents" → [dim]Shows registered agents[/dim]
  • "Show me my last 10 actions" → [dim]Displays recent history[/dim]
  • "What teams are configured?" → [dim]Lists available teams[/dim]
  • "Use agent weather_agent" → [dim]Switches to that agent[/dim]
  • "Delegate to weather_team" → [dim]Hands off to specialist team[/dim]

[bold cyan]🔄 Workflow:[/bold cyan]

  1. Start → Talk to Alfred (natural language or slash commands)
  2. Ask Alfred → He'll use his tools to answer or help
  3. Switch agents → Use "Use agent X" or /use_agent X
  4. Return to Alfred → Use /call_alfred or just ask for him
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


def get_available_agents(container):
    """
    Get list of available agents from capability service.

    Args:
        container: Dependency injection container

    Returns:
        Tuple of (agents_list, agent_names_lowercase)
    """
    capability_service = container.get_capability_service()
    agents = capability_service.get_agents()
    agent_names = [a.get("name", "").lower() for a in agents]
    return agents, agent_names


def get_available_teams(container):
    """
    Get list of available teams from capability service.

    Args:
        container: Dependency injection container

    Returns:
        Tuple of (teams_list, team_names_lowercase)
    """
    capability_service = container.get_capability_service()
    teams = capability_service.get_teams()
    team_names = [t.get("name", "").lower() for t in teams]
    return teams, team_names


def extract_number_from_query(query: str, default: int = 5) -> int:
    """
    Extract a number from a query string.

    Args:
        query: User query string
        default: Default value if no number found

    Returns:
        Extracted number or default
    """
    import re

    # Try to find a number in the query
    numbers = re.findall(r'\b(\d+)\b', query)
    if numbers:
        try:
            return int(numbers[0])
        except (ValueError, IndexError):
            pass

    # Check for word numbers
    word_to_num = {
        "five": 5, "ten": 10, "fifteen": 15, "twenty": 20,
        "thirty": 30, "fifty": 50, "hundred": 100
    }
    query_lower = query.lower()
    for word, num in word_to_num.items():
        if word in query_lower:
            return num

    return default


def format_tool_result(result: ToolResult, prefix: str = "Alfred") -> str:
    """
    Format a ToolResult for display in the CLI.

    Args:
        result: ToolResult from tool execution
        prefix: Name prefix for display (e.g., "Alfred")

    Returns:
        Formatted string for console display
    """
    if not result.success:
        return f"[bold white]{prefix}:[/bold white] {result.error}"

    # If the result has a pre-formatted display string, use it
    if isinstance(result.data, dict) and "formatted" in result.data:
        return f"[bold white]{prefix}:[/bold white] Certainly.\n\n{result.data['formatted']}"

    # Otherwise, try to display the raw data
    return f"[bold white]{prefix}:[/bold white] {result.data}"


async def process_query(query: str, agent_name: str = DEFAULT_AGENT) -> dict:
    """
    Process user query using specified agent (defaults to Alfred).

    Args:
        query: User's question or request
        agent_name: Name of agent to use (default: alfred)

    Returns:
        Dict with 'response' (str) and optionally 'switch_to_agent' (str)
    """
    # Input validation
    if not query or not query.strip():
        return {"response": ""}

    query = query.strip()
    if len(query) > MAX_QUERY_LENGTH:
        return {
            "response": f"[bold white]Alfred:[/bold white] I apologize, but that query is too long ({len(query)} characters). Please keep it under {MAX_QUERY_LENGTH} characters."
        }

    container = get_container()
    tool_registry = container.get_tool_registry()

    try:
        if agent_name == DEFAULT_AGENT:
            # Alfred: Detect intent and call appropriate tools
            query_lower = query.lower()
            logger.info(f"Processing Alfred query: {query[:100]}...")

            # Pattern 1: Capabilities / "What can you do?"
            # More specific: must start with question words or have "list/show"
            if any(query_lower.startswith(phrase) for phrase in ["what can", "what are", "list ", "show "]) or \
               any(phrase in query_lower for phrase in ["list capabilities", "show capabilities", "what capabilities"]):

                if any(word in query_lower for word in ["agent"]):
                    category = "agents"
                elif any(word in query_lower for word in ["tool"]):
                    category = "tools"
                elif any(word in query_lower for word in ["team"]):
                    category = "teams"
                else:
                    category = "all"

                logger.info(f"Calling list_capabilities tool with category={category}")
                tool = tool_registry.create_tool("alfred.list_capabilities")
                result = await tool.execute(category=category)
                return {"response": format_tool_result(result)}

            # Pattern 2: History / "Show my actions"
            # More specific: must mention "history" or "action" with relevant context
            elif any(phrase in query_lower for phrase in [
                "my history", "show history", "view history",
                "my action", "last action", "recent action",
                "what did i do", "what have i done",
            ]):
                limit = extract_number_from_query(query, default=5)
                limit = min(limit, 100)  # Cap at 100

                logger.info(f"Calling show_history tool with limit={limit}")
                tool = tool_registry.create_tool("alfred.show_history")
                result = await tool.execute(scope="recent", limit=limit)
                return {"response": format_tool_result(result)}

            # Pattern 3: Delegation / "Delegate to team"
            elif any(phrase in query_lower for phrase in [
                "delegate to",
                "use team",
                "use the team",
                "hand off to",
                "handoff to",
                "switch to team",
            ]):
                # Dynamically fetch available teams
                teams, team_names = get_available_teams(container)

                # Try to extract team name from query
                found_team = None
                for team_info in teams:
                    team_name_check = team_info.get("name", "").lower()
                    if team_name_check in query_lower.replace(" ", "_"):
                        found_team = team_info.get("name")
                        break

                if found_team:
                    logger.info(f"Calling delegate_to_team tool with team={found_team}")
                    tool = tool_registry.create_tool("alfred.delegate_to_team")
                    result = await tool.execute(team_name=found_team, task=query)
                    return {"response": format_tool_result(result)}
                else:
                    # Show available teams dynamically
                    team_list = "\n  • ".join([t.get("name", "Unknown") for t in teams]) if teams else "None configured"
                    example_team = teams[0].get('name', 'team_name') if teams else 'team_name'
                    return {"response": f"""[bold white]Alfred:[/bold white] I'd be delighted to delegate, but I need to know which team.

[bold cyan]Available teams:[/bold cyan]
  • {team_list}

[dim]Try: "Delegate to {example_team}" or use /teams to see details.[/dim]"""}

            # Pattern 4: Agent switching / "Use agent X"
            elif any(phrase in query_lower for phrase in [
                "use agent",
                "switch to agent",
                "work with agent",
                "talk to agent",
            ]):
                # Get list of available agents
                agents, agent_names = get_available_agents(container)

                # Look for agent name in query
                found_agent = None
                for agent_info in agents:
                    agent_name_check = agent_info.get("name", "").lower()
                    if agent_name_check in query_lower:
                        found_agent = agent_info.get("name")
                        break

                if found_agent:
                    logger.info(f"Switching to agent: {found_agent}")
                    return {
                        "response": f"""[bold white]Alfred:[/bold white] Very good. I shall step aside.

[green]✓ Switched to: {found_agent}[/green]

[dim]You're now talking to {found_agent}. Use /call_alfred to return to me.[/dim]""",
                        "switch_to_agent": found_agent.lower()
                    }
                else:
                    # Show available agents
                    agent_list = "\n  • ".join([a.get("name", "Unknown") for a in agents]) if agents else "None registered"
                    example_agent = agents[0].get('name', 'agent_name') if agents else 'agent_name'
                    return {"response": f"""[bold white]Alfred:[/bold white] Which agent would you like to use?

[bold cyan]Available agents:[/bold cyan]
  • {agent_list}

[dim]Try: "Use agent {example_agent}" or /agents for details.[/dim]"""}

            # Pattern 5: Help request
            elif any(phrase in query_lower for phrase in ["help", "how do i", "how can i"]):
                show_help()
                return {"response": "[dim](Help displayed above)[/dim]"}

            # Pattern 6: No match - provide helpful suggestions
            else:
                logger.info(f"No pattern matched for query: {query[:100]}")
                return {"response": f"""[bold white]Alfred:[/bold white] I'm not quite certain how to assist with: "{query}"

[bold cyan]💡 Here's what I can do for you:[/bold cyan]
  • [green]"What can you do?"[/green] - See all available agents, tools, and teams
  • [green]"Show my last 10 actions"[/green] - View your recent history
  • [green]"Delegate to weather_team"[/green] - Hand off to a specialist team
  • [green]"Use agent <name>"[/green] - Switch to a specific agent (try: /agents to see list)

[cyan]Tip:[/cyan] [dim]Use /help to see all slash commands.[/dim]"""}

        else:
            # Other agents: Placeholder for future direct agent interaction
            logger.info(f"Query passed to non-Alfred agent: {agent_name}")
            return {"response": f"""[bold white]{agent_name.title()}:[/bold white] Task received: {query}

[dim](Direct agent interaction is being configured. You'll soon execute tasks
through specialist agents. For now, use Alfred as your interface.)[/dim]

[cyan]Tip:[/cyan] Use [bold]/call_alfred[/bold] to return to Alfred."""}

    except ValueError as e:
        logger.error(f"Validation error in process_query: {e}")
        return {"response": f"[bold white]Alfred:[/bold white] I apologize, but there was an issue with your request: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error in process_query: {e}", exc_info=True)
        if agent_name == DEFAULT_AGENT:
            return {"response": f"""[bold white]Alfred:[/bold white] My apologies. I've encountered an unexpected issue:

[red]{str(e)}[/red]

[dim]Please try again, or use /help to see available commands.[/dim]"""}
        else:
            return {"response": f"[bold white]{agent_name.title()}:[/bold white] [red]Error: {str(e)}[/red]"}


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

    # Setup signal handlers for graceful shutdown
    shutdown_event = asyncio.Event()
    cleanup_completed = False

    def signal_handler(signum):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown")
        shutdown_event.set()

    # Register handlers for SIGTERM and SIGINT early, before entering the main loop
    # CRITICAL: Only register signal handlers on Unix-like systems
    if hasattr(signal, 'SIGTERM'):
        try:
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))
        except (RuntimeError, OSError) as e:
            # Signal handling may not be available in some environments (Windows, testing)
            logger.warning(f"Could not register signal handlers: {e}")

    # Current agent mode (alfred is default)
    current_agent = DEFAULT_AGENT

    try:
        while True:
            try:
                # Show prompt based on current agent
                if current_agent == DEFAULT_AGENT:
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
                        console.print("\n[bold white]Alfred:[/bold white] Very good. Until next time. 👋\n")
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
                        if current_agent != DEFAULT_AGENT:
                            current_agent = DEFAULT_AGENT
                            console.print("\n[bold white]Alfred:[/bold white] Welcome back. How may I assist you further?")
                        else:
                            console.print("\n[bold white]Alfred:[/bold white] I'm already here. At your service.")
                    elif cmd.startswith("/use_agent"):
                        # Extract agent name from command
                        parts = user_input.split(maxsplit=1)
                        if len(parts) > 1:
                            requested_agent = parts[1].strip().lower()
                            # Validate agent exists using helper function
                            agents, agent_names = get_available_agents(container)

                            if requested_agent in agent_names:
                                current_agent = requested_agent
                                console.print(f"\n[bold white]Alfred:[/bold white] Very good. Switching to [green]{requested_agent}[/green].")
                                console.print("[dim]Note: Direct agent interaction is being configured. Use /call_alfred to return.[/dim]")
                            else:
                                console.print(f"[red]Agent '{requested_agent}' not found.[/red]")
                                console.print(f"Available agents: {', '.join(agent_names)}")
                                console.print("Use [bold]/agents[/bold] to see full details")
                        else:
                            console.print("[yellow]Usage: /use_agent <agent_name>[/yellow]")
                            console.print("Example: /use_agent weather_agent")
                            console.print("Use [bold]/agents[/bold] to see available agents")
                    elif cmd == "/clear":
                        console.clear()
                        print_banner()
                        if current_agent == DEFAULT_AGENT:
                            print_alfred_greeting()
                    else:
                        console.print(f"[red]Unknown command: {cmd}[/red]")
                        console.print("Type [bold]/help[/bold] for available commands")
                else:
                    # Process as query using current agent
                    with console.status("[bold green]Thinking...[/bold green]"):
                        result = await process_query(user_input, current_agent)

                    # Handle result (dict with 'response' and optionally 'switch_to_agent')
                    if result.get("response"):
                        console.print(f"\n{result['response']}")

                    # Handle agent switching from natural language
                    if "switch_to_agent" in result:
                        current_agent = result["switch_to_agent"]
                        logger.info(f"Switched to agent: {current_agent}")

            except KeyboardInterrupt:
                console.print("\n\n[bold white]Alfred:[/bold white] Interrupted. Very good. Exiting...")
                break
            except EOFError:
                console.print("\n\n[bold white]Alfred:[/bold white] Until next time. 👋")
                break

    finally:
        # CRITICAL: Ensure cleanup even if exception occurs
        if not cleanup_completed:
            console.print("\n[yellow]Cleaning up resources...[/yellow]")
            try:
                await asyncio.wait_for(container.dispose(), timeout=5.0)
                cleanup_completed = True
                logger.info("Container disposed successfully")
            except asyncio.TimeoutError:
                logger.error("Container disposal timed out after 5 seconds")
            except Exception as e:
                logger.error(f"Error during container disposal: {e}")


def main():
    """Entry point"""
    try:
        asyncio.run(interactive_loop())
    except KeyboardInterrupt:
        console.print("\n\n[bold yellow]Goodbye! 👋[/bold yellow]\n")
        sys.exit(0)


if __name__ == "__main__":
    main()

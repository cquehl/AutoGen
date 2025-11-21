#!/usr/bin/env python3
"""
Demo script for Alfred with MCP integration
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.alfred.main_mcp import create_alfred_mcp
from src.core.mcp import MCPConfig, MCPServerConfig, ServerType, TransportType
from src.core.telemetry import setup_logging
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()


async def main():
    """Main demo function"""

    # Setup logging
    setup_logging(level="INFO")

    # Create MCP configuration
    # Note: For demo purposes, we'll create a minimal config
    # In production, you would have actual MCP servers installed
    mcp_config = MCPConfig(
        enabled=True,
        servers=[
            # Add filesystem server if you have it installed
            # MCPServerConfig(
            #     name="filesystem",
            #     type=ServerType.FILESYSTEM,
            #     transport=TransportType.STDIO,
            #     command="npx @modelcontextprotocol/server-filesystem",
            #     env={"ALLOWED_DIRECTORIES": "/tmp,/Users"},
            #     auto_start=True
            # )
        ],
        log_level="INFO"
    )

    # Create Alfred with MCP
    console.print(Panel.fit(
        "[bold cyan]Alfred MCP Integration Demo[/bold cyan]\n"
        "Enhanced AI Concierge with Model Context Protocol",
        border_style="cyan"
    ))

    alfred = create_alfred_mcp(mcp_config)

    try:
        # Initialize Alfred
        console.print("\n[yellow]Initializing Alfred with MCP...[/yellow]")
        await alfred.initialize()

        # Show greeting
        greeting = await alfred.greet()
        console.print(Panel(Markdown(greeting), title="Alfred", border_style="green"))

        # Demo commands
        console.print("\n[bold]Available Commands:[/bold]")
        console.print("  • Type your message for Alfred")
        console.print("  • /mcp status - Show MCP status")
        console.print("  • /mcp tools - List available MCP tools")
        console.print("  • /mcp servers - Show configured servers")
        console.print("  • /quit - Exit the demo")
        console.print()

        # Interactive loop
        while True:
            try:
                # Get user input
                user_input = console.input("[bold blue]You:[/bold blue] ")

                if user_input.lower() == "/quit":
                    break

                # Process message
                console.print("[yellow]Alfred is thinking...[/yellow]")

                # Check if streaming is appropriate
                if user_input.startswith("/mcp"):
                    # Non-streaming for MCP commands
                    response = await alfred.handle_message(user_input)
                    console.print(Panel(Markdown(response), title="Alfred", border_style="green"))
                else:
                    # Stream the response
                    console.print("[bold green]Alfred:[/bold green] ", end="")
                    full_response = ""
                    async for token in alfred.process_message_streaming(user_input):
                        console.print(token, end="")
                        full_response += token
                    console.print()

            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted. Type /quit to exit.[/yellow]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

    finally:
        # Shutdown
        console.print("\n[yellow]Shutting down Alfred...[/yellow]")
        await alfred.shutdown()
        console.print("[green]Goodbye![/green]")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
        sys.exit(0)
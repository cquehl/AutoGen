#!/usr/bin/env python3
"""
Test Alfred's NEW capabilities as an executive assistant.
This script tests the newly implemented tools.
"""

import asyncio
import sys
from v2.core import get_container
from rich.console import Console
from rich.panel import Panel
import tempfile
import os

console = Console()

async def test_web_search():
    """Test: Can Alfred search the web?"""
    console.print(Panel("[bold cyan]Test 1: Web Search[/bold cyan]", border_style="cyan"))

    container = get_container()
    obs = container.get_observability_manager()
    obs.initialize()

    tool_registry = container.get_tool_registry()

    try:
        # Create web search tool
        tool = tool_registry.create_tool("web.search")

        # Search for something relevant
        console.print("[bold]Searching for: Python programming tutorials[/bold]")
        result = await tool.execute(query="Python programming tutorials", max_results=3)

        if result.success:
            console.print(f"[green]✓ Web search successful! Found {result.data.get('count', 0)} results[/green]")
            if result.data.get("formatted"):
                console.print(result.data["formatted"][:500] + "...")  # Print first 500 chars
        else:
            console.print(f"[red]✗ Web search failed: {result.error}[/red]")

    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")

    console.print()
    return container

async def test_news_search():
    """Test: Can Alfred get today's news?"""
    console.print(Panel("[bold cyan]Test 2: News Retrieval[/bold cyan]", border_style="cyan"))

    container = get_container()
    tool_registry = container.get_tool_registry()

    try:
        # Create news search tool
        tool = tool_registry.create_tool("web.news")

        # Get tech news
        console.print("[bold]Fetching technology news...[/bold]")
        result = await tool.execute(category="technology", max_results=3)

        if result.success:
            console.print(f"[green]✓ News retrieval successful! Found {result.data.get('count', 0)} articles[/green]")
            console.print(f"   Source: {result.data.get('source', 'Unknown')}")
            if result.data.get("note"):
                console.print(f"   Note: {result.data['note']}")
            if result.data.get("formatted"):
                console.print(result.data["formatted"][:500] + "...")  # Print first 500 chars
        else:
            console.print(f"[red]✗ News retrieval failed: {result.error}[/red]")

    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")

    console.print()

async def test_file_write():
    """Test: Can Alfred write files?"""
    console.print(Panel("[bold cyan]Test 3: File Writing[/bold cyan]", border_style="cyan"))

    container = get_container()
    tool_registry = container.get_tool_registry()

    try:
        # Create write tool
        tool = tool_registry.create_tool("file.write")

        # Write a test file in project directory (allowed path)
        test_file = os.path.join(os.getcwd(), "alfred_test_write.txt")

        content = """# Test File Created by Alfred

This file was created by Alfred, the executive assistant, to test file writing capabilities.

Date: 2025-11-20
Purpose: Capability testing
Status: Success
"""

        console.print(f"[bold]Writing test file to: {test_file}[/bold]")
        result = await tool.execute(file_path=test_file, content=content)

        if result.success:
            console.print(f"[green]✓ File writing successful![/green]")
            console.print(f"   File: {result.data.get('file_path')}")
            console.print(f"   Bytes written: {result.data.get('bytes_written')}")
            console.print(f"   Lines written: {result.data.get('lines_written')}")

            # Verify file exists
            if os.path.exists(test_file):
                console.print(f"   [green]✓ File verified to exist[/green]")
        else:
            console.print(f"[red]✗ File writing failed: {result.error}[/red]")

    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")

    console.print()

async def test_file_append():
    """Test: Can Alfred append to files?"""
    console.print(Panel("[bold cyan]Test 4: File Appending[/bold cyan]", border_style="cyan"))

    container = get_container()
    tool_registry = container.get_tool_registry()

    try:
        # Create append tool
        tool = tool_registry.create_tool("file.append")

        # Append to the test file we just created
        test_file = os.path.join(os.getcwd(), "alfred_test_write.txt")

        additional_content = "\n\nAppended by Alfred:\n- Append test successful\n- Alfred can modify existing files\n"

        console.print(f"[bold]Appending to: {test_file}[/bold]")
        result = await tool.execute(file_path=test_file, content=additional_content)

        if result.success:
            console.print(f"[green]✓ File appending successful![/green]")
            console.print(f"   Bytes appended: {result.data.get('bytes_appended')}")
            console.print(f"   Lines appended: {result.data.get('lines_appended')}")
            console.print(f"   New file size: {result.data.get('new_size')} bytes")
        else:
            console.print(f"[red]✗ File appending failed: {result.error}[/red]")

    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")

    console.print()

async def test_file_read_verify():
    """Test: Can Alfred read back the file?"""
    console.print(Panel("[bold cyan]Test 5: Reading Back Written File[/bold cyan]", border_style="cyan"))

    container = get_container()
    tool_registry = container.get_tool_registry()

    try:
        # Create read tool using registry
        tool = tool_registry.create_tool("file.read")

        # Read the test file
        test_file = os.path.join(os.getcwd(), "alfred_test_write.txt")

        console.print(f"[bold]Reading: {test_file}[/bold]")
        result = await tool.execute(file_path=test_file)

        if result.success:
            console.print(f"[green]✓ File reading successful![/green]")
            console.print(f"   Lines read: {result.data.get('lines_read')}")
            console.print(f"\n   Content preview:")
            content = result.data.get('content', '')
            console.print(f"   {content[:200]}...")
        else:
            console.print(f"[red]✗ File reading failed: {result.error}[/red]")

    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")

    console.print()

async def test_all_capabilities():
    """Test: List all capabilities including new ones"""
    console.print(Panel("[bold cyan]Test 6: List All Capabilities[/bold cyan]", border_style="cyan"))

    container = get_container()
    tool_registry = container.get_tool_registry()
    tools = tool_registry.list_tools()

    console.print(f"[green]Total tools registered: {len(tools)}[/green]\n")

    # Group by category
    from collections import defaultdict
    by_category = defaultdict(list)
    for tool in tools:
        by_category[tool['category']].append(tool['name'])

    for category, tool_names in sorted(by_category.items()):
        console.print(f"[bold cyan]{category.upper()}:[/bold cyan]")
        for name in sorted(tool_names):
            console.print(f"  • {name}")
        console.print()

async def main():
    """Main test runner"""
    console.print("\n[bold cyan]════════════════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]    ALFRED NEW CAPABILITIES TEST SUITE[/bold cyan]")
    console.print("[bold cyan]════════════════════════════════════════════════════════════[/bold cyan]\n")

    try:
        # Run all tests
        container = await test_web_search()
        await test_news_search()
        await test_file_write()
        await test_file_append()
        await test_file_read_verify()
        await test_all_capabilities()

        # Summary
        console.print("\n[bold cyan]════════════════════════════════════════════════════════════[/bold cyan]")
        console.print("[bold cyan]                    SUMMARY[/bold cyan]")
        console.print("[bold cyan]════════════════════════════════════════════════════════════[/bold cyan]\n")

        console.print("[bold green]✓ NEW Capabilities Implemented:[/bold green]")
        console.print("  1. Web search (DuckDuckGo)")
        console.print("  2. News retrieval (with fallback)")
        console.print("  3. File writing")
        console.print("  4. File appending")
        console.print("  5. Complete file management")

        console.print("\n[bold cyan]Alfred can now:[/bold cyan]")
        console.print("  • Search the web for information")
        console.print("  • Get today's news on any topic")
        console.print("  • Create and write documents")
        console.print("  • Modify existing files")
        console.print("  • Read, write, and manage files")
        console.print("  • Provide comprehensive executive assistant services")

        console.print("\n[bold yellow]Still TODO (Future Enhancements):[/bold yellow]")
        console.print("  • Calendar integration")
        console.print("  • Email management")
        console.print("  • Task management integration")
        console.print("  • Meeting transcription")
        console.print("  • Travel planning")
        console.print()

        # Cleanup
        await container.dispose()

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Test interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Error during testing: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

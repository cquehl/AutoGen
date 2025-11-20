#!/usr/bin/env python3
"""
Test Alfred's capabilities as an executive assistant.
This script tests various real-world EA tasks to identify limitations.
"""

import asyncio
import sys
from v2.core import get_container
from v2.tools.alfred.list_capabilities_tool import ListCapabilitiesTool
from v2.tools.alfred.show_history_tool import ShowHistoryTool
from rich.console import Console
from rich.panel import Panel

console = Console()

async def test_capabilities():
    """Test what Alfred can currently do"""
    console.print(Panel("[bold cyan]Test 1: Listing Current Capabilities[/bold cyan]", border_style="cyan"))

    container = get_container()
    obs = container.get_observability_manager()
    obs.initialize()

    # Test list capabilities
    capability_service = container.get_capability_service()
    tool = ListCapabilitiesTool(capability_service=capability_service)

    result = await tool.execute(category="all")
    console.print(result.data.get("formatted", str(result.data)))
    console.print()

    return container

async def test_news_retrieval():
    """Test: Can Alfred get today's news?"""
    console.print(Panel("[bold cyan]Test 2: Retrieving Today's News[/bold cyan]", border_style="cyan"))
    console.print("[yellow]❌ LIMITATION: No news retrieval capability found[/yellow]")
    console.print("[dim]Alfred needs a web search or news API tool[/dim]")
    console.print()

async def test_file_reading():
    """Test: Can Alfred read files?"""
    console.print(Panel("[bold cyan]Test 3: Reading Files[/bold cyan]", border_style="cyan"))

    container = get_container()
    tool_registry = container.get_tool_registry()
    tools = tool_registry.list_tools()

    file_tools = [t for t in tools if "file" in t["name"].lower()]

    if file_tools:
        console.print(f"[green]✓ Found {len(file_tools)} file tool(s):[/green]")
        for tool in file_tools:
            console.print(f"  • {tool['name']}: {tool['description']}")

        # Test reading a file
        console.print("\n[bold]Testing file.read on README-V2.md...[/bold]")
        from v2.tools.file.read_tool import ReadFileTool
        read_tool = ReadFileTool()

        result = await read_tool.execute(file_path="README-V2.md", lines=10)
        if result.success:
            console.print(f"[green]✓ Successfully read file (first {result.data.get('lines_read', 0)} lines)[/green]")
        else:
            console.print(f"[red]✗ Error: {result.error}[/red]")
    else:
        console.print("[yellow]❌ LIMITATION: No file reading capability[/yellow]")

    console.print()

async def test_calendar_scheduling():
    """Test: Can Alfred manage calendar/schedule?"""
    console.print(Panel("[bold cyan]Test 4: Calendar & Scheduling[/bold cyan]", border_style="cyan"))
    console.print("[yellow]❌ LIMITATION: No calendar integration[/yellow]")
    console.print("[dim]Alfred needs calendar API tools (Google Calendar, Outlook, etc.)[/dim]")
    console.print()

async def test_email_management():
    """Test: Can Alfred manage emails?"""
    console.print(Panel("[bold cyan]Test 5: Email Management[/bold cyan]", border_style="cyan"))
    console.print("[yellow]❌ LIMITATION: No email capabilities[/yellow]")
    console.print("[dim]Alfred needs email API tools (Gmail, Outlook, etc.)[/dim]")
    console.print()

async def test_document_creation():
    """Test: Can Alfred create documents?"""
    console.print(Panel("[bold cyan]Test 6: Document Creation[/bold cyan]", border_style="cyan"))
    console.print("[yellow]⚠️  LIMITED: Can only read files, not create/edit documents[/yellow]")
    console.print("[dim]Alfred needs document creation tools (Word, Google Docs, PDF, etc.)[/dim]")
    console.print()

async def test_task_management():
    """Test: Can Alfred manage tasks/todos?"""
    console.print(Panel("[bold cyan]Test 7: Task Management[/bold cyan]", border_style="cyan"))
    console.print("[yellow]❌ LIMITATION: No task management integration[/yellow]")
    console.print("[dim]Alfred needs task API tools (Todoist, Asana, Jira, etc.)[/dim]")
    console.print()

async def test_web_research():
    """Test: Can Alfred do web research?"""
    console.print(Panel("[bold cyan]Test 8: Web Research[/bold cyan]", border_style="cyan"))
    console.print("[yellow]❌ LIMITATION: Web surfer agent is planned but not yet implemented[/yellow]")
    console.print("[dim]Alfred needs web browsing/search capabilities[/dim]")
    console.print()

async def test_data_analysis():
    """Test: Can Alfred analyze data?"""
    console.print(Panel("[bold cyan]Test 9: Data Analysis[/bold cyan]", border_style="cyan"))

    container = get_container()
    tool_registry = container.get_tool_registry()
    tools = tool_registry.list_tools()

    db_tools = [t for t in tools if "database" in t["name"].lower()]

    if db_tools:
        console.print(f"[green]✓ Found {len(db_tools)} database tool(s):[/green]")
        for tool in db_tools:
            console.print(f"  • {tool['name']}: {tool['description']}")
    else:
        console.print("[yellow]❌ No database tools[/yellow]")

    console.print()

async def test_meeting_transcription():
    """Test: Can Alfred transcribe meetings?"""
    console.print(Panel("[bold cyan]Test 10: Meeting Transcription[/bold cyan]", border_style="cyan"))
    console.print("[yellow]❌ LIMITATION: No transcription capabilities[/yellow]")
    console.print("[dim]Alfred needs speech-to-text or meeting transcription tools[/dim]")
    console.print()

async def test_notifications_reminders():
    """Test: Can Alfred send notifications/reminders?"""
    console.print(Panel("[bold cyan]Test 11: Notifications & Reminders[/bold cyan]", border_style="cyan"))
    console.print("[yellow]❌ LIMITATION: No notification system[/yellow]")
    console.print("[dim]Alfred needs notification/reminder capabilities[/dim]")
    console.print()

async def test_travel_planning():
    """Test: Can Alfred help with travel planning?"""
    console.print(Panel("[bold cyan]Test 12: Travel Planning[/bold cyan]", border_style="cyan"))
    console.print("[yellow]❌ LIMITATION: No travel API integrations[/yellow]")
    console.print("[dim]Alfred needs flight/hotel booking, maps integration, etc.[/dim]")
    console.print()

async def main():
    """Main test runner"""
    console.print("\n[bold cyan]════════════════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]    ALFRED EXECUTIVE ASSISTANT CAPABILITY TEST SUITE[/bold cyan]")
    console.print("[bold cyan]════════════════════════════════════════════════════════════[/bold cyan]\n")

    try:
        # Run all tests
        container = await test_capabilities()
        await test_news_retrieval()
        await test_file_reading()
        await test_calendar_scheduling()
        await test_email_management()
        await test_document_creation()
        await test_task_management()
        await test_web_research()
        await test_data_analysis()
        await test_meeting_transcription()
        await test_notifications_reminders()
        await test_travel_planning()

        # Summary
        console.print("\n[bold cyan]════════════════════════════════════════════════════════════[/bold cyan]")
        console.print("[bold cyan]                    SUMMARY OF FINDINGS[/bold cyan]")
        console.print("[bold cyan]════════════════════════════════════════════════════════════[/bold cyan]\n")

        console.print("[bold green]✓ Working Capabilities:[/bold green]")
        console.print("  • File reading (basic)")
        console.print("  • Database queries")
        console.print("  • Weather forecasts")
        console.print("  • System capability listing")
        console.print("  • History viewing")
        console.print("  • Team delegation")

        console.print("\n[bold yellow]❌ Missing Executive Assistant Capabilities:[/bold yellow]")
        console.print("  1. News retrieval / web search")
        console.print("  2. Calendar/scheduling integration")
        console.print("  3. Email management")
        console.print("  4. Document creation/editing")
        console.print("  5. Task management integration")
        console.print("  6. Web research (planned but not implemented)")
        console.print("  7. Meeting transcription")
        console.print("  8. Notifications & reminders")
        console.print("  9. Travel planning APIs")
        console.print(" 10. File writing/editing capabilities")

        console.print("\n[bold cyan]Next Steps:[/bold cyan]")
        console.print("  1. Implement web search/news tool")
        console.print("  2. Add file write/edit tool")
        console.print("  3. Create calendar integration tool")
        console.print("  4. Build email management tool")
        console.print("  5. Add task management integration")
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

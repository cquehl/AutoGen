#!/usr/bin/env python3
"""
MCP Filesystem Server Integration Demo

This example demonstrates how to integrate and use the MCP filesystem server
with the Suntory V3 system.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.mcp import (
    MCPManager,
    MCPConfig,
    MCPServerConfig,
    ServerType,
    TransportType,
    MCPAutoGenBridge,
    AutoGenToolAdapter
)
from core.telemetry import setup_logging


async def demo_filesystem_server():
    """Demonstrate filesystem MCP server integration"""

    # Setup logging
    setup_logging(level="INFO")

    # Configure MCP with filesystem server
    filesystem_config = MCPServerConfig(
        name="filesystem",
        type=ServerType.FILESYSTEM,
        transport=TransportType.STDIO,
        command="npx @modelcontextprotocol/server-filesystem",
        env={
            "ALLOWED_DIRECTORIES": "/tmp/mcp-demo,/Users/cjq/Dev/MyProjects/AutoGen/v3"
        },
        auto_start=True
    )

    # Create MCP configuration
    mcp_config = MCPConfig(
        enabled=True,
        servers=[filesystem_config],
        log_level="DEBUG"
    )

    # Initialize MCP Manager
    print("Initializing MCP Manager...")
    mcp_manager = MCPManager(config=mcp_config)

    try:
        # Initialize the MCP subsystem
        await mcp_manager.initialize()
        print(f"✓ MCP subsystem initialized")

        # List available tools
        print("\n📋 Available Tools:")
        tools = await mcp_manager.list_tools()
        for tool in tools:
            print(f"  • {tool.name}: {tool.description}")
            if tool.parameters:
                for param in tool.parameters:
                    req = "required" if param.required else "optional"
                    print(f"    - {param.name} ({param.type.value}, {req}): {param.description}")

        # Create AutoGen bridge
        print("\n🌉 Creating AutoGen Bridge...")
        bridge = MCPAutoGenBridge(mcp_manager)
        adapter = AutoGenToolAdapter(bridge)

        # Simulate agent getting tools
        agent_name = "CODER"
        print(f"\n🤖 Getting tools for agent: {agent_name}")
        agent_tools = adapter.get_tools_for_agent(agent_name)
        print(f"  Found {len(agent_tools)} tools for {agent_name}")

        # Example: Execute a filesystem operation
        print("\n📁 Demo: Reading a file")

        # Create a test file
        test_dir = "/tmp/mcp-demo"
        os.makedirs(test_dir, exist_ok=True)
        test_file = f"{test_dir}/test.txt"
        with open(test_file, "w") as f:
            f.write("Hello from MCP Filesystem Server!\nThis is a test file.")
        print(f"  Created test file: {test_file}")

        # Execute read_file tool (if available)
        if any(t.name == "read_file" for t in tools):
            print(f"  Reading file via MCP...")
            result = await mcp_manager.execute_tool(
                tool_name="read_file",
                arguments={"path": test_file},
                agent_name=agent_name
            )
            print(f"  File contents:\n{result.result if hasattr(result, 'result') else result}")

        # Example: List directory
        if any(t.name == "list_directory" for t in tools):
            print(f"\n📂 Demo: Listing directory")
            result = await mcp_manager.execute_tool(
                tool_name="list_directory",
                arguments={"path": test_dir},
                agent_name=agent_name
            )
            print(f"  Directory contents:\n{result.result if hasattr(result, 'result') else result}")

        # Get metrics
        print("\n📊 MCP Metrics:")
        metrics = mcp_manager.get_metrics()
        for key, value in metrics.items():
            print(f"  • {key}: {value}")

        # Health check
        print("\n🏥 Health Check:")
        health = await mcp_manager.health_check()
        for server, status in health.items():
            emoji = "✅" if status.healthy else "❌"
            print(f"  {emoji} {server}: {status.status} - {status.message}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        print("\n🧹 Shutting down MCP subsystem...")
        await mcp_manager.shutdown()
        print("✓ Shutdown complete")


async def demo_mcp_with_agent():
    """Demonstrate MCP integration with an AutoGen agent"""

    from agents.specialist import create_engineer_agent

    # Setup logging
    setup_logging(level="INFO")

    # Configure MCP
    filesystem_config = MCPServerConfig(
        name="filesystem",
        type=ServerType.FILESYSTEM,
        transport=TransportType.STDIO,
        command="npx @modelcontextprotocol/server-filesystem",
        env={
            "ALLOWED_DIRECTORIES": "/tmp/mcp-demo,/Users/cjq/Dev/MyProjects/AutoGen/v3"
        }
    )

    mcp_config = MCPConfig(
        enabled=True,
        servers=[filesystem_config]
    )

    # Initialize MCP
    mcp_manager = MCPManager(config=mcp_config)
    await mcp_manager.initialize()

    # Create bridge and adapter
    bridge = MCPAutoGenBridge(mcp_manager)
    adapter = AutoGenToolAdapter(bridge)

    try:
        # Create an engineer agent
        print("Creating ENGINEER agent with MCP tools...")
        engineer = create_engineer_agent()

        # Register MCP tools with the agent
        adapter.register_with_agent(engineer, "ENGINEER")
        print("✓ MCP tools registered with agent")

        # Now the agent can use MCP tools in its workflow
        # This would be used in the actual agent execution context

    finally:
        await mcp_manager.shutdown()


if __name__ == "__main__":
    # Run the basic demo
    print("=" * 60)
    print("MCP Filesystem Server Integration Demo")
    print("=" * 60)

    asyncio.run(demo_filesystem_server())

    # Uncomment to run agent integration demo
    # print("\n" + "=" * 60)
    # print("MCP Agent Integration Demo")
    # print("=" * 60)
    # asyncio.run(demo_mcp_with_agent())
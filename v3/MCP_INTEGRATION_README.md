# MCP Integration for Suntory V3

## Overview

The Model Context Protocol (MCP) integration enables Suntory V3's agents to connect with external tools and services through a standardized protocol. This integration significantly expands the capabilities of our AI agents while maintaining clean architecture and security.

## ✅ Implementation Status

### Completed Components

1. **Core Infrastructure**
   - ✅ MCP configuration management (Pydantic-based)
   - ✅ MCP Manager for orchestration
   - ✅ Client Manager with connection pooling
   - ✅ Server Supervisor for lifecycle management
   - ✅ MCP-AutoGen bridge for tool conversion
   - ✅ Comprehensive error handling
   - ✅ Unit test suite

2. **Alfred Integration**
   - ✅ Enhanced Alfred with MCP capabilities (`alfred/main_mcp.py`)
   - ✅ MCP command interface (`/mcp` commands)
   - ✅ Dynamic tool discovery
   - ✅ Agent-specific permissions

3. **Documentation & Examples**
   - ✅ Development proposal
   - ✅ Demo scripts
   - ✅ Test coverage

## Architecture

```
┌─────────────────────────────────────────────────┐
│                 ALFRED MCP                       │
│         (Enhanced AI Concierge)                 │
└───────────────────┬──────────────────────────────┘
                    │
        ┌───────────▼────────────┐
        │   MCP Manager          │
        │  (Orchestration)       │
        └───────────┬────────────┘
                    │
    ┌───────────────┼───────────────────┐
    │               │                   │
┌───▼──────┐  ┌────▼──────┐  ┌────────▼────────┐
│Client     │  │Server     │  │AutoGen         │
│Manager    │  │Supervisor │  │Bridge          │
└───────────┘  └───────────┘  └─────────────────┘
                    │
         ┌──────────▼───────────────┐
         │    MCP SERVERS           │
         ├──────────────────────────┤
         │ • Filesystem             │
         │ • GitHub                 │
         │ • Database               │
         │ • Web Search             │
         │ • Custom Servers         │
         └──────────────────────────┘
```

## Quick Start

### 1. Installation

```bash
cd v3

# Install Python dependencies
source venv/bin/activate  # or create venv if needed
pip install psutil pydantic pydantic-settings

# Install MCP servers (optional - for actual usage)
npm install -g @modelcontextprotocol/server-filesystem
npm install -g @modelcontextprotocol/server-github
```

### 2. Configuration

Create or update `.env` file:

```env
# MCP Configuration
MCP_ENABLED=true
MCP_MAX_CONNECTIONS=10

# Filesystem Server
MCP_FS_ENABLED=true
MCP_FS_ALLOWED_DIRS=/tmp,/Users/cjq/Dev

# GitHub Server (requires token)
MCP_GITHUB_ENABLED=true
GITHUB_TOKEN=your_github_token
MCP_GITHUB_DEFAULT_OWNER=your_github_username
MCP_GITHUB_DEFAULT_REPO=your_repo

# Database Server (optional)
MCP_DB_ENABLED=false
DATABASE_URL=postgresql://user:pass@localhost/dbname
```

### 3. Usage

#### Basic Demo
```bash
python demo_mcp.py
```

#### In Your Code
```python
from src.alfred.main_mcp import create_alfred_mcp
from src.core.mcp import MCPConfig, MCPServerConfig, ServerType, TransportType

# Configure MCP
config = MCPConfig(
    enabled=True,
    servers=[
        MCPServerConfig(
            name="filesystem",
            type=ServerType.FILESYSTEM,
            transport=TransportType.STDIO,
            command="npx @modelcontextprotocol/server-filesystem",
            env={"ALLOWED_DIRECTORIES": "/tmp,/Users"}
        )
    ]
)

# Create and initialize Alfred with MCP
alfred = create_alfred_mcp(config)
await alfred.initialize()

# Use Alfred with MCP tools
response = await alfred.handle_message("Read the README.md file")

# Execute MCP tools directly
result = await alfred.execute_mcp_tool(
    tool_name="read_file",
    arguments={"path": "/path/to/file.txt"}
)
```

## Available MCP Commands

When using Alfred with MCP integration, these commands are available:

- `/mcp status` - Show MCP subsystem status
- `/mcp tools` - List all available MCP tools
- `/mcp servers` - Show configured MCP servers
- `/mcp reload` - Reload MCP configuration

## Agent Permissions

Different agents have access to different MCP servers by default:

| Agent | Default MCP Access |
|-------|-------------------|
| ALFRED | filesystem, github, web_search, memory |
| CODER | filesystem, github, documentation |
| DATA | database, filesystem |
| ENGINEER | filesystem, github |
| OPS | docker, kubernetes |
| SECURITY | filesystem, github |
| PRODUCT | None (advisory only) |
| UX | None (advisory only) |
| QA | None (advisory only) |

## Testing

Run the comprehensive test suite:

```bash
cd v3
pytest tests/test_mcp.py -v
```

## File Structure

```
v3/
├── src/
│   ├── core/
│   │   └── mcp/
│   │       ├── __init__.py          # Package initialization
│   │       ├── config.py            # Configuration management
│   │       ├── types.py             # Type definitions
│   │       ├── manager.py           # MCP Manager (orchestrator)
│   │       ├── client.py            # Client connection manager
│   │       ├── supervisor.py        # Server lifecycle management
│   │       └── autogen_bridge.py    # AutoGen integration
│   └── alfred/
│       └── main_mcp.py              # Alfred with MCP integration
├── tests/
│   └── test_mcp.py                  # Comprehensive test suite
├── examples/
│   └── mcp_filesystem_demo.py       # Filesystem server demo
├── demo_mcp.py                      # Interactive CLI demo
├── MCP_INTEGRATION_PROPOSAL.md      # Development proposal
└── MCP_INTEGRATION_README.md        # This file
```

## Security Considerations

1. **Server Authentication**: Each MCP server requires proper authentication
2. **Permission Model**: Agent-based permissions restrict tool access
3. **Sandboxing**: MCP servers can run in Docker containers
4. **Input Validation**: All tool parameters are validated
5. **Audit Logging**: All MCP operations are logged

## Performance

- Connection pooling for efficient resource usage
- Async operations throughout
- Caching of tool descriptions
- Health monitoring with automatic restart
- Configurable timeouts and retries

## Extending MCP

### Adding a New MCP Server

1. Create server configuration:
```python
new_server = MCPServerConfig(
    name="my_server",
    type=ServerType.CUSTOM,
    transport=TransportType.STDIO,
    command="my-mcp-server",
    env={"CONFIG": "value"}
)
```

2. Add to MCP config:
```python
config.servers.append(new_server)
```

3. Update agent permissions if needed:
```python
permissions = MCPAgentPermissions(
    agent_name="CODER",
    allowed_servers=["my_server"],
    allowed_tools=["specific_tool"]
)
config.agent_permissions.append(permissions)
```

### Creating Custom MCP Server

Follow the MCP specification to create custom servers that can integrate with Suntory V3.

## Troubleshooting

### MCP Not Initializing
- Check that MCP_ENABLED=true in environment
- Verify MCP server commands are installed
- Check logs for specific error messages

### Tools Not Available
- Verify agent has permission to access the server
- Check server health with `/mcp status`
- Ensure server is running with `/mcp servers`

### Connection Issues
- Check transport configuration (stdio/sse/websocket)
- Verify environment variables are set
- Check network connectivity for SSE/WebSocket

## Future Enhancements

- [ ] WebSocket and SSE transport implementation
- [ ] Dynamic server discovery (mDNS, registry)
- [ ] Advanced caching strategies
- [ ] MCP server marketplace integration
- [ ] Visual tool builder interface
- [ ] Real-time collaboration tools
- [ ] Enhanced monitoring dashboard

## Contributing

When contributing to MCP integration:

1. Follow the existing architecture patterns
2. Add comprehensive tests for new features
3. Update documentation
4. Ensure backward compatibility
5. Run the full test suite before submitting

## Support

For issues or questions about MCP integration:
1. Check this README first
2. Review the test cases for examples
3. Check the logs for detailed error messages
4. Refer to the MCP specification documentation

---

*MCP integration transforms Suntory V3 into an extensible AI platform capable of connecting to any external system while maintaining security and clean architecture.*
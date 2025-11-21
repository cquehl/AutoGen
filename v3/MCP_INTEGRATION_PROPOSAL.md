# MCP Integration Development Proposal for Suntory V3

## Executive Summary

This proposal outlines the integration of Model Context Protocol (MCP) into the Suntory V3 multi-agent system. MCP will enable our agents to connect with external tools and services through a standardized protocol, significantly expanding their capabilities while maintaining our clean architecture.

---

## 1. What is MCP?

**Model Context Protocol (MCP)** is an open standard developed by Anthropic that enables seamless integration between AI applications and external data sources/tools. It provides:

- **Standardized Communication**: Unified protocol for tool integration
- **Security**: Built-in authentication and permission management
- **Flexibility**: Support for various transport mechanisms (stdio, SSE, WebSocket)
- **Ecosystem**: Growing library of pre-built MCP servers

### Key Benefits for Suntory V3:
1. **Expanded Capabilities**: Access to databases, APIs, file systems, and specialized tools
2. **Interoperability**: Connect with any MCP-compatible application
3. **Maintainability**: Clean separation between agent logic and tool implementations
4. **Scalability**: Easy addition of new capabilities without modifying core code

---

## 2. Current V3 Architecture Analysis

Based on our analysis, Suntory V3 has:

### Strengths for MCP Integration:
- **Modular Architecture**: Clean separation of concerns
- **LLM Gateway**: Unified interface for model interactions
- **Agent System**: Both specialist and Magentic-One agents
- **Tool Support**: Existing framework for agent tools
- **Async Support**: Already using async/await patterns
- **Error Handling**: Comprehensive error system

### Integration Points:
1. **LLM Gateway** (`core/llm_gateway.py`): Add MCP tool descriptions to prompts
2. **Agent Tools** (`agents/`): Convert MCP resources to agent tools
3. **Docker Executor** (`core/docker_executor.py`): Run MCP servers in containers
4. **Configuration** (`core/config.py`): MCP server settings
5. **Alfred Main** (`alfred/main_enhanced.py`): MCP orchestration

---

## 3. MCP Integration Architecture

### 3.1 Proposed Architecture

```
┌─────────────────────────────────────────────────┐
│                 ALFRED MAIN                      │
│            (MCP-Enhanced Orchestrator)          │
└───────────────────┬──────────────────────────────┘
                    │
        ┌───────────▼────────────┐
        │   MCP Manager          │
        │  (New Component)       │
        └───────────┬────────────┘
                    │
    ┌───────────────┼───────────────────┐
    │               │                   │
┌───▼──────┐  ┌────▼──────┐  ┌────────▼────────┐
│MCP Client│  │MCP Server │  │MCP Registry     │
│Manager   │  │Supervisor │  │& Discovery      │
└───┬──────┘  └────┬──────┘  └────────┬────────┘
    │              │                   │
    └──────────────┼───────────────────┘
                   │
    ┌──────────────▼───────────────────────┐
    │         MCP SERVERS                  │
    ├───────────────────────────────────────┤
    │ • Filesystem Server (local files)    │
    │ • Database Server (SQL/NoSQL)        │
    │ • GitHub Server (repo operations)    │
    │ • Slack Server (messaging)           │
    │ • Web Search Server (internet)       │
    │ • Memory Server (RAG/vector DB)      │
    │ • Custom Servers (domain-specific)   │
    └──────────────────────────────────────┘
```

### 3.2 New Components

#### MCP Manager (`v3/src/core/mcp/manager.py`)
```python
class MCPManager:
    """Central orchestrator for all MCP operations"""

    async def initialize(self, config: MCPConfig):
        """Initialize MCP subsystem with configuration"""

    async def discover_servers(self) -> List[MCPServer]:
        """Discover available MCP servers"""

    async def connect_server(self, server: MCPServer) -> MCPConnection:
        """Establish connection to an MCP server"""

    async def list_tools(self) -> List[MCPTool]:
        """Get all available tools from connected servers"""

    async def execute_tool(self, tool_name: str, args: Dict) -> Any:
        """Execute a tool and return results"""

    async def handle_resource(self, resource: MCPResource) -> Any:
        """Handle MCP resource requests"""
```

#### MCP Client Manager (`v3/src/core/mcp/client.py`)
```python
class MCPClientManager:
    """Manages MCP client connections"""

    def __init__(self):
        self.clients: Dict[str, MCPClient] = {}
        self.connection_pool = ConnectionPool(max_connections=10)

    async def create_client(self, transport: Transport) -> MCPClient:
        """Create an MCP client with specified transport"""

    async def get_client(self, server_id: str) -> MCPClient:
        """Get or create client for a server"""
```

#### MCP Server Supervisor (`v3/src/core/mcp/supervisor.py`)
```python
class MCPServerSupervisor:
    """Manages lifecycle of MCP servers"""

    async def start_server(self, config: ServerConfig) -> MCPServer:
        """Start an MCP server process"""

    async def stop_server(self, server_id: str):
        """Stop an MCP server"""

    async def restart_server(self, server_id: str):
        """Restart an MCP server"""

    async def health_check(self, server_id: str) -> HealthStatus:
        """Check server health"""

    async def monitor_servers(self):
        """Monitor all running servers"""
```

#### MCP-AutoGen Bridge (`v3/src/core/mcp/autogen_bridge.py`)
```python
class MCPAutoGenBridge:
    """Bridges MCP tools to AutoGen agent tools"""

    def convert_mcp_to_autogen_tool(self, mcp_tool: MCPTool) -> Callable:
        """Convert MCP tool to AutoGen-compatible function"""

    def create_tool_description(self, mcp_tool: MCPTool) -> Dict:
        """Generate tool description for LLM"""

    async def execute_with_retry(self, tool_func: Callable, args: Dict):
        """Execute tool with retry logic"""
```

---

## 4. Integration Strategy

### 4.1 Which Agents Should Use MCP?

#### **Recommended: Selective Integration**

**Primary MCP Users:**
1. **ALFRED (Main Orchestrator)**: Full MCP access for coordination
2. **CODER Agent**: Access to filesystem, GitHub, documentation
3. **DATA Agent**: Database connections, data sources
4. **WEB_SURFER**: Web search, API integrations
5. **FILE_SURFER**: Enhanced file operations

**Limited MCP Access:**
- **ENGINEER**: Code-related MCP tools only
- **OPS**: Infrastructure and monitoring tools
- **SECURITY**: Security scanning tools

**No MCP Access (Pure Advisory):**
- **PRODUCT**: Strategy and planning only
- **UX**: Design recommendations only
- **QA**: Test strategy only (uses CODER for execution)

**Rationale:**
- Maintains clear separation of concerns
- Reduces complexity and potential conflicts
- Improves security by limiting tool access
- Easier to debug and maintain

### 4.2 Implementation Phases

#### Phase 1: Foundation (Week 1-2)
- [ ] Create MCP core components
- [ ] Implement basic client/server management
- [ ] Add configuration support
- [ ] Create AutoGen bridge
- [ ] Unit tests for core functionality

#### Phase 2: Essential Servers (Week 2-3)
- [ ] Integrate filesystem MCP server
- [ ] Integrate GitHub MCP server
- [ ] Integrate database MCP server (PostgreSQL/SQLite)
- [ ] Test with CODER and FILE_SURFER agents

#### Phase 3: Enhanced Capabilities (Week 3-4)
- [ ] Add web search MCP server
- [ ] Add Slack/Discord MCP server
- [ ] Add memory/RAG MCP server
- [ ] Integrate with ALFRED main orchestrator

#### Phase 4: Production Readiness (Week 4-5)
- [ ] Implement health monitoring
- [ ] Add comprehensive error handling
- [ ] Performance optimization
- [ ] Security audit
- [ ] Documentation

---

## 5. Specific MCP Servers to Integrate

### 5.1 Core MCP Servers (Priority 1)

#### **1. Filesystem Server**
- **Purpose**: Advanced file operations beyond basic read/write
- **Features**: Watch files, directory operations, permissions
- **Users**: CODER, FILE_SURFER, ALFRED
- **Source**: Official MCP filesystem server

#### **2. GitHub Server**
- **Purpose**: Repository operations, PR management, issues
- **Features**: Clone, commit, push, PR creation, code review
- **Users**: CODER, ENGINEER, OPS
- **Source**: Official MCP GitHub server

#### **3. PostgreSQL/SQLite Server**
- **Purpose**: Database operations
- **Features**: Query, schema management, migrations
- **Users**: DATA, CODER
- **Source**: Official MCP database servers

### 5.2 Communication Servers (Priority 2)

#### **4. Slack Server**
- **Purpose**: Team communication, notifications
- **Features**: Send messages, read channels, manage threads
- **Users**: ALFRED, OPS
- **Source**: Official MCP Slack server

#### **5. Email Server (Custom)**
- **Purpose**: Email operations
- **Features**: Send, receive, parse emails
- **Users**: ALFRED
- **Implementation**: Custom using SMTP/IMAP

### 5.3 Knowledge Servers (Priority 3)

#### **6. Web Search Server**
- **Purpose**: Internet search and browsing
- **Features**: Search, scrape, summarize
- **Users**: WEB_SURFER, ALFRED
- **Source**: Brave Search MCP or custom

#### **7. Memory/RAG Server**
- **Purpose**: Long-term memory and knowledge retrieval
- **Features**: Store, query, update knowledge base
- **Users**: All agents
- **Implementation**: Custom using ChromaDB/Pinecone

#### **8. Documentation Server**
- **Purpose**: Access to documentation
- **Features**: Search docs, API references
- **Users**: CODER, ENGINEER
- **Source**: Custom or adapted

### 5.4 Development Tools (Priority 4)

#### **9. Docker Server**
- **Purpose**: Container management
- **Features**: Build, run, monitor containers
- **Users**: OPS, CODER
- **Implementation**: Custom using Docker SDK

#### **10. Kubernetes Server**
- **Purpose**: K8s cluster operations
- **Features**: Deploy, scale, monitor
- **Users**: OPS
- **Implementation**: Custom using K8s API

---

## 6. Implementation Details

### 6.1 Configuration Schema

```python
# v3/src/core/mcp/config.py
from pydantic import BaseSettings

class MCPServerConfig(BaseModel):
    name: str
    type: str  # "filesystem", "github", "database", etc.
    transport: str  # "stdio", "sse", "websocket"
    command: Optional[str]  # For stdio transport
    url: Optional[str]  # For SSE/WebSocket
    env: Dict[str, str] = {}
    auto_start: bool = True
    restart_policy: str = "on-failure"
    max_retries: int = 3

class MCPConfig(BaseSettings):
    enabled: bool = True
    servers: List[MCPServerConfig] = []
    max_connections: int = 10
    timeout: int = 30
    health_check_interval: int = 60
    log_level: str = "INFO"

    class Config:
        env_prefix = "MCP_"
```

### 6.2 Environment Variables

```env
# MCP Configuration
MCP_ENABLED=true
MCP_MAX_CONNECTIONS=10
MCP_TIMEOUT=30

# Filesystem Server
MCP_FS_ENABLED=true
MCP_FS_ALLOWED_DIRS=/Users/cjq/Dev/MyProjects/AutoGen,/tmp
MCP_FS_READ_ONLY=false

# GitHub Server
MCP_GITHUB_ENABLED=true
MCP_GITHUB_TOKEN=${GITHUB_TOKEN}
MCP_GITHUB_DEFAULT_OWNER=cjq
MCP_GITHUB_DEFAULT_REPO=AutoGen

# Database Server
MCP_DB_ENABLED=true
MCP_DB_CONNECTION_STRING=postgresql://user:pass@localhost/dbname
MCP_DB_MAX_QUERY_SIZE=10000

# Slack Server
MCP_SLACK_ENABLED=false
MCP_SLACK_TOKEN=${SLACK_BOT_TOKEN}
MCP_SLACK_DEFAULT_CHANNEL=#general

# Web Search Server
MCP_SEARCH_ENABLED=true
MCP_SEARCH_API_KEY=${BRAVE_SEARCH_API_KEY}
MCP_SEARCH_MAX_RESULTS=10
```

### 6.3 Tool Registration Flow

```python
# When an agent requests available tools
async def get_agent_tools(agent_type: str) -> List[Tool]:
    tools = []

    # Get agent's allowed MCP servers
    allowed_servers = get_allowed_servers(agent_type)

    # For each allowed server
    for server_id in allowed_servers:
        # Get MCP client
        client = await mcp_manager.get_client(server_id)

        # List available tools
        mcp_tools = await client.list_tools()

        # Convert to AutoGen tools
        for mcp_tool in mcp_tools:
            autogen_tool = bridge.convert_mcp_to_autogen_tool(mcp_tool)
            tools.append(autogen_tool)

    return tools
```

### 6.4 Error Handling

```python
class MCPError(SuntoryError):
    """Base class for MCP-related errors"""
    pass

class MCPConnectionError(MCPError):
    """Failed to connect to MCP server"""
    pass

class MCPToolExecutionError(MCPError):
    """Tool execution failed"""
    pass

class MCPServerError(MCPError):
    """MCP server error"""
    pass

class MCPTimeoutError(MCPError):
    """MCP operation timed out"""
    pass
```

---

## 7. Security Considerations

### 7.1 Authentication & Authorization
- **Server Authentication**: Each MCP server requires authentication tokens
- **Permission Model**: Agent-based permissions for tool access
- **Audit Logging**: All MCP tool executions logged with agent ID

### 7.2 Sandboxing
- **Docker Isolation**: MCP servers run in Docker containers
- **Resource Limits**: CPU, memory, and time limits per server
- **Network Segmentation**: Servers isolated from production network

### 7.3 Input Validation
- **Parameter Validation**: Strict validation of tool parameters
- **SQL Injection Prevention**: Parameterized queries for database servers
- **Path Traversal Prevention**: Validate file paths in filesystem server

---

## 8. Testing Strategy

### 8.1 Unit Tests
```python
# v3/tests/test_mcp_manager.py
async def test_server_discovery()
async def test_client_creation()
async def test_tool_execution()
async def test_error_handling()
```

### 8.2 Integration Tests
```python
# v3/tests/test_mcp_integration.py
async def test_filesystem_operations()
async def test_github_operations()
async def test_database_queries()
async def test_multi_server_coordination()
```

### 8.3 End-to-End Tests
```python
# v3/tests/test_mcp_e2e.py
async def test_agent_with_mcp_tools()
async def test_alfred_mcp_orchestration()
async def test_failover_scenarios()
```

---

## 9. Performance Considerations

### 9.1 Connection Pooling
- Maintain persistent connections to MCP servers
- Reuse connections across multiple tool calls
- Implement connection timeout and retry logic

### 9.2 Caching
- Cache tool descriptions and schemas
- Cache frequently accessed resources
- Implement TTL-based cache invalidation

### 9.3 Async Operations
- All MCP operations are async
- Parallel tool execution where possible
- Non-blocking server health checks

---

## 10. Monitoring & Observability

### 10.1 Metrics
- MCP server availability
- Tool execution latency
- Error rates per server
- Connection pool utilization

### 10.2 Logging
- Structured logging for all MCP operations
- Correlation IDs for request tracing
- Debug mode for detailed protocol messages

### 10.3 Health Checks
- Periodic server health checks
- Automatic restart on failure
- Alerting for critical failures

---

## 11. Documentation Requirements

### 11.1 Developer Documentation
- MCP integration architecture
- Adding new MCP servers
- Creating custom MCP servers
- Troubleshooting guide

### 11.2 User Documentation
- Available MCP tools per agent
- Configuration guide
- Performance tuning
- Security best practices

### 11.3 API Documentation
- MCP Manager API
- Tool registration API
- Error codes and handling

---

## 12. Migration Path

### 12.1 Backward Compatibility
- Existing agents continue to work without MCP
- Gradual migration of tools to MCP
- Feature flags for MCP enablement

### 12.2 Rollback Strategy
- MCP can be disabled via configuration
- Fallback to native implementations
- Data migration scripts if needed

---

## 13. Success Metrics

### 13.1 Technical Metrics
- ✅ All core MCP servers integrated
- ✅ < 100ms average tool execution latency
- ✅ > 99.9% server availability
- ✅ Zero security vulnerabilities

### 13.2 Business Metrics
- ✅ 50% reduction in custom tool development time
- ✅ 3x increase in available agent capabilities
- ✅ Seamless integration with external systems
- ✅ Improved developer productivity

---

## 14. Timeline & Resources

### Timeline (5-6 weeks)
- **Week 1-2**: Core MCP implementation
- **Week 2-3**: Essential server integration
- **Week 3-4**: Enhanced capabilities
- **Week 4-5**: Testing & optimization
- **Week 5-6**: Documentation & deployment

### Resources Needed
- 1 Senior Developer (full-time)
- 1 DevOps Engineer (part-time)
- MCP server licenses (if any)
- Additional compute resources for MCP servers

---

## 15. Risks & Mitigation

### 15.1 Technical Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| MCP protocol changes | High | Version pinning, compatibility layer |
| Server instability | Medium | Health monitoring, auto-restart |
| Performance degradation | Medium | Caching, connection pooling |
| Security vulnerabilities | High | Regular audits, sandboxing |

### 15.2 Operational Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| Increased complexity | Medium | Comprehensive documentation |
| Debugging difficulty | Medium | Enhanced logging, tracing |
| Resource consumption | Low | Resource limits, monitoring |

---

## 16. Conclusion

MCP integration will transform Suntory V3 into a truly extensible AI platform capable of:
- **Connecting to any external system** via standardized protocol
- **Scaling capabilities** without modifying core code
- **Interoperating** with other MCP-compatible applications
- **Maintaining** clean architecture and separation of concerns

The selective integration approach ensures we gain maximum benefit while maintaining system stability and security.

---

## Appendix A: Example MCP Tool Usage

```python
# Agent using MCP filesystem tool
async def agent_read_file(file_path: str):
    # Get MCP filesystem client
    fs_client = await mcp_manager.get_client("filesystem")

    # Execute read tool
    result = await fs_client.execute_tool(
        "read_file",
        {"path": file_path}
    )

    return result.content

# Agent using MCP GitHub tool
async def agent_create_pr(title: str, body: str):
    # Get MCP GitHub client
    gh_client = await mcp_manager.get_client("github")

    # Create pull request
    pr = await gh_client.execute_tool(
        "create_pull_request",
        {
            "title": title,
            "body": body,
            "base": "main",
            "head": "feature-branch"
        }
    )

    return pr.url
```

## Appendix B: MCP Server Configuration Examples

```yaml
# mcp-servers.yaml
servers:
  - name: filesystem
    type: filesystem
    transport: stdio
    command: "npx @modelcontextprotocol/server-filesystem"
    env:
      ALLOWED_DIRECTORIES: "/Users/cjq/Dev/MyProjects/AutoGen"
    auto_start: true

  - name: github
    type: github
    transport: stdio
    command: "npx @modelcontextprotocol/server-github"
    env:
      GITHUB_TOKEN: "${GITHUB_TOKEN}"
    auto_start: true

  - name: postgres
    type: database
    transport: stdio
    command: "npx @modelcontextprotocol/server-postgres"
    env:
      CONNECTION_STRING: "${DATABASE_URL}"
    auto_start: false
```

---

*This proposal provides a comprehensive roadmap for MCP integration into Suntory V3, ensuring we build a robust, scalable, and maintainable system that significantly enhances our agents' capabilities.*
"""
Test suite for MCP (Model Context Protocol) integration
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import json

# Import MCP components
from src.core.mcp import (
    MCPConfig,
    MCPServerConfig,
    MCPManager,
    MCPClientManager,
    MCPServerSupervisor,
    MCPAutoGenBridge,
    AutoGenToolAdapter,
    TransportType,
    ServerType,
    RestartPolicy,
    MCPTool,
    ToolParameter,
    ToolParameterType,
    HealthStatus,
    ServerStatus,
    get_mcp_config,
    reset_mcp_config,
    get_mcp_manager,
    reset_mcp_manager
)


class TestMCPConfig:
    """Test MCP configuration management"""

    def test_server_config_creation(self):
        """Test creating an MCP server configuration"""
        config = MCPServerConfig(
            name="test_server",
            type=ServerType.FILESYSTEM,
            transport=TransportType.STDIO,
            command="test_command",
            env={"TEST_VAR": "value"},
            auto_start=True,
            restart_policy=RestartPolicy.ON_FAILURE,
            max_retries=3
        )

        assert config.name == "test_server"
        assert config.type == ServerType.FILESYSTEM
        assert config.transport == TransportType.STDIO
        assert config.command == "test_command"
        assert config.env["TEST_VAR"] == "value"
        assert config.auto_start is True
        assert config.restart_policy == RestartPolicy.ON_FAILURE
        assert config.max_retries == 3

    def test_server_config_validation(self):
        """Test server configuration validation"""
        # Should fail - stdio transport requires command
        with pytest.raises(ValueError, match="Command is required for stdio transport"):
            MCPServerConfig(
                name="test",
                type=ServerType.FILESYSTEM,
                transport=TransportType.STDIO,
                command=None
            )

        # Should fail - SSE transport requires URL
        with pytest.raises(ValueError, match="URL is required for sse transport"):
            MCPServerConfig(
                name="test",
                type=ServerType.FILESYSTEM,
                transport=TransportType.SSE,
                url=None
            )

    def test_mcp_config_creation(self):
        """Test creating main MCP configuration"""
        server_config = MCPServerConfig(
            name="test_server",
            type=ServerType.FILESYSTEM,
            transport=TransportType.STDIO,
            command="test_command"
        )

        mcp_config = MCPConfig(
            enabled=True,
            servers=[server_config],
            max_connections=5,
            health_check_interval=30
        )

        assert mcp_config.enabled is True
        assert len(mcp_config.servers) == 1
        assert mcp_config.servers[0].name == "test_server"
        assert mcp_config.max_connections == 5
        assert mcp_config.health_check_interval == 30

    def test_get_server_config(self):
        """Test retrieving specific server configuration"""
        server1 = MCPServerConfig(name="server1", type=ServerType.FILESYSTEM,
                                  transport=TransportType.STDIO, command="cmd1")
        server2 = MCPServerConfig(name="server2", type=ServerType.GITHUB,
                                  transport=TransportType.STDIO, command="cmd2")

        config = MCPConfig(servers=[server1, server2])

        assert config.get_server_config("server1") == server1
        assert config.get_server_config("server2") == server2
        assert config.get_server_config("nonexistent") is None

    def test_agent_permissions(self):
        """Test agent permission configuration"""
        config = MCPConfig()

        # Test default permissions for known agents
        assert "filesystem" in config.get_allowed_servers_for_agent("ALFRED")
        assert "github" in config.get_allowed_servers_for_agent("CODER")
        assert "database" in config.get_allowed_servers_for_agent("DATA")
        assert len(config.get_allowed_servers_for_agent("PRODUCT")) == 0  # Advisory agent

    def test_config_singleton(self):
        """Test MCP config singleton behavior"""
        config1 = get_mcp_config()
        config2 = get_mcp_config()
        assert config1 is config2

        reset_mcp_config()
        config3 = get_mcp_config()
        assert config3 is not config1


class TestMCPManager:
    """Test MCP Manager functionality"""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration"""
        server_config = MCPServerConfig(
            name="test_server",
            type=ServerType.FILESYSTEM,
            transport=TransportType.STDIO,
            command="test_command",
            auto_start=True
        )
        return MCPConfig(enabled=True, servers=[server_config])

    @pytest.fixture
    def manager(self, mock_config):
        """Create MCP manager with mock config"""
        return MCPManager(config=mock_config)

    @pytest.mark.asyncio
    async def test_manager_initialization(self, manager):
        """Test MCP manager initialization"""
        assert manager.initialized is False
        assert len(manager.connected_servers) == 0
        assert len(manager.available_tools) == 0

        # Mock the server supervisor and client manager
        with patch.object(manager.server_supervisor, 'start_server', new_callable=AsyncMock) as mock_start:
            with patch.object(manager.client_manager, 'create_client', new_callable=AsyncMock) as mock_client:
                mock_client.return_value = Mock(
                    list_tools=AsyncMock(return_value=[]),
                    get_capabilities=AsyncMock(return_value=Mock())
                )
                mock_start.return_value = Mock()

                await manager.initialize()

                assert manager.initialized is True
                mock_start.assert_called_once()
                mock_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_tools(self, manager):
        """Test listing available tools"""
        # Create mock tools
        tool1 = MCPTool(name="tool1", description="Test tool 1")
        tool2 = MCPTool(name="tool2", description="Test tool 2")

        manager.available_tools = {
            "tool1": tool1,
            "tool2": tool2
        }
        manager.tool_to_server = {
            "tool1": "test_server",
            "tool2": "test_server"
        }
        manager.initialized = True

        # List all tools
        tools = await manager.list_tools()
        assert len(tools) == 2
        assert tool1 in tools
        assert tool2 in tools

        # List tools for specific agent with permissions
        manager.config.agent_permissions = []  # Use default permissions
        tools = await manager.list_tools("ALFRED")
        assert len(tools) == 0  # No filesystem server in connected_servers

    @pytest.mark.asyncio
    async def test_execute_tool(self, manager):
        """Test tool execution"""
        # Setup mock tool
        tool = MCPTool(
            name="test_tool",
            description="Test tool",
            parameters=[
                ToolParameter(
                    name="param1",
                    type=ToolParameterType.STRING,
                    description="Test parameter",
                    required=True
                )
            ]
        )

        manager.available_tools = {"test_tool": tool}
        manager.tool_to_server = {"test_tool": "test_server"}
        manager.initialized = True

        # Mock connection and client
        mock_client = Mock()
        mock_client.execute_tool = AsyncMock(return_value={"result": "success"})

        mock_connection = Mock(client=mock_client)
        manager.connected_servers = {"test_server": mock_connection}

        # Execute tool
        result = await manager.execute_tool(
            tool_name="test_tool",
            arguments={"param1": "value1"},
            agent_name="ALFRED"
        )

        assert result.success is True
        assert result.tool_name == "test_tool"
        mock_client.execute_tool.assert_called_once_with("test_tool", {"param1": "value1"})

    @pytest.mark.asyncio
    async def test_health_check(self, manager):
        """Test server health checking"""
        manager.connected_servers = {"test_server": Mock()}

        with patch.object(manager.server_supervisor, 'health_check', new_callable=AsyncMock) as mock_health:
            mock_health.return_value = HealthStatus(
                healthy=True,
                status="healthy",
                message="Server is running"
            )

            health = await manager.health_check("test_server")

            assert "test_server" in health
            assert health["test_server"].healthy is True
            assert health["test_server"].status == "healthy"

    def test_get_metrics(self, manager):
        """Test metrics collection"""
        # Add some operation data
        manager.operation_counts = {"tool1": 5, "tool2": 3}
        manager.operation_times = {
            "tool1": [0.1, 0.2, 0.15],
            "tool2": [0.3, 0.25]
        }

        metrics = manager.get_metrics()

        assert metrics["connected_servers"] == 0
        assert metrics["available_tools"] == 0
        assert metrics["operation_counts"]["tool1"] == 5
        assert metrics["operation_counts"]["tool2"] == 3
        assert metrics["average_execution_times"]["tool1"] == pytest.approx(0.15)
        assert metrics["average_execution_times"]["tool2"] == pytest.approx(0.275)

    @pytest.mark.asyncio
    async def test_shutdown(self, manager):
        """Test manager shutdown"""
        manager.initialized = True
        manager.connected_servers = {"test_server": Mock()}

        with patch.object(manager, 'disconnect_server', new_callable=AsyncMock) as mock_disconnect:
            with patch.object(manager.server_supervisor, 'shutdown', new_callable=AsyncMock) as mock_supervisor_shutdown:
                await manager.shutdown()

                mock_disconnect.assert_called_once_with("test_server")
                mock_supervisor_shutdown.assert_called_once()
                assert manager.initialized is False


class TestMCPClientManager:
    """Test MCP Client Manager functionality"""

    @pytest.fixture
    def client_manager(self):
        """Create client manager"""
        return MCPClientManager(max_connections=5)

    @pytest.mark.asyncio
    async def test_create_stdio_client(self, client_manager):
        """Test creating STDIO transport client"""
        with patch('src.core.mcp.client.StdioTransport') as mock_transport_class:
            mock_transport = Mock()
            mock_transport.connect = AsyncMock()
            mock_transport_class.return_value = mock_transport

            with patch('src.core.mcp.client.RealMCPClient') as mock_client_class:
                mock_client = Mock()
                mock_client.connect = AsyncMock()
                mock_client.connected = True
                mock_client_class.return_value = mock_client

                client = await client_manager.create_client(
                    server_id="test_server",
                    transport_type=TransportType.STDIO,
                    transport_config={
                        "command": "test_command",
                        "env": {"TEST": "value"}
                    }
                )

                assert client == mock_client
                mock_transport_class.assert_called_once()
                mock_client.connect.assert_called_once()
                assert "test_server" in client_manager.pool.connections

    @pytest.mark.asyncio
    async def test_connection_pooling(self, client_manager):
        """Test connection pool reuse"""
        # Create mock client
        mock_client = Mock()
        mock_client.connected = True
        client_manager.pool.connections["test_server"] = mock_client

        # Request same client
        client = await client_manager.get_client("test_server")

        assert client is mock_client  # Should return same instance

    @pytest.mark.asyncio
    async def test_close_client(self, client_manager):
        """Test closing a client connection"""
        mock_client = Mock()
        mock_client.disconnect = AsyncMock()
        client_manager.pool.connections["test_server"] = mock_client

        await client_manager.close_client("test_server")

        mock_client.disconnect.assert_called_once()
        assert "test_server" not in client_manager.pool.connections


class TestMCPServerSupervisor:
    """Test MCP Server Supervisor functionality"""

    @pytest.fixture
    def supervisor(self):
        """Create server supervisor"""
        return MCPServerSupervisor()

    @pytest.fixture
    def server_config(self):
        """Create test server configuration"""
        return MCPServerConfig(
            name="test_server",
            type=ServerType.FILESYSTEM,
            transport=TransportType.STDIO,
            command="echo 'test'",
            restart_policy=RestartPolicy.ON_FAILURE,
            max_retries=3
        )

    @pytest.mark.asyncio
    async def test_start_server(self, supervisor, server_config):
        """Test starting a server"""
        with patch('asyncio.create_subprocess_exec', new_callable=AsyncMock) as mock_subprocess:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_process.returncode = None
            mock_process.stderr = AsyncMock()
            mock_subprocess.return_value = mock_process

            server = await supervisor.start_server(server_config)

            assert server.id == "test_server"
            assert server.status == ServerStatus.RUNNING
            assert server.process_id == 12345
            assert "test_server" in supervisor.servers

    @pytest.mark.asyncio
    async def test_stop_server(self, supervisor, server_config):
        """Test stopping a server"""
        # Create mock server process
        mock_process = Mock()
        mock_process.terminate = Mock()
        mock_process.wait = AsyncMock()
        mock_process.returncode = 0

        server_proc = Mock()
        server_proc.process = mock_process
        server_proc.status = ServerStatus.RUNNING
        server_proc.stop = AsyncMock()

        supervisor.servers["test_server"] = server_proc

        await supervisor.stop_server("test_server")

        server_proc.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check(self, supervisor, server_config):
        """Test server health checking"""
        # Create mock server process
        server_proc = Mock()
        server_proc.is_running = True
        server_proc.config = server_config
        server_proc.restart_count = 0
        server_proc.get_resource_usage = Mock(return_value={
            "cpu_percent": 10.5,
            "memory_mb": 128.3
        })
        server_proc.uptime = Mock()

        supervisor.servers["test_server"] = server_proc

        health = await supervisor.health_check("test_server")

        assert health.healthy is True
        assert health.status == "healthy"
        assert health.error_count == 0

    def test_get_running_servers(self, supervisor):
        """Test getting list of running servers"""
        # Create mock servers
        server1 = Mock()
        server1.is_running = True

        server2 = Mock()
        server2.is_running = False

        server3 = Mock()
        server3.is_running = True

        supervisor.servers = {
            "server1": server1,
            "server2": server2,
            "server3": server3
        }

        running = supervisor.get_running_servers()

        assert len(running) == 2
        assert "server1" in running
        assert "server3" in running
        assert "server2" not in running


class TestMCPAutoGenBridge:
    """Test MCP-AutoGen bridge functionality"""

    @pytest.fixture
    def mock_manager(self):
        """Create mock MCP manager"""
        manager = Mock()
        manager.list_tools = AsyncMock()
        manager.execute_tool = AsyncMock()
        return manager

    @pytest.fixture
    def bridge(self, mock_manager):
        """Create bridge with mock manager"""
        return MCPAutoGenBridge(mcp_manager=mock_manager)

    def test_convert_tool_to_autogen(self, bridge):
        """Test converting MCP tool to AutoGen function"""
        tool = MCPTool(
            name="test_tool",
            description="A test tool",
            parameters=[
                ToolParameter(
                    name="input",
                    type=ToolParameterType.STRING,
                    description="Input string",
                    required=True
                ),
                ToolParameter(
                    name="count",
                    type=ToolParameterType.NUMBER,
                    description="Count value",
                    required=False,
                    default=1
                )
            ],
            returns="Processed result"
        )

        # Convert tool
        func = bridge.convert_mcp_to_autogen_tool(tool)

        assert callable(func)
        assert func.__name__ == "test_tool"
        assert "A test tool" in func.__doc__
        assert "input" in func.__annotations__
        assert func.__annotations__["input"] == str
        assert func.__annotations__["count"] == Optional[float]

    def test_create_tool_description(self, bridge):
        """Test creating tool description for LLM"""
        tool = MCPTool(
            name="process_data",
            description="Process input data",
            parameters=[
                ToolParameter(
                    name="data",
                    type=ToolParameterType.OBJECT,
                    description="Input data object",
                    required=True
                ),
                ToolParameter(
                    name="format",
                    type=ToolParameterType.STRING,
                    description="Output format",
                    required=False,
                    enum=["json", "xml", "csv"],
                    default="json"
                )
            ]
        )

        description = bridge.create_tool_description(tool)

        assert description["name"] == "process_data"
        assert description["description"] == "Process input data"
        assert "data" in description["parameters"]["properties"]
        assert "format" in description["parameters"]["properties"]
        assert description["parameters"]["properties"]["format"]["enum"] == ["json", "xml", "csv"]
        assert description["parameters"]["required"] == ["data"]

    @pytest.mark.asyncio
    async def test_execute_mcp_tool(self, bridge, mock_manager):
        """Test executing an MCP tool"""
        # Setup mock execution
        from src.core.mcp.types import ToolExecutionResult
        mock_result = ToolExecutionResult(
            tool_name="test_tool",
            success=True,
            result={"output": "success"},
            execution_time=0.5,
            server="test_server"
        )
        mock_manager.execute_tool.return_value = mock_result

        # Execute tool
        result = await bridge._execute_mcp_tool(
            tool_name="test_tool",
            arguments={"input": "test"},
            agent_name="ALFRED"
        )

        assert result == {"output": "success"}
        mock_manager.execute_tool.assert_called_once_with(
            tool_name="test_tool",
            arguments={"input": "test"},
            agent_name="ALFRED"
        )

    def test_validate_arguments(self, bridge):
        """Test argument validation"""
        tool = MCPTool(
            name="test",
            description="Test",
            parameters=[
                ToolParameter(
                    name="required_param",
                    type=ToolParameterType.STRING,
                    description="Required",
                    required=True
                ),
                ToolParameter(
                    name="optional_param",
                    type=ToolParameterType.NUMBER,
                    description="Optional",
                    required=False,
                    min_value=0,
                    max_value=100
                )
            ]
        )

        # Valid arguments
        bridge._validate_arguments(tool, {"required_param": "test", "optional_param": 50})

        # Missing required parameter
        with pytest.raises(ValueError, match="Missing required parameter"):
            bridge._validate_arguments(tool, {"optional_param": 50})

        # Wrong type
        with pytest.raises(TypeError, match="must be a string"):
            bridge._validate_arguments(tool, {"required_param": 123})

        # Out of range
        with pytest.raises(ValueError, match="must be <="):
            bridge._validate_arguments(tool, {"required_param": "test", "optional_param": 150})


class TestAutoGenToolAdapter:
    """Test AutoGen tool adapter functionality"""

    @pytest.fixture
    def mock_bridge(self):
        """Create mock bridge"""
        bridge = Mock()
        bridge.mcp_manager = Mock()
        bridge.mcp_manager.list_tools = AsyncMock()
        bridge.create_autogen_tool_registry = Mock()
        bridge.create_tool_description = Mock()
        bridge.convert_mcp_to_autogen_tool = Mock()
        return bridge

    @pytest.fixture
    def adapter(self, mock_bridge):
        """Create adapter with mock bridge"""
        adapter = AutoGenToolAdapter()
        adapter.bridge = mock_bridge
        return adapter

    def test_get_tools_for_agent(self, adapter, mock_bridge):
        """Test getting tools for an agent"""
        # Setup mock registry
        mock_bridge.create_autogen_tool_registry.return_value = {
            "tool1": Mock(),
            "tool2": Mock(),
            "tool3": Mock()
        }

        tools = adapter.get_tools_for_agent("ALFRED")

        assert len(tools) == 3
        mock_bridge.create_autogen_tool_registry.assert_called_once_with("ALFRED", include_descriptions=False)

    def test_register_with_agent(self, adapter):
        """Test registering MCP tools with an AutoGen agent"""
        # Create mock agent
        mock_agent = Mock()
        mock_agent.register_tool = Mock()

        # Setup mock tools
        adapter.get_tools_for_agent = Mock(return_value=[Mock(), Mock()])

        adapter.register_with_agent(mock_agent, "ENGINEER")

        assert mock_agent.register_tool.call_count == 2
        adapter.get_tools_for_agent.assert_called_once_with("ENGINEER")


# Integration tests
class TestMCPIntegration:
    """Integration tests for MCP components"""

    @pytest.mark.asyncio
    async def test_full_mcp_flow(self):
        """Test complete MCP flow from configuration to tool execution"""
        # Create configuration
        config = MCPConfig(
            enabled=True,
            servers=[
                MCPServerConfig(
                    name="test_server",
                    type=ServerType.FILESYSTEM,
                    transport=TransportType.STDIO,
                    command="echo 'test'",
                    auto_start=False  # Don't auto-start in test
                )
            ]
        )

        # Create manager
        manager = MCPManager(config=config)

        # Mock server and client creation
        with patch.object(manager.server_supervisor, 'start_server', new_callable=AsyncMock):
            with patch.object(manager.client_manager, 'create_client', new_callable=AsyncMock) as mock_create:
                # Create mock client with tools
                mock_client = Mock()
                mock_client.list_tools = AsyncMock(return_value=[
                    MCPTool(name="test_tool", description="Test tool")
                ])
                mock_client.execute_tool = AsyncMock(return_value={"result": "success"})
                mock_client.get_capabilities = AsyncMock(return_value=Mock())
                mock_create.return_value = mock_client

                # Initialize
                await manager.initialize()

                # Create bridge
                bridge = MCPAutoGenBridge(manager)

                # Get tools for agent
                tools = await manager.list_tools("ALFRED")
                assert len(tools) > 0

                # Convert tool
                autogen_tool = bridge.convert_mcp_to_autogen_tool(tools[0], "ALFRED")
                assert callable(autogen_tool)

                # Execute tool
                manager.connected_servers["test_server"] = Mock(client=mock_client)
                manager.available_tools["test_tool"] = tools[0]
                manager.tool_to_server["test_tool"] = "test_server"

                result = await manager.execute_tool(
                    tool_name="test_tool",
                    arguments={},
                    agent_name="ALFRED"
                )

                assert result.success is True

                # Cleanup
                await manager.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
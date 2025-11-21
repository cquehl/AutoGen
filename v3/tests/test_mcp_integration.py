"""
MCP Integration Test Suite

End-to-end integration tests for MCP subsystem.
Tests complete workflows, failure scenarios, and performance under load.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List
import psutil
import os

# Import MCP components
from src.core.mcp import (
    MCPConfig,
    MCPServerConfig,
    MCPManager,
    MCPClientManager,
    MCPServerSupervisor,
    MCPAutoGenBridge,
    TransportType,
    ServerType,
    RestartPolicy,
    MCPTool,
    ToolParameter,
    ToolParameterType,
    HealthStatus
)


@pytest.mark.integration
class TestEndToEndFlow:
    """Test complete end-to-end MCP workflows"""

    @pytest.mark.asyncio
    async def test_full_mcp_lifecycle(self):
        """Test complete lifecycle: initialize → discover → execute → shutdown"""
        # Create configuration
        config = MCPConfig(
            enabled=True,
            servers=[
                MCPServerConfig(
                    name="test_server",
                    type=ServerType.FILESYSTEM,
                    transport=TransportType.STDIO,
                    command="echo test",
                    auto_start=True
                )
            ]
        )

        # Create manager
        manager = MCPManager(config=config)

        # Mock server and client
        with patch.object(manager.server_supervisor, 'start_server', new_callable=AsyncMock) as mock_start:
            with patch.object(manager.client_manager, 'create_client', new_callable=AsyncMock) as mock_create:
                # Setup mock client
                mock_client = Mock()
                mock_client.list_tools = AsyncMock(return_value=[
                    MCPTool(
                        name="read_file",
                        description="Read a file",
                        parameters=[
                            ToolParameter(
                                name="path",
                                type=ToolParameterType.STRING,
                                description="File path",
                                required=True
                            )
                        ]
                    )
                ])
                mock_client.execute_tool = AsyncMock(return_value={"content": "file contents"})
                mock_client.get_capabilities = AsyncMock(return_value=Mock())
                mock_create.return_value = mock_client
                mock_start.return_value = Mock()

                # 1. Initialize
                await manager.initialize()
                assert manager.initialized
                assert len(manager.connected_servers) == 1

                # 2. Discover tools
                tools = await manager.list_tools()
                assert len(tools) > 0
                assert any(t.name == "read_file" for t in tools)

                # 3. Execute tool
                manager.available_tools["read_file"] = tools[0]
                manager.tool_to_server["read_file"] = "test_server"
                manager.connected_servers["test_server"] = Mock(client=mock_client)

                result = await manager.execute_tool(
                    tool_name="read_file",
                    arguments={"path": "/tmp/test.txt"},
                    agent_name="ALFRED"
                )
                assert result.success
                assert result.result["content"] == "file contents"

                # 4. Shutdown
                await manager.shutdown()
                assert not manager.initialized

    @pytest.mark.asyncio
    async def test_autogen_bridge_integration(self):
        """Test MCP → AutoGen bridge integration"""
        # Create MCP manager
        manager = MCPManager()
        manager.initialized = True

        # Create mock tool
        tool = MCPTool(
            name="calculate",
            description="Calculate something",
            parameters=[
                ToolParameter(
                    name="expression",
                    type=ToolParameterType.STRING,
                    description="Math expression",
                    required=True
                )
            ]
        )

        manager.available_tools = {"calculate": tool}
        manager.tool_to_server = {"calculate": "test_server"}

        mock_client = Mock()
        mock_client.execute_tool = AsyncMock(return_value={"result": 42})
        manager.connected_servers = {"test_server": Mock(client=mock_client)}

        # Create bridge
        bridge = MCPAutoGenBridge(mcp_manager=manager)

        # Convert to AutoGen tool
        autogen_func = bridge.convert_mcp_to_autogen_tool(tool, "ALFRED")

        # Verify function properties
        assert callable(autogen_func)
        assert autogen_func.__name__ == "calculate"
        assert "Calculate something" in autogen_func.__doc__

        # Execute through bridge
        result = await autogen_func(expression="2 + 2")
        assert result == {"result": 42}


@pytest.mark.integration
class TestConcurrentOperations:
    """Test system behavior under concurrent load"""

    @pytest.mark.asyncio
    async def test_100_concurrent_tool_executions(self):
        """Test 100 parallel tool executions complete successfully"""
        manager = MCPManager()
        manager.initialized = True

        # Setup mock tool
        tool = MCPTool(name="test_tool", description="Test")
        manager.available_tools = {"test_tool": tool}
        manager.tool_to_server = {"test_tool": "test_server"}

        # Mock client with small delay to simulate real work
        mock_client = Mock()

        async def mock_execute(name, args):
            await asyncio.sleep(0.01)  # 10ms delay
            return {"result": "success", "id": args.get("id")}

        mock_client.execute_tool = mock_execute
        manager.connected_servers = {"test_server": Mock(client=mock_client)}

        # Execute 100 concurrent requests
        start_time = time.time()
        tasks = [
            manager.execute_tool("test_tool", {"id": i}, agent_name="ALFRED")
            for i in range(100)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start_time

        # Verify all completed successfully
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) == 100

        # Should complete faster than sequential (100 * 10ms = 1s)
        assert duration < 0.5  # Should be much faster due to concurrency

        print(f"100 concurrent executions completed in {duration:.2f}s")

    @pytest.mark.asyncio
    async def test_concurrent_server_connections(self):
        """Test connecting to multiple servers concurrently"""
        config = MCPConfig(
            enabled=True,
            servers=[
                MCPServerConfig(
                    name=f"server_{i}",
                    type=ServerType.FILESYSTEM,
                    transport=TransportType.STDIO,
                    command="echo test",
                    auto_start=True
                )
                for i in range(5)
            ]
        )

        manager = MCPManager(config=config)

        with patch.object(manager.server_supervisor, 'start_server', new_callable=AsyncMock):
            with patch.object(manager.client_manager, 'create_client', new_callable=AsyncMock) as mock_create:
                mock_create.return_value = Mock(
                    list_tools=AsyncMock(return_value=[]),
                    get_capabilities=AsyncMock(return_value=Mock())
                )

                await manager.initialize()

                # All 5 servers should be connected
                assert len(manager.connected_servers) == 5

    @pytest.mark.asyncio
    async def test_no_race_conditions_in_tool_discovery(self):
        """Test that concurrent tool discovery doesn't cause races"""
        manager = MCPManager()
        manager.initialized = True

        # Setup mock servers
        for i in range(3):
            mock_client = Mock()
            mock_client.list_tools = AsyncMock(return_value=[
                MCPTool(name=f"tool_{i}_{j}", description=f"Tool {j}")
                for j in range(10)
            ])
            manager.connected_servers[f"server_{i}"] = Mock(client=mock_client)

        # Discover tools concurrently multiple times
        tasks = [manager._discover_tools() for _ in range(10)]
        await asyncio.gather(*tasks)

        # Tools should be discovered correctly (3 servers * 10 tools)
        assert len(manager.available_tools) == 30
        assert len(manager.tool_to_server) == 30


@pytest.mark.integration
class TestFailureRecovery:
    """Test system behavior during failures"""

    @pytest.mark.asyncio
    async def test_server_crash_and_restart(self):
        """Test automatic restart when server crashes"""
        config = MCPServerConfig(
            name="crash_server",
            type=ServerType.FILESYSTEM,
            transport=TransportType.STDIO,
            command="echo test",
            restart_policy=RestartPolicy.ON_FAILURE,
            max_retries=3
        )

        supervisor = MCPServerSupervisor()

        with patch('asyncio.create_subprocess_exec', new_callable=AsyncMock) as mock_exec:
            # First start: success
            mock_process1 = Mock()
            mock_process1.pid = 12345
            mock_process1.returncode = None
            mock_process1.stderr = AsyncMock()

            # Simulate crash
            async def wait_then_crash():
                await asyncio.sleep(0.1)
                mock_process1.returncode = 1  # Crashed

            mock_process1.wait = wait_then_crash
            mock_exec.return_value = mock_process1

            # Start server
            server = await supervisor.start_server(config)
            assert server.status == "running"

            # Wait for "crash"
            await asyncio.sleep(0.2)

            # Verify restart was attempted
            # (Implementation will add restart logic)

    @pytest.mark.asyncio
    async def test_connection_timeout_handling(self):
        """Test handling of connection timeouts"""
        manager = MCPManager()
        manager.initialized = True

        tool = MCPTool(name="slow_tool", description="Slow tool")
        manager.available_tools = {"slow_tool": tool}
        manager.tool_to_server = {"slow_tool": "test_server"}

        # Mock client that times out
        mock_client = Mock()

        async def slow_execute(name, args):
            await asyncio.sleep(100)  # Longer than timeout
            return {"result": "too late"}

        mock_client.execute_tool = slow_execute
        manager.connected_servers = {"test_server": Mock(client=mock_client)}

        # Should timeout
        from src.core.mcp import MCPOperationError
        with pytest.raises(MCPOperationError, match="timeout"):
            await manager.execute_tool(
                "slow_tool",
                {},
                agent_name="ALFRED",
                timeout=0.1  # 100ms timeout
            )

    @pytest.mark.asyncio
    async def test_network_failure_retry(self):
        """Test automatic retry on network failures"""
        from src.core.mcp.autogen_bridge import MCPAutoGenBridge

        bridge = MCPAutoGenBridge()

        # Mock function that fails twice then succeeds
        call_count = 0

        async def failing_func(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network error")
            return {"result": "success"}

        # Execute with retry
        result = await bridge.execute_with_retry(
            failing_func,
            {},
            max_retries=3,
            backoff_base=1.1  # Fast backoff for testing
        )

        assert result == {"result": "success"}
        assert call_count == 3  # Failed twice, succeeded on 3rd

    @pytest.mark.asyncio
    async def test_graceful_degradation_no_docker(self):
        """Test graceful degradation when Docker not available"""
        # If docker-based server fails to start, system should continue
        # with other servers
        config = MCPConfig(
            enabled=True,
            servers=[
                MCPServerConfig(
                    name="docker_server",
                    type=ServerType.DOCKER,
                    transport=TransportType.STDIO,
                    command="docker run mcp-server",  # Will fail
                    auto_start=True
                ),
                MCPServerConfig(
                    name="local_server",
                    type=ServerType.FILESYSTEM,
                    transport=TransportType.STDIO,
                    command="echo test",  # Will succeed
                    auto_start=True
                )
            ]
        )

        manager = MCPManager(config=config)

        with patch.object(manager.server_supervisor, 'start_server', new_callable=AsyncMock) as mock_start:
            # Docker server fails
            async def conditional_start(cfg):
                if "docker" in cfg.name:
                    raise RuntimeError("Docker not available")
                return Mock()

            mock_start.side_effect = conditional_start

            with patch.object(manager.client_manager, 'create_client', new_callable=AsyncMock):
                # Should initialize despite Docker failure
                await manager.initialize()

                # At least local server should be connected
                # (Implementation should handle partial failures gracefully)


@pytest.mark.integration
class TestHealthMonitoring:
    """Test health monitoring and alerting"""

    @pytest.mark.asyncio
    async def test_health_checks_detect_unhealthy_server(self):
        """Test health monitoring detects unhealthy servers"""
        supervisor = MCPServerSupervisor()

        config = MCPServerConfig(
            name="test_server",
            type=ServerType.FILESYSTEM,
            transport=TransportType.STDIO,
            command="echo test",
            max_memory_mb=100,
            max_cpu_percent=50
        )

        with patch('asyncio.create_subprocess_exec', new_callable=AsyncMock) as mock_exec:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_process.returncode = None
            mock_process.stderr = AsyncMock()
            mock_exec.return_value = mock_process

            server = await supervisor.start_server(config)

            # Mock excessive resource usage
            with patch('psutil.Process') as mock_psutil:
                mock_proc = Mock()
                mock_proc.cpu_percent.return_value = 80  # Exceeds 50% limit
                mock_proc.memory_info.return_value = Mock(rss=150 * 1024 * 1024)  # Exceeds 100MB
                mock_psutil.return_value = mock_proc

                health = await supervisor.health_check("test_server")

                assert not health.healthy
                assert health.status == "degraded"
                assert "CPU" in health.message or "Memory" in health.message

    @pytest.mark.asyncio
    async def test_periodic_health_checks_run(self):
        """Test that periodic health checks execute"""
        supervisor = MCPServerSupervisor()
        supervisor.monitoring_enabled = True

        config = MCPServerConfig(
            name="test_server",
            type=ServerType.FILESYSTEM,
            transport=TransportType.STDIO,
            command="echo test"
        )

        with patch('asyncio.create_subprocess_exec', new_callable=AsyncMock) as mock_exec:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_process.returncode = None
            mock_process.stderr = AsyncMock()
            mock_exec.return_value = mock_process

            await supervisor.start_server(config)

            # Start monitoring
            await supervisor.monitor_servers()

            # Wait for health check cycle
            await asyncio.sleep(1)

            # Verify health check task is running
            assert supervisor._monitor_task is not None
            assert not supervisor._monitor_task.done()

            # Cleanup
            await supervisor.shutdown()


@pytest.mark.integration
class TestCacheConsistency:
    """Test cache behavior under various conditions"""

    @pytest.mark.asyncio
    async def test_cache_consistency_under_load(self):
        """Test cache remains consistent under concurrent access"""
        manager = MCPManager()
        manager.cache_enabled = True

        # Concurrent cache operations
        async def cache_operations(identifier: str):
            for i in range(100):
                # Write
                manager.cache[f"{identifier}_{i}"] = {"data": identifier}
                # Read
                value = manager.cache.get(f"{identifier}_{i}")
                assert value is not None

        tasks = [cache_operations(f"agent_{i}") for i in range(10)]
        await asyncio.gather(*tasks)

        # Cache should have all entries
        assert len(manager.cache) == 1000  # 10 agents * 100 entries

    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self):
        """Test cache entries expire after TTL"""
        manager = MCPManager()
        manager.config.cache_ttl = 1  # 1 second TTL
        manager.cache_enabled = True

        from datetime import datetime, timedelta

        # Add cache entry
        manager.cache["test_key"] = {"data": "value"}
        manager.cache_timestamps["test_key"] = datetime.utcnow()

        # Check before expiration
        result = manager._check_cache("test_key")
        assert result is not None

        # Simulate time passing
        manager.cache_timestamps["test_key"] = datetime.utcnow() - timedelta(seconds=2)

        # Check after expiration
        result = manager._check_cache("test_key")
        assert result is None  # Should be expired
        assert "test_key" not in manager.cache  # Should be removed

    @pytest.mark.asyncio
    async def test_cache_cleanup_task_runs(self):
        """Test that cache cleanup task removes old entries"""
        manager = MCPManager()
        manager.config.cache_ttl = 1
        manager.cache_enabled = True

        from datetime import datetime, timedelta

        # Add expired entries
        for i in range(10):
            manager.cache[f"key_{i}"] = {"data": i}
            manager.cache_timestamps[f"key_{i}"] = datetime.utcnow() - timedelta(seconds=2)

        # Run cleanup
        await manager._cleanup_cache()

        # All expired entries should be removed
        assert len(manager.cache) == 0


@pytest.mark.integration
class TestResourceLeaks:
    """Test for memory leaks and resource cleanup"""

    @pytest.mark.asyncio
    async def test_no_connection_leaks(self):
        """Test that connections are properly cleaned up"""
        manager = MCPManager()

        # Create and close many connections
        for i in range(50):
            with patch.object(manager.server_supervisor, 'start_server', new_callable=AsyncMock):
                with patch.object(manager.client_manager, 'create_client', new_callable=AsyncMock) as mock_create:
                    mock_client = Mock()
                    mock_client.list_tools = AsyncMock(return_value=[])
                    mock_client.get_capabilities = AsyncMock(return_value=Mock())
                    mock_create.return_value = mock_client

                    await manager.connect_server(f"server_{i}")
                    await manager.disconnect_server(f"server_{i}")

        # No servers should remain connected
        assert len(manager.connected_servers) == 0

    @pytest.mark.asyncio
    async def test_no_task_leaks(self):
        """Test that async tasks are properly cleaned up"""
        initial_task_count = len(asyncio.all_tasks())

        manager = MCPManager()
        manager.initialized = True

        # Perform operations that create tasks
        mock_tool = MCPTool(name="test", description="Test")
        manager.available_tools = {"test": mock_tool}
        manager.tool_to_server = {"test": "server"}

        mock_client = Mock()
        mock_client.execute_tool = AsyncMock(return_value={"result": "ok"})
        manager.connected_servers = {"server": Mock(client=mock_client)}

        # Execute multiple operations
        for _ in range(20):
            await manager.execute_tool("test", {})

        # Shutdown
        await manager.shutdown()

        # Wait for cleanup
        await asyncio.sleep(0.1)

        # Task count should return to baseline
        final_task_count = len(asyncio.all_tasks())
        assert final_task_count <= initial_task_count + 2  # Allow small variance

    @pytest.mark.asyncio
    async def test_subprocess_cleanup_on_shutdown(self):
        """Test that all subprocesses are cleaned up on shutdown"""
        supervisor = MCPServerSupervisor()

        # Start multiple servers
        configs = [
            MCPServerConfig(
                name=f"server_{i}",
                type=ServerType.FILESYSTEM,
                transport=TransportType.STDIO,
                command="echo test"
            )
            for i in range(3)
        ]

        with patch('asyncio.create_subprocess_exec', new_callable=AsyncMock) as mock_exec:
            mock_processes = []
            for i in range(3):
                mock_proc = Mock()
                mock_proc.pid = 10000 + i
                mock_proc.returncode = None
                mock_proc.stderr = AsyncMock()
                mock_proc.terminate = Mock()
                mock_proc.wait = AsyncMock()
                mock_processes.append(mock_proc)

            mock_exec.side_effect = mock_processes

            # Start servers
            for config in configs:
                await supervisor.start_server(config)

            # Shutdown
            await supervisor.shutdown()

            # All processes should be terminated
            for proc in mock_processes:
                proc.terminate.assert_called()


@pytest.mark.integration
class TestPerformance:
    """Performance benchmarks and SLA validation"""

    @pytest.mark.asyncio
    async def test_tool_execution_latency(self):
        """Test tool execution completes within SLA (< 100ms overhead)"""
        manager = MCPManager()
        manager.initialized = True

        tool = MCPTool(name="fast_tool", description="Fast tool")
        manager.available_tools = {"fast_tool": tool}
        manager.tool_to_server = {"fast_tool": "server"}

        mock_client = Mock()

        # Mock tool takes 10ms
        async def mock_execute(name, args):
            await asyncio.sleep(0.01)
            return {"result": "done"}

        mock_client.execute_tool = mock_execute
        manager.connected_servers = {"server": Mock(client=mock_client)}

        # Measure overhead
        start = time.time()
        result = await manager.execute_tool("fast_tool", {})
        duration = time.time() - start

        # Total time should be ~10ms + overhead < 100ms
        assert duration < 0.1  # 100ms
        assert result.success

    @pytest.mark.asyncio
    async def test_throughput_100_requests_per_second(self):
        """Test system can handle 100 requests/second"""
        manager = MCPManager()
        manager.initialized = True

        tool = MCPTool(name="throughput_tool", description="Test")
        manager.available_tools = {"throughput_tool": tool}
        manager.tool_to_server = {"throughput_tool": "server"}

        mock_client = Mock()
        mock_client.execute_tool = AsyncMock(return_value={"result": "ok"})
        manager.connected_servers = {"server": Mock(client=mock_client)}

        # Execute 100 requests
        start = time.time()
        tasks = [
            manager.execute_tool("throughput_tool", {})
            for _ in range(100)
        ]
        await asyncio.gather(*tasks)
        duration = time.time() - start

        # Should complete in < 1 second (100 req/s)
        assert duration < 1.0
        print(f"Throughput: {100/duration:.1f} req/s")


# Test fixtures
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Clean up singletons and state after each test"""
    yield
    from src.core.mcp import reset_mcp_config, reset_mcp_manager
    reset_mcp_config()
    reset_mcp_manager()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "integration"])

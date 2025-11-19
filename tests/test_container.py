"""
Test dependency injection container and thread safety.
"""

import pytest
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch

from v2.core.container import Container, get_container, reset_container


class TestContainer:
    """Test the dependency injection container."""

    def setup_method(self):
        """Reset container before each test."""
        reset_container()

    def teardown_method(self):
        """Cleanup after each test."""
        reset_container()

    def test_singleton_pattern(self):
        """Should return the same container instance."""
        container1 = get_container()
        container2 = get_container()
        assert container1 is container2

    def test_thread_safety(self):
        """Should be thread-safe when creating container."""
        containers = []

        def get_container_in_thread():
            containers.append(get_container())

        # Create multiple threads trying to get container simultaneously
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=get_container_in_thread)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All should be the same instance
        assert all(c is containers[0] for c in containers)

    def test_reset_container(self):
        """Should properly reset container."""
        container1 = get_container()
        reset_container()
        container2 = get_container()
        assert container1 is not container2

    @pytest.mark.asyncio
    async def test_container_disposal(self):
        """Should properly dispose of all resources."""
        container = get_container()

        # Mock the pool manager to track disposal
        pool_manager = container.get_connection_pool_manager()
        original_dispose = pool_manager.dispose
        dispose_called = False

        async def mock_dispose():
            nonlocal dispose_called
            dispose_called = True
            await original_dispose()

        pool_manager.dispose = mock_dispose

        await container.dispose()
        assert dispose_called

    def test_service_registration(self):
        """Should register and retrieve services correctly."""
        container = get_container()

        # Get various services
        agent_registry = container.get_agent_registry()
        tool_registry = container.get_tool_registry()
        security = container.get_security_middleware()

        assert agent_registry is not None
        assert tool_registry is not None
        assert security is not None

        # Should return same instances
        assert agent_registry is container.get_agent_registry()
        assert tool_registry is container.get_tool_registry()

    def test_lazy_initialization(self):
        """Should lazily initialize services."""
        container = get_container()

        # Services shouldn't exist until requested
        assert not hasattr(container, '_agent_registry')

        # Request service
        registry = container.get_agent_registry()

        # Now it should exist
        assert hasattr(container, '_agent_registry')

    @pytest.mark.asyncio
    async def test_concurrent_service_access(self):
        """Should handle concurrent access to services."""
        container = get_container()
        results = []

        async def get_service():
            registry = container.get_agent_registry()
            results.append(registry)

        # Create multiple concurrent tasks
        tasks = [get_service() for _ in range(10)]
        await asyncio.gather(*tasks)

        # All should get the same instance
        assert all(r is results[0] for r in results)
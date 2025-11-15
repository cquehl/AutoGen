"""
Yamazaki v2 - Dependency Injection Container

Manages service lifecycle and dependency injection.
Provides singleton and factory patterns for components.
"""

from typing import Optional, Dict, Any, Callable
from pathlib import Path

from ..config.models import AppSettings, load_settings_from_yaml


class Container:
    """
    IoC container for dependency injection.

    Manages service lifecycle and provides dependency resolution.
    """

    def __init__(self, settings: Optional[AppSettings] = None):
        """
        Initialize container.

        Args:
            settings: Application settings (loaded from env if not provided)
        """
        self._settings = settings
        self._singletons: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}

    @property
    def settings(self) -> AppSettings:
        """Get application settings (lazy load)"""
        if self._settings is None:
            from ..config import get_settings
            self._settings = get_settings()
        return self._settings

    def get_connection_pool(self):
        """
        Get database connection pool (singleton).

        Returns:
            Connection pool manager
        """
        if "connection_pool" not in self._singletons:
            from ..services.database import ConnectionPoolManager

            self._singletons["connection_pool"] = ConnectionPoolManager(
                config=self.settings.database
            )

        return self._singletons["connection_pool"]

    def get_security_middleware(self):
        """
        Get security middleware (singleton).

        Returns:
            SecurityMiddleware instance
        """
        if "security_middleware" not in self._singletons:
            from ..security.middleware import SecurityMiddleware

            self._singletons["security_middleware"] = SecurityMiddleware(
                config=self.settings.security
            )

        return self._singletons["security_middleware"]

    def get_tool_registry(self):
        """
        Get tool registry (singleton).

        Returns:
            ToolRegistry instance
        """
        if "tool_registry" not in self._singletons:
            from ..tools.registry import ToolRegistry

            registry = ToolRegistry(
                security_middleware=self.get_security_middleware(),
                connection_pool=self.get_connection_pool(),
            )

            # Auto-discover and register tools
            registry.discover_tools()

            self._singletons["tool_registry"] = registry

        return self._singletons["tool_registry"]

    def get_agent_registry(self):
        """
        Get agent registry (singleton).

        Returns:
            AgentRegistry instance
        """
        if "agent_registry" not in self._singletons:
            from ..agents.registry import AgentRegistry

            registry = AgentRegistry(
                settings=self.settings,
                tool_registry=self.get_tool_registry(),
            )

            # Auto-discover and register agents
            registry.discover_agents()

            self._singletons["agent_registry"] = registry

        return self._singletons["agent_registry"]

    def get_observability_manager(self):
        """
        Get observability manager (singleton).

        Returns:
            ObservabilityManager instance
        """
        if "observability" not in self._singletons:
            from ..observability.manager import ObservabilityManager

            self._singletons["observability"] = ObservabilityManager(
                config=self.settings.observability
            )

        return self._singletons["observability"]

    def get_database_service(self):
        """
        Get database service (factory).

        Returns:
            DatabaseService instance
        """
        from ..services.database import DatabaseService

        return DatabaseService(
            pool=self.get_connection_pool(),
            security=self.get_security_middleware(),
        )

    def get_file_service(self):
        """
        Get file service (factory).

        Returns:
            FileService instance
        """
        from ..services.file_service import FileService

        return FileService(
            security=self.get_security_middleware(),
        )

    def get_agent_factory(self):
        """
        Get agent factory (singleton).

        Returns:
            AgentFactory instance
        """
        if "agent_factory" not in self._singletons:
            from ..agents.factory import AgentFactory

            self._singletons["agent_factory"] = AgentFactory(
                settings=self.settings,
                agent_registry=self.get_agent_registry(),
                tool_registry=self.get_tool_registry(),
            )

        return self._singletons["agent_factory"]

    def get_message_bus(self):
        """
        Get message bus (singleton).

        Returns:
            MessageBus instance
        """
        if "message_bus" not in self._singletons:
            from ..messaging.message_bus import MessageBus
            from ..messaging.handlers import LoggingHandler, MetricsHandler

            bus = MessageBus(max_history=1000)

            # Add default handlers
            logging_handler = LoggingHandler(log_level="INFO")
            metrics_handler = MetricsHandler()

            bus.subscribe_all(logging_handler.handle)
            bus.subscribe_all(metrics_handler.handle)

            self._singletons["message_bus"] = bus
            self._singletons["metrics_handler"] = metrics_handler

        return self._singletons["message_bus"]

    def get_state_manager(self):
        """
        Get state manager (singleton).

        Returns:
            StateManager instance
        """
        if "state_manager" not in self._singletons:
            from ..memory.state_manager import StateManager

            self._singletons["state_manager"] = StateManager(
                storage_path=".autogen_state",
                enable_versioning=True,
                max_versions=10,
            )

        return self._singletons["state_manager"]

    async def dispose(self):
        """
        Dispose of all resources and cleanup.

        Call this on application shutdown.
        """
        # Shutdown message bus
        if "message_bus" in self._singletons:
            await self._singletons["message_bus"].shutdown()

        # Close connection pool
        if "connection_pool" in self._singletons:
            await self._singletons["connection_pool"].dispose()

        # Shutdown observability
        if "observability" in self._singletons:
            await self._singletons["observability"].shutdown()

        # Clear singletons
        self._singletons.clear()

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "Container":
        """
        Create container from YAML configuration.

        Args:
            yaml_path: Path to settings.yaml

        Returns:
            Container with loaded settings
        """
        settings = load_settings_from_yaml(yaml_path)
        return cls(settings=settings)


# Global container instance
_container: Optional[Container] = None


def get_container() -> Container:
    """
    Get global container instance.

    Returns:
        Container singleton
    """
    global _container
    if _container is None:
        _container = Container()
    return _container


def reset_container():
    """Reset global container (useful for testing)"""
    global _container
    _container = None

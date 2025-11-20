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

            # Register all tools
            self._register_all_tools(registry)

            # Register Alfred's tools (requires services, so done after registry creation)
            self._register_alfred_tools(registry)

            self._singletons["tool_registry"] = registry

        return self._singletons["tool_registry"]

    def _register_all_tools(self, registry):
        """
        Register all standard tools.

        Args:
            registry: ToolRegistry to register tools in
        """
        from ..tools.database import DatabaseQueryTool
        from ..tools.file import FileReadTool, WriteFileTool, AppendFileTool
        from ..tools.weather import WeatherForecastTool
        from ..tools.web import WebSearchTool, NewsSearchTool

        # Database tools
        registry.register(
            name=DatabaseQueryTool.NAME,
            tool_class=DatabaseQueryTool,
        )

        # File tools
        registry.register(
            name=FileReadTool.NAME,
            tool_class=FileReadTool,
        )

        registry.register(
            name=WriteFileTool.NAME,
            tool_class=WriteFileTool,
        )

        registry.register(
            name=AppendFileTool.NAME,
            tool_class=AppendFileTool,
        )

        # Weather tools
        registry.register(
            name=WeatherForecastTool.NAME,
            tool_class=WeatherForecastTool,
        )

        # Web tools
        registry.register(
            name=WebSearchTool.NAME,
            tool_class=WebSearchTool,
        )

        registry.register(
            name=NewsSearchTool.NAME,
            tool_class=NewsSearchTool,
        )

    def _register_alfred_tools(self, registry):
        """
        Register Alfred's specialized tools with service dependencies.

        Args:
            registry: ToolRegistry to register tools in
        """
        from ..tools.alfred import (
            ListCapabilitiesTool,
            ShowHistoryTool,
            DelegateToTeamTool,
        )

        # Register tools with Alfred category
        # Note: These tools need special handling in get_tool due to service dependencies
        registry.register(
            name=ListCapabilitiesTool.NAME,
            tool_class=ListCapabilitiesTool,
        )

        registry.register(
            name=ShowHistoryTool.NAME,
            tool_class=ShowHistoryTool,
        )

        registry.register(
            name=DelegateToTeamTool.NAME,
            tool_class=DelegateToTeamTool,
        )

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

            # Initialize Alfred's services and inject into tool registry
            self._initialize_alfred_services()

        return self._singletons["agent_factory"]

    def _initialize_alfred_services(self):
        """
        Initialize services required for Alfred and inject into tool registry.

        This must be called after agent_factory is created to avoid circular dependencies.
        """
        # Get or create the services
        capability_service = self.get_capability_service()
        history_service = self.get_history_service()
        agent_factory = self._singletons["agent_factory"]

        # Inject services into tool registry for Alfred's tools
        tool_registry = self.get_tool_registry()
        tool_registry.set_alfred_services(
            capability_service=capability_service,
            history_service=history_service,
            agent_factory=agent_factory,
        )

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

    def get_background_job_manager(self):
        """
        Get background job manager (singleton).

        Returns:
            BackgroundJobManager instance
        """
        if "background_job_manager" not in self._singletons:
            from ..tools.shell.background_job_manager import BackgroundJobManager

            self._singletons["background_job_manager"] = BackgroundJobManager(
                max_jobs=self.settings.shell_config.max_background_jobs,
                max_output_lines=self.settings.shell_config.max_output_lines,
            )

        return self._singletons["background_job_manager"]

    def get_command_executor(self):
        """
        Get command executor (singleton).

        Returns the BashCommandExecutor which wraps BashTool.
        This is available after tool registry is initialized.

        Returns:
            CommandExecutor instance
        """
        if "command_executor" not in self._singletons:
            from ..core.command_executor import BashCommandExecutor

            # Get the bash tool from tool registry
            tool_registry = self.get_tool_registry()
            bash_tool = tool_registry.create_tool("shell.bash")

            self._singletons["command_executor"] = BashCommandExecutor(bash_tool)

        return self._singletons["command_executor"]

    def get_vision_service(self):
        """
        Get vision service (singleton).

        Provides vision model capabilities for image analysis.

        Returns:
            VisionService instance
        """
        if "vision_service" not in self._singletons:
            from ..services.vision_service import VisionService

            self._singletons["vision_service"] = VisionService(
                config=self.settings.multimodal,
                llm_settings=self.settings,
                security_middleware=self.get_security_middleware(),
            )

        return self._singletons["vision_service"]

    def get_capability_service(self):
        """
        Get capability service (singleton).

        Provides auto-discovery and caching of system capabilities for Alfred.

        Returns:
            CapabilityService instance
        """
        if "capability_service" not in self._singletons:
            from ..services.capability_service import CapabilityService

            self._singletons["capability_service"] = CapabilityService(
                agent_registry=self.get_agent_registry(),
                tool_registry=self.get_tool_registry(),
                settings=self.settings,
            )

        return self._singletons["capability_service"]

    def get_history_service(self):
        """
        Get history service (singleton).

        Provides unified access to conversation history, message bus events,
        and tool execution logs for Alfred.

        Returns:
            HistoryService instance
        """
        if "history_service" not in self._singletons:
            from ..services.history_service import HistoryService

            self._singletons["history_service"] = HistoryService(
                message_bus=self.get_message_bus(),
                observability_manager=self.get_observability_manager(),
            )

        return self._singletons["history_service"]

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

        # Cleanup background jobs
        if "background_job_manager" in self._singletons:
            # Kill all running jobs before shutdown
            job_manager = self._singletons["background_job_manager"]
            for job_id in list(job_manager.jobs.keys()):
                await job_manager.kill_job(job_id)

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


# Global container instance with thread safety
import threading

_container: Optional[Container] = None
_container_lock = threading.Lock()


def get_container() -> Container:
    """
    Get global container instance with thread-safe initialization.

    Returns:
        Container singleton

    FIXED: Double-checked locking for thread safety
    """
    global _container
    if _container is None:
        with _container_lock:
            # Double-check after acquiring lock
            if _container is None:
                _container = Container()
    return _container


def reset_container():
    """
    Reset global container (useful for testing).

    FIXED: Thread-safe reset
    """
    global _container
    with _container_lock:
        _container = None

"""
MCP Server Supervisor

This module manages the lifecycle of MCP servers, including starting, stopping,
monitoring, and automatic restart on failure.
"""

import asyncio
import os
import signal
import subprocess
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import logging
import psutil

from .config import MCPServerConfig, RestartPolicy
from .types import MCPServer, HealthStatus
from ..telemetry import LoggerMixin


class ServerStatus(str, Enum):
    """MCP server status states"""
    CONFIGURED = "configured"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    RESTARTING = "restarting"


class MCPServerProcess:
    """Wrapper for MCP server subprocess"""

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.process: Optional[asyncio.subprocess.Process] = None
        self.status = ServerStatus.CONFIGURED
        self.started_at: Optional[datetime] = None
        self.stopped_at: Optional[datetime] = None
        self.restart_count = 0
        self.error_message: Optional[str] = None
        self.logger = logging.getLogger(f"MCPServer[{config.name}]")

    async def start(self) -> None:
        """Start the MCP server process"""
        if self.status == ServerStatus.RUNNING:
            self.logger.warning("Server already running")
            return

        self.status = ServerStatus.STARTING
        self.error_message = None

        try:
            # Prepare environment
            env = os.environ.copy()
            env.update(self.config.env)

            # Parse command
            if self.config.command:
                cmd_parts = self.config.command.split() + self.config.args
            else:
                raise ValueError("No command specified for server")

            # Set working directory
            cwd = self.config.working_directory or os.getcwd()

            # Start subprocess
            self.process = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=cwd
            )

            self.started_at = datetime.utcnow()
            self.status = ServerStatus.RUNNING

            # Start monitoring tasks
            asyncio.create_task(self._monitor_stderr())

            self.logger.info(f"Started MCP server: PID {self.process.pid}")

        except Exception as e:
            self.status = ServerStatus.ERROR
            self.error_message = str(e)
            self.logger.error(f"Failed to start server: {e}")
            raise

    async def stop(self, timeout: int = 10) -> None:
        """Stop the MCP server process gracefully"""
        if self.process is None or self.status != ServerStatus.RUNNING:
            self.logger.warning("Server not running")
            return

        self.status = ServerStatus.STOPPING
        self.logger.info("Stopping MCP server...")

        try:
            # Send termination signal
            self.process.terminate()

            # Wait for graceful shutdown
            try:
                await asyncio.wait_for(self.process.wait(), timeout=timeout)
                self.logger.info("Server stopped gracefully")
            except asyncio.TimeoutError:
                # Force kill if graceful shutdown fails
                self.logger.warning("Graceful shutdown timeout, forcing kill")
                self.process.kill()
                await self.process.wait()

            self.stopped_at = datetime.utcnow()
            self.status = ServerStatus.STOPPED

        except Exception as e:
            self.logger.error(f"Error stopping server: {e}")
            self.status = ServerStatus.ERROR
            self.error_message = str(e)

    async def restart(self) -> None:
        """Restart the MCP server"""
        self.status = ServerStatus.RESTARTING
        self.restart_count += 1
        self.logger.info(f"Restarting server (attempt {self.restart_count})")

        await self.stop()
        await asyncio.sleep(2)  # Brief pause before restart
        await self.start()

    async def _monitor_stderr(self) -> None:
        """Monitor stderr output for errors"""
        if not self.process or not self.process.stderr:
            return

        try:
            async for line in self.process.stderr:
                error_line = line.decode().strip()
                if error_line:
                    self.logger.error(f"Server error: {error_line}")
                    # Check for critical errors that should trigger restart
                    if any(keyword in error_line.lower() for keyword in ["fatal", "panic", "crashed"]):
                        self.error_message = error_line
                        if self.config.restart_policy != RestartPolicy.NEVER:
                            asyncio.create_task(self._handle_crash())
        except Exception as e:
            self.logger.error(f"Error monitoring stderr: {e}")

    async def _handle_crash(self) -> None:
        """Handle server crash based on restart policy"""
        if self.restart_count >= self.config.max_retries:
            self.logger.error(f"Maximum restart attempts ({self.config.max_retries}) reached")
            self.status = ServerStatus.ERROR
            return

        if self.config.restart_policy == RestartPolicy.ALWAYS:
            await self.restart()
        elif self.config.restart_policy == RestartPolicy.ON_FAILURE:
            if self.status == ServerStatus.ERROR:
                await self.restart()

    def get_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage of the server process"""
        if not self.process or not self.process.pid:
            return {}

        try:
            proc = psutil.Process(self.process.pid)
            return {
                "cpu_percent": proc.cpu_percent(),
                "memory_mb": proc.memory_info().rss / 1024 / 1024,
                "num_threads": proc.num_threads(),
                "open_files": len(proc.open_files()) if hasattr(proc, 'open_files') else 0
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {}

    @property
    def is_running(self) -> bool:
        """Check if server is running"""
        return (
            self.process is not None
            and self.process.returncode is None
            and self.status == ServerStatus.RUNNING
        )

    @property
    def uptime(self) -> Optional[timedelta]:
        """Get server uptime"""
        if self.started_at and self.is_running:
            return datetime.utcnow() - self.started_at
        return None


class MCPServerSupervisor(LoggerMixin):
    """
    Manages lifecycle of multiple MCP servers.

    Provides centralized control for starting, stopping, monitoring,
    and automatically restarting MCP servers.
    """

    def __init__(self):
        """Initialize the server supervisor"""
        super().__init__()
        self.servers: Dict[str, MCPServerProcess] = {}
        self.health_check_tasks: Dict[str, asyncio.Task] = {}
        self.monitoring_enabled = True
        self._monitor_task: Optional[asyncio.Task] = None

    async def start_server(self, config: MCPServerConfig) -> MCPServer:
        """
        Start an MCP server process.

        Args:
            config: Server configuration

        Returns:
            MCP server information
        """
        server_id = config.name

        # Check if server already exists
        if server_id in self.servers:
            server_proc = self.servers[server_id]
            if server_proc.is_running:
                self.logger.info(f"Server {server_id} already running")
                return self._create_server_info(server_id)

        # Create new server process
        server_proc = MCPServerProcess(config)
        self.servers[server_id] = server_proc

        # Start the server
        await server_proc.start()

        # Start health monitoring
        if self.monitoring_enabled:
            await self._start_health_monitoring(server_id)

        return self._create_server_info(server_id)

    async def stop_server(self, server_id: str, timeout: int = 10) -> None:
        """
        Stop an MCP server.

        Args:
            server_id: Server identifier
            timeout: Graceful shutdown timeout in seconds
        """
        if server_id not in self.servers:
            self.logger.warning(f"Server {server_id} not found")
            return

        # Stop health monitoring
        await self._stop_health_monitoring(server_id)

        # Stop the server
        server_proc = self.servers[server_id]
        await server_proc.stop(timeout)

        self.logger.info(f"Stopped server: {server_id}")

    async def restart_server(self, server_id: str) -> None:
        """
        Restart an MCP server.

        Args:
            server_id: Server identifier
        """
        if server_id not in self.servers:
            self.logger.warning(f"Server {server_id} not found")
            return

        server_proc = self.servers[server_id]
        await server_proc.restart()

    async def health_check(self, server_id: str) -> HealthStatus:
        """
        Check health of a specific server.

        Args:
            server_id: Server identifier

        Returns:
            Health status of the server
        """
        if server_id not in self.servers:
            return HealthStatus(
                healthy=False,
                status="not_found",
                message=f"Server {server_id} not found"
            )

        server_proc = self.servers[server_id]

        if not server_proc.is_running:
            return HealthStatus(
                healthy=False,
                status="stopped",
                message="Server is not running",
                error_count=server_proc.restart_count
            )

        # Check resource usage
        resources = server_proc.get_resource_usage()

        # Check if exceeding limits
        config = server_proc.config
        issues = []

        if config.max_memory_mb and resources.get("memory_mb", 0) > config.max_memory_mb:
            issues.append(f"Memory usage ({resources['memory_mb']:.1f}MB) exceeds limit ({config.max_memory_mb}MB)")

        if config.max_cpu_percent and resources.get("cpu_percent", 0) > config.max_cpu_percent:
            issues.append(f"CPU usage ({resources['cpu_percent']:.1f}%) exceeds limit ({config.max_cpu_percent}%)")

        if issues:
            return HealthStatus(
                healthy=False,
                status="degraded",
                message="; ".join(issues),
                error_count=server_proc.restart_count
            )

        # Server is healthy
        return HealthStatus(
            healthy=True,
            status="healthy",
            message=f"Uptime: {server_proc.uptime}",
            error_count=server_proc.restart_count
        )

    async def _start_health_monitoring(self, server_id: str) -> None:
        """Start health monitoring for a server"""
        if server_id in self.health_check_tasks:
            return

        async def monitor():
            while server_id in self.servers:
                try:
                    await asyncio.sleep(60)  # Check every minute
                    status = await self.health_check(server_id)
                    if not status.healthy and status.status != "stopped":
                        self.logger.warning(f"Server {server_id} unhealthy: {status.message}")
                        # Consider restart based on policy
                        server_proc = self.servers[server_id]
                        if server_proc.config.restart_policy == RestartPolicy.ON_FAILURE:
                            await server_proc.restart()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Health check error for {server_id}: {e}")

        task = asyncio.create_task(monitor())
        self.health_check_tasks[server_id] = task

    async def _stop_health_monitoring(self, server_id: str) -> None:
        """Stop health monitoring for a server"""
        if server_id in self.health_check_tasks:
            task = self.health_check_tasks.pop(server_id)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def monitor_servers(self) -> None:
        """Monitor all running servers"""
        if self._monitor_task and not self._monitor_task.done():
            return

        async def monitor_loop():
            while self.monitoring_enabled:
                try:
                    await asyncio.sleep(30)  # Check every 30 seconds
                    for server_id, server_proc in list(self.servers.items()):
                        if server_proc.is_running:
                            resources = server_proc.get_resource_usage()
                            self.logger.debug(
                                f"Server {server_id} - CPU: {resources.get('cpu_percent', 0):.1f}%, "
                                f"Memory: {resources.get('memory_mb', 0):.1f}MB"
                            )
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Monitoring error: {e}")

        self._monitor_task = asyncio.create_task(monitor_loop())

    def _create_server_info(self, server_id: str) -> MCPServer:
        """Create MCPServer info object"""
        server_proc = self.servers[server_id]
        return MCPServer(
            id=server_id,
            type=server_proc.config.type,
            transport=server_proc.config.transport,
            status=server_proc.status,
            config=server_proc.config,
            process_id=server_proc.process.pid if server_proc.process else None,
            started_at=server_proc.started_at,
            error_message=server_proc.error_message
        )

    def get_server_status(self, server_id: str) -> Optional[ServerStatus]:
        """Get status of a specific server"""
        if server_id in self.servers:
            return self.servers[server_id].status
        return None

    def get_all_servers(self) -> List[MCPServer]:
        """Get information about all servers"""
        return [self._create_server_info(sid) for sid in self.servers.keys()]

    def get_running_servers(self) -> List[str]:
        """Get list of running server IDs"""
        return [
            sid for sid, server in self.servers.items()
            if server.is_running
        ]

    async def stop_all_servers(self) -> None:
        """Stop all running servers"""
        self.logger.info("Stopping all MCP servers...")
        tasks = []
        for server_id in list(self.servers.keys()):
            tasks.append(self.stop_server(server_id))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def shutdown(self) -> None:
        """Shutdown the supervisor and all servers"""
        self.monitoring_enabled = False

        # Cancel monitoring task
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        # Stop all health monitoring
        for server_id in list(self.health_check_tasks.keys()):
            await self._stop_health_monitoring(server_id)

        # Stop all servers
        await self.stop_all_servers()

        self.logger.info("MCP Server Supervisor shutdown complete")
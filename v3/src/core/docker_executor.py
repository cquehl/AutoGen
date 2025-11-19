"""
Suntory v3 - Docker Code Executor
Secure code execution in sandboxed Docker containers
"""

import asyncio
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple

import docker
from docker.errors import DockerException, ImageNotFound
from docker.models.containers import Container

from .config import get_settings
from .errors import ResourceError, SuntoryError
from .telemetry import get_logger

logger = get_logger(__name__)


class DockerExecutor:
    """
    Execute code safely in Docker containers.

    Features:
    - Isolated execution environment
    - Resource limits (CPU, memory)
    - Timeout protection
    - Network isolation options
    - Result capture
    """

    def __init__(self):
        self.settings = get_settings()
        self.client: Optional[docker.DockerClient] = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Docker client - non-fatal if Docker unavailable"""
        if not self.settings.docker_enabled:
            logger.warning("Docker execution is disabled in configuration")
            return

        try:
            self.client = docker.from_env()
            # Test connection
            self.client.ping()
            logger.info("Docker client initialized successfully")
        except DockerException as e:
            # Don't raise - log warning and allow graceful degradation
            logger.warning(
                f"Docker not available: {e}. "
                "Code execution features will be disabled. "
                "Start Docker daemon to enable."
            )
            self.client = None

    def _ensure_image(self, image: str = "python:3.11-slim"):
        """Ensure Docker image is available"""
        if not self.client:
            raise SuntoryError("Docker client not initialized")

        try:
            self.client.images.get(image)
            logger.debug(f"Image {image} already available")
        except ImageNotFound:
            logger.info(f"Pulling image {image}...")
            try:
                self.client.images.pull(image)
                logger.info(f"Image {image} pulled successfully")
            except DockerException as e:
                raise SuntoryError(
                    message=f"Failed to pull Docker image {image}",
                    recovery_suggestions=[
                        "Check internet connection",
                        "Verify Docker Hub is accessible",
                        "Try pulling the image manually: `docker pull {image}`"
                    ],
                    original_error=e
                )

    def _execute_in_container(
        self,
        command: list,
        timeout: int,
        memory_limit: str = "512m",
        cpu_limit: float = 1.0,
        network_disabled: bool = True,
        working_dir: str = "/workspace"
    ) -> Tuple[str, str, int]:
        """
        Core execution logic for Docker containers.

        ARCHITECTURE: Centralized execution to eliminate code duplication.

        Args:
            command: Command to execute in container
            timeout: Timeout in seconds
            memory_limit: Memory limit (e.g., "512m", "1g")
            cpu_limit: CPU limit as fraction (e.g., 1.0 = 1 CPU)
            network_disabled: Disable network access
            working_dir: Working directory in container

        Returns:
            Tuple of (stdout, stderr, exit_code)

        Raises:
            SuntoryError: If execution fails
        """
        if not self.client:
            raise SuntoryError(
                message="Docker execution is disabled",
                recovery_suggestions=[
                    "Enable Docker in configuration",
                    "Start Docker daemon"
                ]
            )

        self._ensure_image()

        logger.info(
            "Executing command in Docker",
            command=command[:100] if len(str(command)) > 100 else command,
            timeout=timeout,
            memory_limit=memory_limit
        )

        container: Optional[Container] = None
        try:
            # Run container
            container = self.client.containers.run(
                image="python:3.11-slim",
                command=command,
                volumes={
                    str(self.settings.get_workspace_path()): {
                        'bind': '/workspace',
                        'mode': 'rw'
                    }
                },
                working_dir=working_dir,
                mem_limit=memory_limit,
                nano_cpus=int(cpu_limit * 1e9),  # Convert to nano CPUs
                network_disabled=network_disabled,
                detach=True,
                remove=False,  # Don't auto-remove, we need logs
                security_opt=["no-new-privileges:true"],
                cap_drop=["ALL"],  # Drop all capabilities
                read_only=False,  # Workspace needs to be writable
            )

            # Wait for completion with timeout
            result = container.wait(timeout=timeout)
            exit_code = result['StatusCode']

            # Get logs
            stdout = container.logs(stdout=True, stderr=False).decode('utf-8')
            stderr = container.logs(stdout=False, stderr=True).decode('utf-8')

            logger.info(
                "Container execution completed",
                exit_code=exit_code,
                stdout_length=len(stdout),
                stderr_length=len(stderr)
            )

            return stdout, stderr, exit_code

        except Exception as e:
            # Kill container on timeout or error
            if container:
                try:
                    container.kill()
                except Exception as kill_error:
                    logger.warning(f"Failed to kill container: {kill_error}")

            if "timeout" in str(e).lower():
                raise ResourceError("execution time", f"{timeout}s")
            else:
                raise SuntoryError(
                    message=f"Container execution failed: {str(e)}",
                    original_error=e
                )

        finally:
            # Clean up container
            if container:
                try:
                    container.remove(force=True)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to remove container: {cleanup_error}")

    async def execute_python(
        self,
        code: str,
        timeout: int = 30,
        memory_limit: str = "512m",
        cpu_limit: float = 1.0,
        network_disabled: bool = True
    ) -> Tuple[str, str, int]:
        """
        Execute Python code in Docker container.

        Args:
            code: Python code to execute
            timeout: Timeout in seconds
            memory_limit: Memory limit (e.g., "512m", "1g")
            cpu_limit: CPU limit as fraction (e.g., 1.0 = 1 CPU)
            network_disabled: Disable network access

        Returns:
            Tuple of (stdout, stderr, exit_code)

        Raises:
            SuntoryError: If execution fails
        """
        # Create temporary file for code
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False,
            dir=self.settings.get_workspace_path()
        ) as f:
            f.write(code)
            code_file = Path(f.name)

        try:
            # Execute in thread pool to avoid blocking event loop
            return await asyncio.to_thread(
                self._execute_in_container,
                command=["python", f"/workspace/{code_file.name}"],
                timeout=timeout,
                memory_limit=memory_limit,
                cpu_limit=cpu_limit,
                network_disabled=network_disabled
            )
        finally:
            # Clean up code file
            try:
                code_file.unlink()
            except Exception as cleanup_error:
                logger.warning(f"Failed to unlink code file: {cleanup_error}")

    async def execute_bash(
        self,
        command: str,
        timeout: int = 30,
        working_dir: str = "/workspace"
    ) -> Tuple[str, str, int]:
        """
        Execute bash command in Docker container.

        Args:
            command: Bash command to execute
            timeout: Timeout in seconds
            working_dir: Working directory

        Returns:
            Tuple of (stdout, stderr, exit_code)
        """
        # Execute in thread pool to avoid blocking event loop
        return await asyncio.to_thread(
            self._execute_in_container,
            command=["bash", "-c", command],
            timeout=timeout,
            working_dir=working_dir
        )

    def is_available(self) -> bool:
        """Check if Docker is available"""
        return self.client is not None


# Singleton instance
_docker_executor: Optional[DockerExecutor] = None


def get_docker_executor() -> DockerExecutor:
    """Get or create Docker executor singleton"""
    global _docker_executor
    if _docker_executor is None:
        _docker_executor = DockerExecutor()
    return _docker_executor


def reset_docker_executor():
    """Reset Docker executor (useful for testing)"""
    global _docker_executor
    if _docker_executor and _docker_executor.client:
        _docker_executor.client.close()
    _docker_executor = None

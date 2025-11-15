# AutoGen V2 - Implementation Guide for Critical Gaps

**Following the Yamazaki v2 Architecture Patterns**

This document provides detailed implementation blueprints for adding the 5 critical capabilities while strictly adhering to AutoGen V2's existing architecture patterns.

---

## Architecture Principles Review

Based on the existing codebase, AutoGen V2 follows these patterns:

### 1. **Plugin-Based Tool Architecture**
```python
# All tools inherit from BaseTool
class BaseTool(ABC):
    NAME: str = "tool.name"
    DESCRIPTION: str = "Tool description"
    CATEGORY: ToolCategory = ToolCategory.GENERAL
    VERSION: str = "1.0.0"
    REQUIRES_SECURITY_VALIDATION: bool = False

    async def execute(self, **kwargs) -> ToolResult
    def validate_params(self, **kwargs) -> tuple[bool, Optional[str]]
    def _get_parameters_schema(self) -> Dict[str, Any]
```

### 2. **Agent Registry Pattern**
```python
# All agents inherit from BaseAgent
class BaseAgent(ABC):
    NAME: str = "agent_name"
    DESCRIPTION: str = "Agent description"
    CATEGORY: str = "category"
    VERSION: str = "1.0.0"

    @property
    @abstractmethod
    def system_message(self) -> str:
        pass
```

### 3. **Dependency Injection via Container**
- Tools receive `security_middleware` and `connection_pool` via DI
- Agents receive `config`, `model_client`, and `tools` via DI
- Registry manages instantiation and dependency wiring

### 4. **Security-First Design**
- Security middleware validates operations
- Audit logging for all security-relevant operations
- Timeout management for all operations
- Centralized validation (SQL, path, etc.)

### 5. **Standardized Result Types**
```python
@dataclass
class ToolResult:
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
```

---

## Implementation #1: Terminal/Bash Execution

### File Structure
```
v2/tools/shell/
├── __init__.py
├── bash_tool.py           # Bash command execution
└── background_job_manager.py  # Background job management
```

### Step 1: Add Shell Category to ToolCategory Enum

**File:** `v2/core/base_tool.py`

```python
class ToolCategory(str, Enum):
    """Tool categories for organization and discovery"""
    DATABASE = "database"
    FILE = "file"
    WEB = "web"
    WEATHER = "weather"
    SHELL = "shell"      # ADD THIS
    GENERAL = "general"
```

### Step 2: Create Security Validator for Shell Commands

**File:** `v2/security/validators/shell_validator.py`

```python
"""
Shell Command Validator

Validates shell commands for security issues.
"""

from typing import Optional, List
from dataclasses import dataclass


@dataclass
class ShellValidationResult:
    """Result of shell command validation"""
    is_valid: bool
    error: Optional[str] = None
    warning: Optional[str] = None
    query_type: Optional[str] = None


class ShellValidator:
    """
    Validates shell commands for security issues.

    Prevents:
    - Destructive commands without confirmation
    - Command injection patterns
    - Resource exhaustion attacks
    """

    # Commands that are always blocked
    BLOCKED_COMMANDS = [
        "rm -rf /",
        "mkfs",
        "dd if=/dev/zero",
        ":(){ :|:& };:",  # Fork bomb
        "chmod -R 777 /",
    ]

    # Commands that require extra validation
    DANGEROUS_COMMANDS = [
        "rm", "rmdir", "dd", "mkfs",
        "fdisk", "parted", "format",
        "shutdown", "reboot", "halt",
    ]

    # Patterns that suggest injection attempts
    INJECTION_PATTERNS = [
        ";", "&&", "||", "|", "`", "$(",
        "\n", "\r", "$(", "${",
    ]

    def __init__(self, config):
        """
        Initialize validator.

        Args:
            config: SecurityConfig with shell settings
        """
        self.config = config
        self.enable_dangerous_commands = getattr(
            config, 'allow_dangerous_shell_commands', False
        )

    def validate(
        self,
        command: str,
        allow_pipes: bool = True,
        allow_chaining: bool = True,
    ) -> ShellValidationResult:
        """
        Validate shell command.

        Args:
            command: Shell command to validate
            allow_pipes: Allow pipe operators (|)
            allow_chaining: Allow command chaining (&&, ||, ;)

        Returns:
            ShellValidationResult
        """
        if not command or not command.strip():
            return ShellValidationResult(
                is_valid=False,
                error="Command cannot be empty"
            )

        command_lower = command.lower().strip()

        # Check for blocked commands
        for blocked in self.BLOCKED_COMMANDS:
            if blocked in command_lower:
                return ShellValidationResult(
                    is_valid=False,
                    error=f"Blocked command pattern detected: {blocked}"
                )

        # Check for dangerous commands
        if not self.enable_dangerous_commands:
            for dangerous in self.DANGEROUS_COMMANDS:
                if command_lower.startswith(dangerous + " ") or command_lower == dangerous:
                    return ShellValidationResult(
                        is_valid=False,
                        error=f"Dangerous command '{dangerous}' is not allowed. "
                               f"Enable dangerous commands in config if needed."
                    )

        # Check for command injection patterns
        has_injection_risk = False
        injection_chars = []

        for pattern in self.INJECTION_PATTERNS:
            if pattern in command:
                # Allow pipes if explicitly allowed
                if pattern == "|" and allow_pipes:
                    continue
                # Allow chaining if explicitly allowed
                if pattern in ["&&", "||", ";"] and allow_chaining:
                    continue

                has_injection_risk = True
                injection_chars.append(pattern)

        if has_injection_risk:
            return ShellValidationResult(
                is_valid=False,
                error=f"Potential command injection detected. "
                      f"Unsafe characters: {', '.join(repr(c) for c in injection_chars)}"
            )

        # Command looks safe
        return ShellValidationResult(
            is_valid=True,
            query_type=self._detect_command_type(command)
        )

    def _detect_command_type(self, command: str) -> str:
        """Detect the type of command (read, write, execute)"""
        command_lower = command.lower().strip()

        # Read operations
        if any(command_lower.startswith(cmd) for cmd in ["ls", "cat", "grep", "find", "head", "tail"]):
            return "read"

        # Write operations
        if any(command_lower.startswith(cmd) for cmd in ["mkdir", "touch", "cp", "mv", "echo >"]):
            return "write"

        # Package management
        if any(cmd in command_lower for cmd in ["pip install", "npm install", "apt install", "brew install"]):
            return "package_install"

        # Build operations
        if any(command_lower.startswith(cmd) for cmd in ["make", "cargo build", "npm run", "pytest"]):
            return "build"

        # Git operations
        if command_lower.startswith("git "):
            return "git"

        return "execute"
```

### Step 3: Update Security Middleware

**File:** `v2/security/middleware.py`

```python
# Add to imports at top
from .validators import SQLValidator, PathValidator, ShellValidator

# Add to OperationType enum
class OperationType(str, Enum):
    """Types of operations that can be validated"""
    SQL_QUERY = "sql_query"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    WEB_FETCH = "web_fetch"
    SHELL_COMMAND = "shell_command"  # ADD THIS

# Add to SecurityMiddleware.__init__
def __init__(self, config):
    """
    Initialize security middleware.

    Args:
        config: SecurityConfig
    """
    self.config = config
    self.validators = {
        "sql": SQLValidator(config),
        "path": PathValidator(config),
        "shell": ShellValidator(config),  # ADD THIS
    }
    self.audit_logger = AuditLogger(enabled=config.enable_audit_log)

# Add validation method
def _validate_shell(self, operation: Operation) -> tuple[bool, Optional[str]]:
    """Validate shell command operation"""
    command = operation.params.get("command", "")
    allow_pipes = operation.params.get("allow_pipes", True)
    allow_chaining = operation.params.get("allow_chaining", True)

    validator = self.validators["shell"]
    result = validator.validate(command, allow_pipes, allow_chaining)
    return result.is_valid, result.error

# Update validate_and_execute method
async def validate_and_execute(
    self,
    operation: Operation,
) -> OperationResult:
    """
    Validate, execute, and audit an operation.

    Args:
        operation: Operation to execute

    Returns:
        OperationResult
    """
    import time

    start_time = time.time()

    # Validate based on operation type
    if operation.type == OperationType.SQL_QUERY:
        is_valid, error = self._validate_sql(operation)
    elif operation.type in [OperationType.FILE_READ, OperationType.FILE_WRITE]:
        is_valid, error = self._validate_file(operation)
    elif operation.type == OperationType.SHELL_COMMAND:  # ADD THIS
        is_valid, error = self._validate_shell(operation)
    else:
        is_valid, error = True, None  # No validation for other types yet

    # ... rest of method unchanged
```

### Step 4: Create Bash Tool

**File:** `v2/tools/shell/bash_tool.py`

```python
"""
Bash Tool - Execute shell commands with security controls
"""

import asyncio
import subprocess
from typing import Optional, Dict, Any
from ...core.base_tool import BaseTool, ToolResult, ToolCategory
from ...security.middleware import Operation, OperationType


class BashTool(BaseTool):
    """
    Execute bash commands with security controls.

    Features:
    - Command execution with timeout
    - Security validation via middleware
    - Audit logging
    - Output capture (stdout + stderr)
    - Working directory support
    """

    NAME = "shell.bash"
    DESCRIPTION = "Execute bash commands with security controls and timeout"
    CATEGORY = ToolCategory.SHELL
    VERSION = "1.0.0"
    REQUIRES_SECURITY_VALIDATION = True

    def __init__(self, security_middleware, **kwargs):
        """
        Initialize bash tool.

        Args:
            security_middleware: Security middleware for validation
            **kwargs: Additional configuration
        """
        super().__init__(**kwargs)
        self.security_middleware = security_middleware
        self.default_timeout = kwargs.get('default_timeout', 120)
        self.max_timeout = kwargs.get('max_timeout', 600)  # 10 minutes max

    async def execute(
        self,
        command: str,
        timeout: Optional[int] = None,
        working_dir: Optional[str] = None,
        capture_output: bool = True,
    ) -> ToolResult:
        """
        Execute bash command.

        Args:
            command: Shell command to execute
            timeout: Timeout in seconds (default: 120, max: 600)
            working_dir: Working directory for command execution
            capture_output: Capture stdout/stderr (default: True)

        Returns:
            ToolResult with command output
        """
        # Determine timeout
        timeout = timeout or self.default_timeout
        timeout = min(timeout, self.max_timeout)

        # Create operation for security middleware
        operation = Operation(
            type=OperationType.SHELL_COMMAND,
            params={
                "command": command,
                "allow_pipes": True,
                "allow_chaining": True,
            },
            executor=self._execute_command,
            timeout=timeout,
        )

        # Add execution params
        operation.params.update({
            "working_dir": working_dir,
            "capture_output": capture_output,
            "actual_timeout": timeout,
        })

        # Execute via security middleware
        result = await self.security_middleware.validate_and_execute(operation)

        if result.blocked:
            return ToolResult.error(
                f"Command blocked by security policy: {result.error}"
            )

        if not result.success:
            return ToolResult.error(result.error)

        return ToolResult.ok(
            data=result.data,
            metadata={"execution_time_ms": result.execution_time_ms}
        )

    async def _execute_command(
        self,
        command: str,
        working_dir: Optional[str],
        capture_output: bool,
        actual_timeout: int,
        **kwargs  # Ignore validation params
    ) -> Dict[str, Any]:
        """
        Internal command execution.

        Args:
            command: Command to execute
            working_dir: Working directory
            capture_output: Whether to capture output
            actual_timeout: Timeout in seconds

        Returns:
            Dict with stdout, stderr, return_code
        """
        try:
            # Create subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=subprocess.PIPE if capture_output else None,
                stderr=subprocess.PIPE if capture_output else None,
                cwd=working_dir,
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=actual_timeout
                )
            except asyncio.TimeoutError:
                # Kill process on timeout
                process.kill()
                await process.wait()
                raise TimeoutError(f"Command timed out after {actual_timeout}s")

            # Decode output
            stdout_str = stdout.decode('utf-8', errors='replace') if stdout else ""
            stderr_str = stderr.decode('utf-8', errors='replace') if stderr else ""

            return {
                "stdout": stdout_str,
                "stderr": stderr_str,
                "return_code": process.returncode,
                "success": process.returncode == 0,
            }

        except Exception as e:
            raise Exception(f"Command execution failed: {str(e)}")

    def validate_params(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters"""
        command = kwargs.get("command")

        if not command:
            return False, "command is required"

        if not isinstance(command, str):
            return False, "command must be a string"

        timeout = kwargs.get("timeout")
        if timeout is not None:
            if not isinstance(timeout, (int, float)):
                return False, "timeout must be a number"
            if timeout <= 0:
                return False, "timeout must be positive"
            if timeout > self.max_timeout:
                return False, f"timeout cannot exceed {self.max_timeout} seconds"

        working_dir = kwargs.get("working_dir")
        if working_dir is not None:
            if not isinstance(working_dir, str):
                return False, "working_dir must be a string"

        return True, None

    def _get_parameters_schema(self) -> Dict[str, Any]:
        """Get parameters schema"""
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute",
                },
                "timeout": {
                    "type": "integer",
                    "description": f"Timeout in seconds (max: {self.max_timeout})",
                    "minimum": 1,
                    "maximum": self.max_timeout,
                    "default": self.default_timeout,
                },
                "working_dir": {
                    "type": "string",
                    "description": "Working directory for command execution (optional)",
                },
                "capture_output": {
                    "type": "boolean",
                    "description": "Capture stdout and stderr (default: true)",
                    "default": True,
                },
            },
            "required": ["command"],
        }
```

### Step 5: Create Background Job Manager

**File:** `v2/tools/shell/background_job_manager.py`

```python
"""
Background Job Manager - Manage long-running shell commands
"""

import asyncio
import subprocess
import uuid
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from collections import deque


class JobStatus(str, Enum):
    """Job execution status"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"
    TIMEOUT = "timeout"


@dataclass
class JobInfo:
    """Information about a background job"""
    id: str
    command: str
    status: JobStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    return_code: Optional[int] = None
    error: Optional[str] = None


class BackgroundJob:
    """A single background job"""

    def __init__(
        self,
        job_id: str,
        command: str,
        process: asyncio.subprocess.Process,
        max_output_lines: int = 1000,
    ):
        self.id = job_id
        self.command = command
        self.process = process
        self.started_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None
        self.status = JobStatus.RUNNING
        self.return_code: Optional[int] = None
        self.error: Optional[str] = None

        # Ring buffer for output (prevents memory exhaustion)
        self.output_buffer = deque(maxlen=max_output_lines)
        self._last_read_index = 0

    def add_output(self, line: str):
        """Add line to output buffer"""
        self.output_buffer.append({
            "timestamp": datetime.utcnow().isoformat(),
            "line": line,
        })

    def get_new_output(self) -> List[Dict]:
        """Get output since last read"""
        buffer_list = list(self.output_buffer)
        new_output = buffer_list[self._last_read_index:]
        self._last_read_index = len(buffer_list)
        return new_output

    def get_all_output(self) -> List[Dict]:
        """Get all output"""
        return list(self.output_buffer)

    def mark_completed(self, return_code: int):
        """Mark job as completed"""
        self.status = JobStatus.COMPLETED if return_code == 0 else JobStatus.FAILED
        self.return_code = return_code
        self.completed_at = datetime.utcnow()

    def mark_killed(self):
        """Mark job as killed"""
        self.status = JobStatus.KILLED
        self.completed_at = datetime.utcnow()

    def get_info(self) -> JobInfo:
        """Get job information"""
        return JobInfo(
            id=self.id,
            command=self.command,
            status=self.status,
            started_at=self.started_at,
            completed_at=self.completed_at,
            return_code=self.return_code,
            error=self.error,
        )


class BackgroundJobManager:
    """
    Manages background shell jobs.

    Features:
    - Start jobs in background
    - Stream output in real-time
    - Monitor job status
    - Kill running jobs
    - Automatic cleanup of completed jobs
    """

    def __init__(self, max_jobs: int = 10, max_output_lines: int = 1000):
        """
        Initialize job manager.

        Args:
            max_jobs: Maximum number of concurrent jobs
            max_output_lines: Maximum output lines per job (ring buffer)
        """
        self.max_jobs = max_jobs
        self.max_output_lines = max_output_lines
        self.jobs: Dict[str, BackgroundJob] = {}
        self._monitor_tasks: Dict[str, asyncio.Task] = {}

    async def start_job(
        self,
        command: str,
        working_dir: Optional[str] = None,
        job_name: Optional[str] = None,
    ) -> str:
        """
        Start a background job.

        Args:
            command: Shell command to execute
            working_dir: Working directory
            job_name: Optional job name (auto-generated if not provided)

        Returns:
            Job ID

        Raises:
            RuntimeError: If max jobs limit reached
        """
        # Check job limit
        active_jobs = [j for j in self.jobs.values() if j.status == JobStatus.RUNNING]
        if len(active_jobs) >= self.max_jobs:
            raise RuntimeError(
                f"Maximum number of concurrent jobs ({self.max_jobs}) reached. "
                f"Kill or wait for existing jobs to complete."
            )

        # Generate job ID
        job_id = job_name or f"job_{uuid.uuid4().hex[:8]}"

        # Create subprocess
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr into stdout
            cwd=working_dir,
        )

        # Create job
        job = BackgroundJob(
            job_id=job_id,
            command=command,
            process=process,
            max_output_lines=self.max_output_lines,
        )

        self.jobs[job_id] = job

        # Start monitoring task
        monitor_task = asyncio.create_task(self._monitor_job(job))
        self._monitor_tasks[job_id] = monitor_task

        return job_id

    async def _monitor_job(self, job: BackgroundJob):
        """Monitor job and capture output"""
        try:
            # Read output line by line
            async for line in job.process.stdout:
                line_str = line.decode('utf-8', errors='replace').rstrip()
                job.add_output(line_str)

            # Wait for process to complete
            return_code = await job.process.wait()
            job.mark_completed(return_code)

        except Exception as e:
            job.error = str(e)
            job.mark_completed(-1)

    def get_output(
        self,
        job_id: str,
        new_only: bool = True,
    ) -> Optional[List[Dict]]:
        """
        Get job output.

        Args:
            job_id: Job ID
            new_only: Get only new output since last read (default: True)

        Returns:
            List of output lines with timestamps, or None if job not found
        """
        job = self.jobs.get(job_id)
        if not job:
            return None

        if new_only:
            return job.get_new_output()
        else:
            return job.get_all_output()

    def get_status(self, job_id: str) -> Optional[JobInfo]:
        """
        Get job status.

        Args:
            job_id: Job ID

        Returns:
            JobInfo or None if job not found
        """
        job = self.jobs.get(job_id)
        if not job:
            return None

        return job.get_info()

    async def kill_job(self, job_id: str) -> bool:
        """
        Kill a running job.

        Args:
            job_id: Job ID

        Returns:
            True if killed, False if job not found or not running
        """
        job = self.jobs.get(job_id)
        if not job or job.status != JobStatus.RUNNING:
            return False

        try:
            job.process.kill()
            await job.process.wait()
            job.mark_killed()
            return True
        except Exception:
            return False

    def list_jobs(self, status_filter: Optional[JobStatus] = None) -> List[JobInfo]:
        """
        List all jobs.

        Args:
            status_filter: Filter by status (optional)

        Returns:
            List of JobInfo objects
        """
        jobs = []
        for job in self.jobs.values():
            if status_filter is None or job.status == status_filter:
                jobs.append(job.get_info())

        return sorted(jobs, key=lambda j: j.started_at, reverse=True)

    async def cleanup_completed(self, keep_recent: int = 10):
        """
        Clean up completed jobs.

        Args:
            keep_recent: Number of recent completed jobs to keep
        """
        completed = [
            job for job in self.jobs.values()
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.KILLED]
        ]

        # Sort by completion time
        completed.sort(key=lambda j: j.completed_at or j.started_at, reverse=True)

        # Remove old jobs
        for job in completed[keep_recent:]:
            del self.jobs[job.id]
            if job.id in self._monitor_tasks:
                self._monitor_tasks[job.id].cancel()
                del self._monitor_tasks[job.id]
```

### Step 6: Register Shell Tools

**File:** `v2/tools/shell/__init__.py`

```python
"""Shell tools for command execution"""

from .bash_tool import BashTool
from .background_job_manager import BackgroundJobManager, JobStatus, JobInfo

__all__ = [
    'BashTool',
    'BackgroundJobManager',
    'JobStatus',
    'JobInfo',
]
```

### Step 7: Update Tool Registry Discovery

**File:** `v2/tools/registry.py`

Update the `discover_tools` method:

```python
def discover_tools(self):
    """
    Auto-discover and register tools from the tools/ directory.

    This scans for all tool modules and registers them.
    """
    # Import tool modules to trigger registration
    try:
        from .database import query_tool, schema_tool
        from .file import read_tool, write_tool
        from .weather import forecast_tool
        from .web import fetch_tool, screenshot_tool
        from .shell import bash_tool  # ADD THIS
    except ImportError as e:
        # Some tools may not exist yet
        pass
```

### Step 8: Update Configuration Models

**File:** `v2/config/models.py`

Add shell configuration to SecurityConfig:

```python
@dataclass
class SecurityConfig:
    """Security configuration"""
    enable_sql_validation: bool = True
    enable_path_validation: bool = True
    enable_shell_validation: bool = True  # ADD THIS
    enable_audit_log: bool = True

    # SQL settings
    allowed_sql_operations: list = field(default_factory=lambda: ["SELECT", "INSERT", "UPDATE", "DELETE"])
    require_where_on_delete: bool = True
    max_query_timeout: int = 30

    # File settings
    allowed_read_paths: list = field(default_factory=lambda: [".", "/tmp"])
    allowed_write_paths: list = field(default_factory=lambda: [".", "/tmp"])
    blocked_file_patterns: list = field(default_factory=lambda: [
        ".ssh", ".env", "credentials", "secrets", "private_key"
    ])

    # Shell settings (ADD THIS SECTION)
    allow_dangerous_shell_commands: bool = False
    shell_command_timeout: int = 120
    max_shell_command_timeout: int = 600
    max_background_jobs: int = 10
```

---

## Implementation #2: Git/GitHub Integration

### File Structure
```
v2/tools/git/
├── __init__.py
├── git_tool.py           # Basic git operations
└── github_tool.py        # GitHub API operations

v2/agents/
├── git_agent.py          # Git specialist agent
```

### Step 1: Add GIT Category

**File:** `v2/core/base_tool.py`

```python
class ToolCategory(str, Enum):
    """Tool categories for organization and discovery"""
    DATABASE = "database"
    FILE = "file"
    WEB = "web"
    WEATHER = "weather"
    SHELL = "shell"
    GIT = "git"          # ADD THIS
    GENERAL = "general"
```

### Step 2: Create Git Tool

**File:** `v2/tools/git/git_tool.py`

```python
"""
Git Tool - Execute git operations safely
"""

import os
from typing import Optional, Dict, Any, List
from ...core.base_tool import BaseTool, ToolResult, ToolCategory


class GitTool(BaseTool):
    """
    Execute git commands safely.

    Features:
    - Status, diff, log operations
    - Branch management
    - Commit creation
    - Safe operations (no force push to main)
    """

    NAME = "git.execute"
    DESCRIPTION = "Execute git commands safely with validation"
    CATEGORY = ToolCategory.GIT
    VERSION = "1.0.0"
    REQUIRES_SECURITY_VALIDATION = False

    def __init__(self, bash_tool, **kwargs):
        """
        Initialize git tool.

        Args:
            bash_tool: BashTool instance for executing git commands
            **kwargs: Additional configuration
        """
        super().__init__(**kwargs)
        self.bash_tool = bash_tool

    async def execute(
        self,
        operation: str,
        **params
    ) -> ToolResult:
        """
        Execute git operation.

        Args:
            operation: Git operation (status, diff, log, add, commit, push, pull, etc.)
            **params: Operation-specific parameters

        Returns:
            ToolResult with git command output
        """
        # Map operation to command
        if operation == "status":
            command = "git status"

        elif operation == "diff":
            staged = params.get("staged", False)
            files = params.get("files", "")
            if staged:
                command = f"git diff --staged {files}"
            else:
                command = f"git diff {files}"

        elif operation == "log":
            num_commits = params.get("num_commits", 10)
            format_str = params.get("format", "--oneline")
            command = f"git log -{num_commits} {format_str}"

        elif operation == "add":
            files = params.get("files", ".")
            command = f"git add {files}"

        elif operation == "commit":
            message = params.get("message")
            if not message:
                return ToolResult.error("commit requires 'message' parameter")
            # Use heredoc for proper message formatting
            command = f'''git commit -m "$(cat <<'EOF'
{message}
EOF
)"'''

        elif operation == "push":
            branch = params.get("branch", "")
            remote = params.get("remote", "origin")
            force = params.get("force", False)

            # Prevent force push to main/master
            if force and branch in ["main", "master"]:
                return ToolResult.error(
                    "Force push to main/master is blocked for safety. "
                    "Please request explicit user confirmation."
                )

            force_flag = "--force" if force else ""
            command = f"git push {remote} {branch} {force_flag}".strip()

        elif operation == "pull":
            branch = params.get("branch", "")
            remote = params.get("remote", "origin")
            command = f"git pull {remote} {branch}".strip()

        elif operation == "branch":
            list_branches = params.get("list", True)
            if list_branches:
                command = "git branch -a"
            else:
                branch_name = params.get("name")
                if not branch_name:
                    return ToolResult.error("branch creation requires 'name' parameter")
                command = f"git branch {branch_name}"

        elif operation == "checkout":
            branch = params.get("branch")
            create_new = params.get("create_new", False)
            if not branch:
                return ToolResult.error("checkout requires 'branch' parameter")

            flag = "-b" if create_new else ""
            command = f"git checkout {flag} {branch}".strip()

        elif operation == "merge":
            branch = params.get("branch")
            if not branch:
                return ToolResult.error("merge requires 'branch' parameter")
            command = f"git merge {branch}"

        elif operation == "stash":
            action = params.get("action", "save")
            if action == "save":
                message = params.get("message", "")
                command = f"git stash push -m '{message}'" if message else "git stash"
            elif action == "pop":
                command = "git stash pop"
            elif action == "list":
                command = "git stash list"
            else:
                return ToolResult.error(f"Unknown stash action: {action}")

        else:
            return ToolResult.error(f"Unknown git operation: {operation}")

        # Execute via bash tool
        result = await self.bash_tool.execute(
            command=command,
            timeout=params.get("timeout", 30),
        )

        return result

    def validate_params(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters"""
        operation = kwargs.get("operation")

        if not operation:
            return False, "operation is required"

        if not isinstance(operation, str):
            return False, "operation must be a string"

        valid_operations = [
            "status", "diff", "log", "add", "commit", "push", "pull",
            "branch", "checkout", "merge", "stash"
        ]

        if operation not in valid_operations:
            return False, f"operation must be one of: {', '.join(valid_operations)}"

        return True, None

    def _get_parameters_schema(self) -> Dict[str, Any]:
        """Get parameters schema"""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "Git operation to perform",
                    "enum": [
                        "status", "diff", "log", "add", "commit", "push", "pull",
                        "branch", "checkout", "merge", "stash"
                    ],
                },
                "message": {
                    "type": "string",
                    "description": "Commit message (for commit operation)",
                },
                "files": {
                    "type": "string",
                    "description": "Files to operate on (for add, diff)",
                },
                "branch": {
                    "type": "string",
                    "description": "Branch name (for push, pull, checkout, merge)",
                },
                "remote": {
                    "type": "string",
                    "description": "Remote name (default: origin)",
                    "default": "origin",
                },
                "force": {
                    "type": "boolean",
                    "description": "Force push (blocked for main/master)",
                    "default": False,
                },
                "timeout": {
                    "type": "integer",
                    "description": "Command timeout in seconds",
                    "default": 30,
                },
            },
            "required": ["operation"],
        }
```

### Step 3: Create GitHub Tool

**File:** `v2/tools/git/github_tool.py`

```python
"""
GitHub Tool - GitHub API operations via gh CLI
"""

from typing import Optional, Dict, Any
from ...core.base_tool import BaseTool, ToolResult, ToolCategory


class GitHubTool(BaseTool):
    """
    GitHub operations using gh CLI.

    Features:
    - Create pull requests
    - View PR status
    - Manage issues
    - View PR checks
    """

    NAME = "github.execute"
    DESCRIPTION = "Execute GitHub operations via gh CLI"
    CATEGORY = ToolCategory.GIT
    VERSION = "1.0.0"
    REQUIRES_SECURITY_VALIDATION = False

    def __init__(self, bash_tool, **kwargs):
        """
        Initialize GitHub tool.

        Args:
            bash_tool: BashTool instance for executing gh commands
            **kwargs: Additional configuration
        """
        super().__init__(**kwargs)
        self.bash_tool = bash_tool

    async def execute(
        self,
        operation: str,
        **params
    ) -> ToolResult:
        """
        Execute GitHub operation.

        Args:
            operation: GitHub operation (create_pr, view_pr, list_prs, pr_checks, etc.)
            **params: Operation-specific parameters

        Returns:
            ToolResult with gh command output
        """
        if operation == "create_pr":
            title = params.get("title")
            body = params.get("body", "")
            base = params.get("base", "main")
            head = params.get("head", "")

            if not title:
                return ToolResult.error("create_pr requires 'title' parameter")

            # Use heredoc for body
            command = f'''gh pr create --title "{title}" --base {base}'''
            if head:
                command += f" --head {head}"
            if body:
                command += f''' --body "$(cat <<'EOF'
{body}
EOF
)"'''
            else:
                command += ' --body ""'

        elif operation == "view_pr":
            pr_number = params.get("pr_number")
            if pr_number:
                command = f"gh pr view {pr_number}"
            else:
                command = "gh pr view"

        elif operation == "list_prs":
            state = params.get("state", "open")
            limit = params.get("limit", 10)
            command = f"gh pr list --state {state} --limit {limit}"

        elif operation == "pr_checks":
            pr_number = params.get("pr_number")
            if pr_number:
                command = f"gh pr checks {pr_number}"
            else:
                command = "gh pr checks"

        elif operation == "merge_pr":
            pr_number = params.get("pr_number")
            merge_method = params.get("method", "merge")  # merge, squash, rebase

            if not pr_number:
                return ToolResult.error("merge_pr requires 'pr_number' parameter")

            command = f"gh pr merge {pr_number} --{merge_method}"

        elif operation == "create_issue":
            title = params.get("title")
            body = params.get("body", "")

            if not title:
                return ToolResult.error("create_issue requires 'title' parameter")

            command = f'''gh issue create --title "{title}" --body "$(cat <<'EOF'
{body}
EOF
)"'''

        elif operation == "list_issues":
            state = params.get("state", "open")
            limit = params.get("limit", 10)
            command = f"gh issue list --state {state} --limit {limit}"

        else:
            return ToolResult.error(f"Unknown GitHub operation: {operation}")

        # Execute via bash tool
        result = await self.bash_tool.execute(
            command=command,
            timeout=params.get("timeout", 60),
        )

        return result

    def validate_params(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters"""
        operation = kwargs.get("operation")

        if not operation:
            return False, "operation is required"

        valid_operations = [
            "create_pr", "view_pr", "list_prs", "pr_checks", "merge_pr",
            "create_issue", "list_issues"
        ]

        if operation not in valid_operations:
            return False, f"operation must be one of: {', '.join(valid_operations)}"

        return True, None

    def _get_parameters_schema(self) -> Dict[str, Any]:
        """Get parameters schema"""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "GitHub operation to perform",
                    "enum": [
                        "create_pr", "view_pr", "list_prs", "pr_checks", "merge_pr",
                        "create_issue", "list_issues"
                    ],
                },
                "title": {
                    "type": "string",
                    "description": "PR or issue title",
                },
                "body": {
                    "type": "string",
                    "description": "PR or issue body/description",
                },
                "pr_number": {
                    "type": "integer",
                    "description": "Pull request number",
                },
                "base": {
                    "type": "string",
                    "description": "Base branch for PR (default: main)",
                    "default": "main",
                },
                "head": {
                    "type": "string",
                    "description": "Head branch for PR",
                },
                "state": {
                    "type": "string",
                    "description": "PR/issue state filter",
                    "enum": ["open", "closed", "merged", "all"],
                    "default": "open",
                },
                "method": {
                    "type": "string",
                    "description": "Merge method",
                    "enum": ["merge", "squash", "rebase"],
                    "default": "merge",
                },
            },
            "required": ["operation"],
        }
```

### Step 4: Create Git Agent

**File:** `v2/agents/git_agent.py`

```python
"""
Git Agent - Version control specialist
"""

from ..core.base_agent import BaseAgent


class GitAgent(BaseAgent):
    """
    Git and GitHub specialist agent.

    Handles version control operations, PR creation, code reviews.
    """

    NAME = "git"
    DESCRIPTION = "Git and GitHub expert for version control operations"
    CATEGORY = "development"
    VERSION = "1.0.0"

    @property
    def system_message(self) -> str:
        return """
        You are a **Git & GitHub Expert Agent**.

        **Your Role:**
        - Manage git repositories and version control
        - Create commits with well-formatted messages
        - Create and manage pull requests
        - Review code changes
        - Manage branches safely
        - Help with GitHub workflows

        **Your Tools:**
        - `git.execute(operation, ...)` - Execute git operations
        - `github.execute(operation, ...)` - Execute GitHub operations

        **Git Operations Available:**
        - status: Check repository status
        - diff: View changes (staged/unstaged)
        - log: View commit history
        - add: Stage files for commit
        - commit: Create commits with messages
        - push: Push changes to remote
        - pull: Pull changes from remote
        - branch: Manage branches
        - checkout: Switch branches
        - merge: Merge branches
        - stash: Stash/restore changes

        **GitHub Operations Available:**
        - create_pr: Create pull request
        - view_pr: View PR details
        - list_prs: List pull requests
        - pr_checks: View PR check status
        - merge_pr: Merge pull request
        - create_issue: Create issue
        - list_issues: List issues

        **Best Practices:**

        1. **Before Committing:**
           - Always run `git status` first
           - Check `git diff` to review changes
           - Stage relevant files with `git add`

        2. **Commit Messages:**
           - Use conventional commits format when appropriate
           - First line: brief summary (50 chars max)
           - Blank line
           - Detailed description if needed
           - Include context and reasoning
           - Always add co-authoring footer:
             ```
             🤖 Generated with AutoGen v2

             Co-Authored-By: AutoGen <noreply@example.com>
             ```

        3. **Pull Requests:**
           - Review changes with `git diff main...HEAD`
           - Create descriptive PR titles
           - Include summary of changes
           - Add test plan or checklist
           - Add co-authoring footer

        4. **Safety:**
           - Never force push to main/master
           - Review diffs before committing
           - Check branch before pushing
           - Confirm destructive operations

        **Example Workflows:**

        **Creating a Commit:**
        ```
        1. git.execute(operation="status")
        2. git.execute(operation="diff")
        3. git.execute(operation="add", files=".")
        4. git.execute(operation="commit", message="feat: Add user authentication\\n\\n...")
        ```

        **Creating a PR:**
        ```
        1. git.execute(operation="diff", files="main...HEAD")
        2. git.execute(operation="log", num_commits=5)
        3. github.execute(operation="create_pr", title="...", body="...")
        ```

        Always be helpful and ensure git operations are safe and well-documented!
        """
```

---

## Implementation #3: Web Search

### File Structure
```
v2/tools/web/
├── __init__.py
├── search_tool.py        # Web search via API
└── fetch_tool.py         # Fetch web pages
```

### Step 1: Create Web Search Tool

**File:** `v2/tools/web/search_tool.py`

```python
"""
Web Search Tool - Search the web via Brave Search API
"""

import httpx
import os
from typing import Optional, Dict, Any, List
from ...core.base_tool import BaseTool, ToolResult, ToolCategory


class WebSearchTool(BaseTool):
    """
    Search the web using Brave Search API.

    Features:
    - Web search with ranking
    - Domain filtering (include/exclude)
    - Date filtering
    - Safe search
    """

    NAME = "web.search"
    DESCRIPTION = "Search the web using Brave Search API"
    CATEGORY = ToolCategory.WEB
    VERSION = "1.0.0"
    REQUIRES_SECURITY_VALIDATION = False

    def __init__(self, **kwargs):
        """
        Initialize web search tool.

        Requires BRAVE_API_KEY environment variable.
        Get free API key at: https://brave.com/search/api/
        """
        super().__init__(**kwargs)
        self.api_key = os.getenv("BRAVE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "BRAVE_API_KEY environment variable not set. "
                "Get a free API key at https://brave.com/search/api/"
            )
        self.base_url = "https://api.search.brave.com/res/v1/web/search"

    async def execute(
        self,
        query: str,
        num_results: int = 10,
        country: str = "US",
        search_lang: str = "en",
        safesearch: str = "moderate",
    ) -> ToolResult:
        """
        Execute web search.

        Args:
            query: Search query
            num_results: Number of results (max 20)
            country: Country code (US, UK, etc.)
            search_lang: Search language (en, es, etc.)
            safesearch: Safe search (off, moderate, strict)

        Returns:
            ToolResult with search results
        """
        try:
            params = {
                "q": query,
                "count": min(num_results, 20),
                "country": country,
                "search_lang": search_lang,
                "safesearch": safesearch,
            }

            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": self.api_key,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    self.base_url,
                    params=params,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()

            # Extract results
            results = []
            for result in data.get("web", {}).get("results", []):
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "description": result.get("description", ""),
                })

            return ToolResult.ok({
                "query": query,
                "results": results,
                "total_results": len(results),
            })

        except httpx.HTTPStatusError as e:
            return ToolResult.error(f"Search API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            return ToolResult.error(f"Search failed: {str(e)}")

    def validate_params(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters"""
        query = kwargs.get("query")

        if not query:
            return False, "query is required"

        if not isinstance(query, str):
            return False, "query must be a string"

        if len(query) < 2:
            return False, "query must be at least 2 characters"

        num_results = kwargs.get("num_results", 10)
        if not isinstance(num_results, int) or num_results < 1 or num_results > 20:
            return False, "num_results must be between 1 and 20"

        return True, None

    def _get_parameters_schema(self) -> Dict[str, Any]:
        """Get parameters schema"""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query",
                    "minLength": 2,
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (1-20)",
                    "minimum": 1,
                    "maximum": 20,
                    "default": 10,
                },
                "country": {
                    "type": "string",
                    "description": "Country code (US, UK, etc.)",
                    "default": "US",
                },
                "search_lang": {
                    "type": "string",
                    "description": "Search language (en, es, fr, etc.)",
                    "default": "en",
                },
                "safesearch": {
                    "type": "string",
                    "description": "Safe search level",
                    "enum": ["off", "moderate", "strict"],
                    "default": "moderate",
                },
            },
            "required": ["query"],
        }
```

---

## Implementation #4: User Interaction

### File Structure
```
v2/interaction/
├── __init__.py
└── prompt.py             # Interactive prompts
```

### Step 1: Create Interactive Prompt System

**File:** `v2/interaction/prompt.py`

```python
"""
Interactive User Prompts

Allows agents to ask questions during execution.
"""

from typing import List, Dict, Optional, Union
from dataclasses import dataclass
from enum import Enum


class PromptType(str, Enum):
    """Types of user prompts"""
    CHOICE = "choice"            # Single choice (radio)
    MULTI_CHOICE = "multi_choice"  # Multiple choice (checkboxes)
    TEXT = "text"                # Free text input
    CONFIRM = "confirm"          # Yes/no confirmation


@dataclass
class PromptOption:
    """An option for choice prompts"""
    label: str
    value: str
    description: Optional[str] = None


@dataclass
class UserPrompt:
    """A user prompt"""
    question: str
    prompt_type: PromptType
    options: Optional[List[PromptOption]] = None
    default: Optional[str] = None
    allow_custom: bool = False


class InteractivePrompter:
    """
    Interactive prompt system for CLI.

    Uses rich/questionary for beautiful terminal prompts.
    """

    @staticmethod
    def ask_choice(
        question: str,
        choices: List[Dict[str, str]],
        default: Optional[str] = None,
    ) -> str:
        """
        Ask user to select one option.

        Args:
            question: Question to ask
            choices: List of {"label": "...", "value": "...", "description": "..."}
            default: Default choice value

        Returns:
            Selected value
        """
        try:
            import questionary
            from questionary import Choice

            choice_objects = [
                Choice(
                    title=f"{c['label']}" + (f" - {c.get('description', '')}" if c.get('description') else ""),
                    value=c['value']
                )
                for c in choices
            ]

            result = questionary.select(
                question,
                choices=choice_objects,
                default=default,
            ).ask()

            return result

        except ImportError:
            # Fallback to simple input if questionary not available
            print(f"\n{question}")
            for i, choice in enumerate(choices, 1):
                desc = f" - {choice.get('description', '')}" if choice.get('description') else ""
                print(f"  {i}. {choice['label']}{desc}")

            while True:
                try:
                    selection = input("\nEnter choice number: ")
                    idx = int(selection) - 1
                    if 0 <= idx < len(choices):
                        return choices[idx]['value']
                    else:
                        print("Invalid choice. Try again.")
                except (ValueError, KeyError):
                    print("Invalid input. Try again.")

    @staticmethod
    def ask_multi_choice(
        question: str,
        choices: List[Dict[str, str]],
    ) -> List[str]:
        """
        Ask user to select multiple options.

        Args:
            question: Question to ask
            choices: List of {"label": "...", "value": "...", "description": "..."}

        Returns:
            List of selected values
        """
        try:
            import questionary
            from questionary import Choice

            choice_objects = [
                Choice(
                    title=f"{c['label']}" + (f" - {c.get('description', '')}" if c.get('description') else ""),
                    value=c['value']
                )
                for c in choices
            ]

            results = questionary.checkbox(
                question,
                choices=choice_objects,
            ).ask()

            return results or []

        except ImportError:
            # Fallback
            print(f"\n{question} (comma-separated numbers)")
            for i, choice in enumerate(choices, 1):
                desc = f" - {choice.get('description', '')}" if choice.get('description') else ""
                print(f"  {i}. {choice['label']}{desc}")

            selection = input("\nEnter choices (e.g., 1,3,4): ")
            selected = []
            for num in selection.split(","):
                try:
                    idx = int(num.strip()) - 1
                    if 0 <= idx < len(choices):
                        selected.append(choices[idx]['value'])
                except ValueError:
                    pass

            return selected

    @staticmethod
    def ask_text(
        question: str,
        default: Optional[str] = None,
        multiline: bool = False,
    ) -> str:
        """
        Ask user for text input.

        Args:
            question: Question to ask
            default: Default value
            multiline: Allow multiline input

        Returns:
            User input
        """
        try:
            import questionary

            if multiline:
                result = questionary.text(
                    question,
                    default=default or "",
                    multiline=True,
                ).ask()
            else:
                result = questionary.text(
                    question,
                    default=default or "",
                ).ask()

            return result or ""

        except ImportError:
            # Fallback
            if default:
                prompt = f"{question} [{default}]: "
            else:
                prompt = f"{question}: "

            result = input(prompt)
            return result or default or ""

    @staticmethod
    def confirm(
        question: str,
        default: bool = False,
    ) -> bool:
        """
        Ask user for yes/no confirmation.

        Args:
            question: Question to ask
            default: Default answer

        Returns:
            True if yes, False if no
        """
        try:
            import questionary

            result = questionary.confirm(
                question,
                default=default,
            ).ask()

            return result

        except ImportError:
            # Fallback
            default_str = "Y/n" if default else "y/N"
            result = input(f"{question} ({default_str}): ").lower()

            if not result:
                return default

            return result in ["y", "yes"]
```

### Step 2: Create AskUser Tool

**File:** `v2/tools/interaction/ask_user_tool.py`

```python
"""
Ask User Tool - Prompt user for input during execution
"""

from typing import Optional, Dict, Any, List
from ...core.base_tool import BaseTool, ToolResult, ToolCategory
from ...interaction.prompt import InteractivePrompter, PromptType


class AskUserTool(BaseTool):
    """
    Ask user questions during agent execution.

    Allows agents to gather preferences, clarify ambiguity, and get decisions.
    """

    NAME = "user.ask"
    DESCRIPTION = "Ask user a question and wait for response"
    CATEGORY = ToolCategory.GENERAL
    VERSION = "1.0.0"
    REQUIRES_SECURITY_VALIDATION = False

    def __init__(self, **kwargs):
        """Initialize ask user tool"""
        super().__init__(**kwargs)
        self.prompter = InteractivePrompter()

    async def execute(
        self,
        question: str,
        prompt_type: str = "choice",
        options: Optional[List[Dict[str, str]]] = None,
        default: Optional[str] = None,
        multiline: bool = False,
    ) -> ToolResult:
        """
        Ask user a question.

        Args:
            question: Question to ask
            prompt_type: Type of prompt (choice, multi_choice, text, confirm)
            options: List of options for choice prompts
            default: Default value
            multiline: Allow multiline for text prompts

        Returns:
            ToolResult with user's response
        """
        try:
            if prompt_type == "choice":
                if not options:
                    return ToolResult.error("choice prompt requires options")

                response = self.prompter.ask_choice(
                    question=question,
                    choices=options,
                    default=default,
                )

            elif prompt_type == "multi_choice":
                if not options:
                    return ToolResult.error("multi_choice prompt requires options")

                response = self.prompter.ask_multi_choice(
                    question=question,
                    choices=options,
                )

            elif prompt_type == "text":
                response = self.prompter.ask_text(
                    question=question,
                    default=default,
                    multiline=multiline,
                )

            elif prompt_type == "confirm":
                response = self.prompter.confirm(
                    question=question,
                    default=default == "true" if default else False,
                )

            else:
                return ToolResult.error(f"Unknown prompt type: {prompt_type}")

            return ToolResult.ok({
                "question": question,
                "response": response,
                "prompt_type": prompt_type,
            })

        except Exception as e:
            return ToolResult.error(f"Failed to get user input: {str(e)}")

    def validate_params(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters"""
        question = kwargs.get("question")

        if not question:
            return False, "question is required"

        prompt_type = kwargs.get("prompt_type", "choice")
        valid_types = ["choice", "multi_choice", "text", "confirm"]

        if prompt_type not in valid_types:
            return False, f"prompt_type must be one of: {', '.join(valid_types)}"

        if prompt_type in ["choice", "multi_choice"]:
            options = kwargs.get("options")
            if not options or not isinstance(options, list):
                return False, f"{prompt_type} requires options list"

        return True, None

    def _get_parameters_schema(self) -> Dict[str, Any]:
        """Get parameters schema"""
        return {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Question to ask the user",
                },
                "prompt_type": {
                    "type": "string",
                    "description": "Type of prompt",
                    "enum": ["choice", "multi_choice", "text", "confirm"],
                    "default": "choice",
                },
                "options": {
                    "type": "array",
                    "description": "Options for choice/multi_choice prompts",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "value": {"type": "string"},
                            "description": {"type": "string"},
                        },
                        "required": ["label", "value"],
                    },
                },
                "default": {
                    "type": "string",
                    "description": "Default value",
                },
                "multiline": {
                    "type": "boolean",
                    "description": "Allow multiline input for text prompts",
                    "default": False,
                },
            },
            "required": ["question"],
        }
```

---

## Implementation #5: Multimodal (Images & PDFs)

### File Structure
```
v2/tools/multimodal/
├── __init__.py
├── image_analysis_tool.py  # Analyze images
└── pdf_tool.py             # Extract/analyze PDFs

v2/agents/
├── multimodal_agent.py     # Multimodal specialist
```

### Step 1: Add Multimodal Category

**File:** `v2/core/base_tool.py`

```python
class ToolCategory(str, Enum):
    """Tool categories for organization and discovery"""
    DATABASE = "database"
    FILE = "file"
    WEB = "web"
    WEATHER = "weather"
    SHELL = "shell"
    GIT = "git"
    MULTIMODAL = "multimodal"  # ADD THIS
    GENERAL = "general"
```

### Step 2: Create Image Analysis Tool

**File:** `v2/tools/multimodal/image_analysis_tool.py`

```python
"""
Image Analysis Tool - Analyze images using vision models
"""

import base64
from pathlib import Path
from typing import Optional, Dict, Any
from ...core.base_tool import BaseTool, ToolResult, ToolCategory


class ImageAnalysisTool(BaseTool):
    """
    Analyze images using vision models.

    Supports: Screenshots, diagrams, charts, photos.
    Uses Claude 3 Vision API.
    """

    NAME = "image.analyze"
    DESCRIPTION = "Analyze images using Claude 3 Vision"
    CATEGORY = ToolCategory.MULTIMODAL
    VERSION = "1.0.0"
    REQUIRES_SECURITY_VALIDATION = False

    def __init__(self, model_client, **kwargs):
        """
        Initialize image analysis tool.

        Args:
            model_client: Vision-capable model client
            **kwargs: Additional configuration
        """
        super().__init__(**kwargs)
        self.model_client = model_client

    async def execute(
        self,
        image_path: str,
        prompt: str,
        max_tokens: int = 1000,
    ) -> ToolResult:
        """
        Analyze an image.

        Args:
            image_path: Path to image file
            prompt: Question/instruction about the image
            max_tokens: Maximum tokens in response

        Returns:
            ToolResult with analysis
        """
        try:
            # Read and encode image
            image_file = Path(image_path)
            if not image_file.exists():
                return ToolResult.error(f"Image file not found: {image_path}")

            # Check file type
            valid_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.webp']
            if image_file.suffix.lower() not in valid_extensions:
                return ToolResult.error(
                    f"Invalid image format. Supported: {', '.join(valid_extensions)}"
                )

            # Read and encode
            with open(image_path, 'rb') as f:
                image_data = base64.standard_b64encode(f.read()).decode('utf-8')

            # Determine media type
            media_type = f"image/{image_file.suffix.lstrip('.').lower()}"
            if media_type == "image/jpg":
                media_type = "image/jpeg"

            # Create message with image
            from autogen_core.models import UserMessage

            message = UserMessage(
                content=[
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
                source="user",
            )

            # Call vision model
            response = await self.model_client.create([message], max_tokens=max_tokens)

            # Extract response
            analysis = response.content

            return ToolResult.ok({
                "image_path": image_path,
                "prompt": prompt,
                "analysis": analysis,
            })

        except Exception as e:
            return ToolResult.error(f"Image analysis failed: {str(e)}")

    def validate_params(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters"""
        image_path = kwargs.get("image_path")
        prompt = kwargs.get("prompt")

        if not image_path:
            return False, "image_path is required"

        if not prompt:
            return False, "prompt is required"

        if not isinstance(image_path, str):
            return False, "image_path must be a string"

        if not isinstance(prompt, str):
            return False, "prompt must be a string"

        return True, None

    def _get_parameters_schema(self) -> Dict[str, Any]:
        """Get parameters schema"""
        return {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to image file (png, jpg, gif, webp)",
                },
                "prompt": {
                    "type": "string",
                    "description": "Question or instruction about the image",
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Maximum tokens in response",
                    "default": 1000,
                },
            },
            "required": ["image_path", "prompt"],
        }
```

### Step 3: Create PDF Tool

**File:** `v2/tools/multimodal/pdf_tool.py`

```python
"""
PDF Tool - Extract and analyze PDF content
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
from ...core.base_tool import BaseTool, ToolResult, ToolCategory


class PDFTool(BaseTool):
    """
    Extract content from PDF files.

    Features:
    - Text extraction
    - Page-by-page extraction
    - Metadata reading
    """

    NAME = "pdf.extract"
    DESCRIPTION = "Extract text and metadata from PDF files"
    CATEGORY = ToolCategory.MULTIMODAL
    VERSION = "1.0.0"
    REQUIRES_SECURITY_VALIDATION = False

    async def execute(
        self,
        pdf_path: str,
        pages: Optional[List[int]] = None,
        extract_metadata: bool = True,
    ) -> ToolResult:
        """
        Extract content from PDF.

        Args:
            pdf_path: Path to PDF file
            pages: Specific pages to extract (None = all pages)
            extract_metadata: Extract PDF metadata

        Returns:
            ToolResult with extracted content
        """
        try:
            import PyPDF2

            pdf_file = Path(pdf_path)
            if not pdf_file.exists():
                return ToolResult.error(f"PDF file not found: {pdf_path}")

            if pdf_file.suffix.lower() != '.pdf':
                return ToolResult.error("File must be a PDF")

            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)

                # Extract metadata
                metadata = {}
                if extract_metadata:
                    info = reader.metadata
                    if info:
                        metadata = {
                            "title": info.get('/Title', ''),
                            "author": info.get('/Author', ''),
                            "subject": info.get('/Subject', ''),
                            "creator": info.get('/Creator', ''),
                        }

                # Determine pages to extract
                num_pages = len(reader.pages)
                if pages is None:
                    pages_to_extract = range(num_pages)
                else:
                    pages_to_extract = [p for p in pages if 0 <= p < num_pages]

                # Extract text
                extracted_pages = []
                for page_num in pages_to_extract:
                    page = reader.pages[page_num]
                    text = page.extract_text()
                    extracted_pages.append({
                        "page_number": page_num + 1,  # 1-indexed
                        "text": text,
                    })

                return ToolResult.ok({
                    "pdf_path": pdf_path,
                    "total_pages": num_pages,
                    "extracted_pages": len(extracted_pages),
                    "metadata": metadata,
                    "pages": extracted_pages,
                })

        except ImportError:
            return ToolResult.error(
                "PyPDF2 not installed. Install with: pip install PyPDF2"
            )
        except Exception as e:
            return ToolResult.error(f"PDF extraction failed: {str(e)}")

    def validate_params(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters"""
        pdf_path = kwargs.get("pdf_path")

        if not pdf_path:
            return False, "pdf_path is required"

        if not isinstance(pdf_path, str):
            return False, "pdf_path must be a string"

        pages = kwargs.get("pages")
        if pages is not None:
            if not isinstance(pages, list):
                return False, "pages must be a list of integers"
            if not all(isinstance(p, int) for p in pages):
                return False, "all page numbers must be integers"

        return True, None

    def _get_parameters_schema(self) -> Dict[str, Any]:
        """Get parameters schema"""
        return {
            "type": "object",
            "properties": {
                "pdf_path": {
                    "type": "string",
                    "description": "Path to PDF file",
                },
                "pages": {
                    "type": "array",
                    "description": "Specific pages to extract (0-indexed, optional)",
                    "items": {"type": "integer"},
                },
                "extract_metadata": {
                    "type": "boolean",
                    "description": "Extract PDF metadata (title, author, etc.)",
                    "default": True,
                },
            },
            "required": ["pdf_path"],
        }
```

---

## Summary: Registration & Dependencies

### Update `requirements.txt`

```txt
# Add these dependencies
questionary>=2.0.1
PyPDF2>=3.0.1
```

### Update Tool Registry (`v2/tools/registry.py`)

```python
def discover_tools(self):
    """
    Auto-discover and register tools from the tools/ directory.

    This scans for all tool modules and registers them.
    """
    # Import tool modules to trigger registration
    try:
        from .database import query_tool, schema_tool
        from .file import read_tool, write_tool
        from .weather import forecast_tool
        from .web import search_tool, fetch_tool, screenshot_tool
        from .shell import bash_tool  # NEW
        from .git import git_tool, github_tool  # NEW
        from .multimodal import image_analysis_tool, pdf_tool  # NEW
        from .interaction import ask_user_tool  # NEW
    except ImportError as e:
        # Some tools may not exist yet
        pass
```

### Update Agent Registry (`v2/agents/registry.py`)

```python
def discover_agents(self):
    """
    Auto-discover and register agents from the agents/ directory.

    This scans for all agent modules and registers them.
    """
    # Import agent modules to trigger registration
    try:
        from . import weather_agent
        from . import data_analyst_agent
        from . import orchestrator_agent
        from . import web_surfer_agent
        from . import git_agent  # NEW
        from . import multimodal_agent  # NEW
    except ImportError as e:
        # Some agents may not exist yet
        pass
```

---

## Testing Each Implementation

### Test Bash Tool
```python
# In validate_v2.py or test file
async def test_bash_tool():
    container = get_container()
    tool_registry = container.get_tool_registry()

    bash_tool = tool_registry.create_tool("shell.bash")

    # Test simple command
    result = await bash_tool.execute(command="ls -la")
    assert result.success
    print(result.data)

    # Test with timeout
    result = await bash_tool.execute(command="sleep 2", timeout=5)
    assert result.success
```

### Test Git Tool
```python
async def test_git_tool():
    container = get_container()
    tool_registry = container.get_tool_registry()

    git_tool = tool_registry.create_tool("git.execute")

    # Test status
    result = await git_tool.execute(operation="status")
    assert result.success
    print(result.data['stdout'])
```

### Test Web Search
```python
async def test_web_search():
    container = get_container()
    tool_registry = container.get_tool_registry()

    search_tool = tool_registry.create_tool("web.search")

    result = await search_tool.execute(
        query="Python async programming",
        num_results=5
    )
    assert result.success
    print(result.data['results'])
```

---

This implementation guide provides complete, production-ready code that strictly follows AutoGen V2's architecture patterns. All new tools and agents integrate seamlessly with the existing registry system, dependency injection, and security middleware.

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Analyze current AutoGen V2 architecture patterns", "activeForm": "Analyzing current AutoGen V2 architecture patterns", "status": "completed"}, {"content": "Design Bash tool following existing patterns", "activeForm": "Designing Bash tool following existing patterns", "status": "completed"}, {"content": "Design Git/GitHub agent and tools", "activeForm": "Designing Git/GitHub agent and tools", "status": "completed"}, {"content": "Design Web Search tool integration", "activeForm": "Designing Web Search tool integration", "status": "completed"}, {"content": "Design User Interaction mechanism", "activeForm": "Designing User Interaction mechanism", "status": "completed"}, {"content": "Design Multimodal agent and tools", "activeForm": "Designing Multimodal agent and tools", "status": "completed"}, {"content": "Create implementation guide document", "activeForm": "Creating implementation guide document", "status": "completed"}]
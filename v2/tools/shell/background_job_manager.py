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

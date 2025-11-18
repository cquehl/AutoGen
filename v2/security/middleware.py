"""
Yamazaki v2 - Security Middleware

Centralized security layer for all operations.
Provides validation, audit logging, and timeout management.
"""

import asyncio
from typing import Any, Dict, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from .validators import SQLValidator, PathValidator, QueryType


class OperationType(str, Enum):
    """Types of operations that can be validated"""
    SQL_QUERY = "sql_query"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    WEB_FETCH = "web_fetch"


@dataclass
class Operation:
    """Operation to be validated and executed"""
    type: OperationType
    params: Dict[str, Any]
    executor: Any  # Callable that executes the operation
    timeout: int = 30


@dataclass
class OperationResult:
    """Result of operation execution"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None
    blocked: bool = False

    @classmethod
    def ok(cls, data: Any, execution_time_ms: float) -> "OperationResult":
        """Create success result"""
        return cls(success=True, data=data, execution_time_ms=execution_time_ms)

    @classmethod
    def error(cls, error: str) -> "OperationResult":
        """Create error result"""
        return cls(success=False, error=error)

    @classmethod
    def blocked(cls, reason: str) -> "OperationResult":
        """Create blocked result"""
        return cls(success=False, error=reason, blocked=True)

    @classmethod
    def timeout(cls) -> "OperationResult":
        """Create timeout result"""
        return cls(success=False, error="Operation timed out")


class AuditLogger:
    """
    Persistent audit logger for security events with tamper detection.

    Stores audit logs in SQLite database with hash-based tamper detection.
    """

    def __init__(self, enabled: bool = True, db_path: str = "./data/audit.db"):
        self.enabled = enabled
        self.db_path = db_path
        self._logger = logging.getLogger(__name__)

        if self.enabled:
            self._ensure_audit_db()

    def _ensure_audit_db(self):
        """Create audit database and table if they don't exist."""
        import sqlite3
        from pathlib import Path

        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    operation_type TEXT NOT NULL,
                    reason TEXT,
                    params TEXT,
                    result_summary TEXT,
                    error TEXT,
                    entry_hash TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_log(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_event_type ON audit_log(event_type)
            """)
            conn.commit()
        finally:
            conn.close()

    def _compute_hash(self, event: dict) -> str:
        """Compute tamper-detection hash for audit event."""
        import hashlib
        import json

        # Create deterministic string representation
        event_str = json.dumps(event, sort_keys=True)
        return hashlib.sha256(event_str.encode()).hexdigest()

    def _write_event(self, event: dict):
        """Write event to audit database."""
        import sqlite3
        import json

        # Compute hash for tamper detection
        entry_hash = self._compute_hash(event)

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                INSERT INTO audit_log (
                    timestamp, event_type, operation_type,
                    reason, params, result_summary, error, entry_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.get("timestamp"),
                event.get("event_type"),
                event.get("operation_type"),
                event.get("reason"),
                json.dumps(event.get("params", {})),
                event.get("result_summary"),
                event.get("error"),
                entry_hash
            ))
            conn.commit()
        except Exception as e:
            self._logger.error(f"Failed to write audit log: {e}")
        finally:
            conn.close()

    def log_blocked(self, operation: Operation, reason: str):
        """Log blocked operation"""
        if not self.enabled:
            return

        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "operation_blocked",
            "operation_type": operation.type.value,
            "reason": reason,
            "params": operation.params,
        }

        self._write_event(event)
        self._logger.warning(f"BLOCKED: {operation.type.value} - {reason}")

    def log_success(self, operation: Operation, result: OperationResult):
        """Log successful operation"""
        if not self.enabled:
            return

        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "operation_success",
            "operation_type": operation.type.value,
            "result_summary": str(result.data)[:200] if result.data else None,
        }

        self._write_event(event)

        # Log DELETE operations prominently
        if operation.type == OperationType.SQL_QUERY:
            query = operation.params.get("query", "")
            if query.strip().upper().startswith("DELETE"):
                self._logger.warning(f"DELETE operation executed: {query[:100]}")

    def log_error(self, operation: Operation, error: str):
        """Log operation error"""
        if not self.enabled:
            return

        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "operation_error",
            "operation_type": operation.type.value,
            "error": error,
        }

        self._write_event(event)

    def get_recent_events(self, limit: int = 100) -> list:
        """Get recent audit events from database."""
        if not self.enabled:
            return []

        import sqlite3
        import json

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("""
                SELECT timestamp, event_type, operation_type, reason, params,
                       result_summary, error, entry_hash
                FROM audit_log
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))

            events = []
            for row in cursor.fetchall():
                events.append({
                    "timestamp": row[0],
                    "event_type": row[1],
                    "operation_type": row[2],
                    "reason": row[3],
                    "params": json.loads(row[4]) if row[4] else {},
                    "result_summary": row[5],
                    "error": row[6],
                    "entry_hash": row[7]
                })

            return events
        finally:
            conn.close()


class SecurityMiddleware:
    """
    Centralized security middleware for all operations.

    Validates, executes, audits, and manages timeouts for operations.
    """

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
        }
        self.audit_logger = AuditLogger(enabled=config.enable_audit_log)

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
        else:
            is_valid, error = True, None  # No validation for other types yet

        # Block if validation failed
        if not is_valid:
            self.audit_logger.log_blocked(operation, error)
            return OperationResult.blocked(error)

        # Execute with timeout
        try:
            result = await asyncio.wait_for(
                operation.executor(**operation.params),
                timeout=operation.timeout
            )

            execution_time_ms = (time.time() - start_time) * 1000

            # Create result
            op_result = OperationResult.ok(result, execution_time_ms)

            # Audit success
            self.audit_logger.log_success(operation, op_result)

            return op_result

        except asyncio.TimeoutError:
            self.audit_logger.log_error(operation, "Operation timed out")
            return OperationResult.timeout()

        except Exception as e:
            error_msg = str(e)
            self.audit_logger.log_error(operation, error_msg)
            return OperationResult.error(error_msg)

    def _validate_sql(self, operation: Operation) -> tuple[bool, Optional[str]]:
        """Validate SQL query operation"""
        query = operation.params.get("query", "")
        validator = self.validators["sql"]
        is_valid, error, _ = validator.validate(query)
        return is_valid, error

    def _validate_file(self, operation: Operation) -> tuple[bool, Optional[str]]:
        """Validate file operation"""
        file_path = operation.params.get("file_path", "")
        op_type = "write" if operation.type == OperationType.FILE_WRITE else "read"
        validator = self.validators["path"]
        is_valid, error, _ = validator.validate(file_path, op_type)
        return is_valid, error

    def get_sql_validator(self) -> SQLValidator:
        """Get SQL validator"""
        return self.validators["sql"]

    def get_path_validator(self) -> PathValidator:
        """Get path validator"""
        return self.validators["path"]

    def get_audit_events(self, limit: int = 100) -> list:
        """Get recent audit events"""
        return self.audit_logger.get_recent_events(limit)

    def __repr__(self) -> str:
        return f"SecurityMiddleware(validators={list(self.validators.keys())})"

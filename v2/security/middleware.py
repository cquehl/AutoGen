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
    """Simple audit logger for security events"""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.events = []  # In-memory storage (use database in production)

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
        self.events.append(event)
        print(f"🚫 BLOCKED: {operation.type.value} - {reason}")

    def log_success(self, operation: Operation, result: OperationResult):
        """Log successful operation"""
        if not self.enabled:
            return

        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "operation_success",
            "operation_type": operation.type.value,
            "execution_time_ms": result.execution_time_ms,
        }
        self.events.append(event)

        # Log DELETE operations prominently
        if operation.type == OperationType.SQL_QUERY:
            query = operation.params.get("query", "")
            if query.strip().upper().startswith("DELETE"):
                print(f"⚠️  DELETE operation executed: {query[:100]}")

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
        self.events.append(event)

    def get_recent_events(self, limit: int = 100) -> list:
        """Get recent audit events"""
        return self.events[-limit:]


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

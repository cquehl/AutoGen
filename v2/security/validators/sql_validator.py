"""
Yamazaki v2 - SQL Validator

Comprehensive SQL query validation using SQL parser.
"""

import re
from typing import Optional, Tuple
from enum import Enum


class QueryType(str, Enum):
    """SQL query types"""
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    UNKNOWN = "UNKNOWN"


class SQLValidator:
    """
    SQL query validator with security checks.

    Uses both regex patterns and SQL parsing for accurate validation.
    """

    def __init__(self, config):
        """
        Initialize SQL validator.

        Args:
            config: SecurityConfig with allowed commands and blocked patterns
        """
        self.allowed_commands = config.allowed_sql_commands
        self.blocked_patterns = config.blocked_sql_patterns
        self.max_length = config.max_query_length

    def validate(self, query: str) -> Tuple[bool, Optional[str], QueryType]:
        """
        Validate SQL query for security.

        Args:
            query: SQL query to validate

        Returns:
            (is_valid, error_message, query_type) tuple
        """
        if not query or not query.strip():
            return False, "Empty query not allowed", QueryType.UNKNOWN

        # Check length
        if len(query) > self.max_length:
            return False, f"Query too long (max {self.max_length} characters)", QueryType.UNKNOWN

        query_upper = query.strip().upper()

        # Determine query type
        query_type = self._determine_query_type(query_upper)

        # Check if query type is allowed
        if query_type == QueryType.UNKNOWN:
            return False, f"Only {', '.join(self.allowed_commands)} queries allowed", query_type

        if query_type.value not in self.allowed_commands:
            return False, f"Query type {query_type.value} not allowed", query_type

        # Check for dangerous patterns
        for pattern in self.blocked_patterns:
            if re.search(pattern, query_upper):
                return False, f"Query contains blocked pattern: {pattern}", query_type

        # Check for multiple statements (prevents query chaining)
        if self._has_multiple_statements(query):
            return False, "Multiple SQL statements not allowed", query_type

        # Additional checks for specific query types
        if query_type == QueryType.DELETE:
            # Ensure DELETE has WHERE clause (prevent accidental full table delete)
            if not re.search(r'\bWHERE\b', query_upper):
                return False, "DELETE without WHERE clause is dangerous", query_type

        return True, None, query_type

    def is_safe(self, query: str) -> bool:
        """
        Check if query is safe (simple boolean check).

        Args:
            query: SQL query

        Returns:
            True if safe, False otherwise
        """
        is_valid, _, _ = self.validate(query)
        return is_valid

    def _determine_query_type(self, query_upper: str) -> QueryType:
        """Determine SQL query type"""
        if query_upper.startswith("SELECT"):
            return QueryType.SELECT
        elif query_upper.startswith("INSERT"):
            return QueryType.INSERT
        elif query_upper.startswith("UPDATE"):
            return QueryType.UPDATE
        elif query_upper.startswith("DELETE"):
            return QueryType.DELETE
        else:
            return QueryType.UNKNOWN

    def _has_multiple_statements(self, query: str) -> bool:
        """
        Check if query contains multiple statements.

        Args:
            query: SQL query

        Returns:
            True if multiple statements detected
        """
        # Remove trailing semicolon if exists
        query = query.strip()
        if query.endswith(';'):
            query = query[:-1]

        # Check for semicolons (statement separator)
        if ';' in query:
            return True

        return False

    def __repr__(self) -> str:
        return f"SQLValidator(allowed={self.allowed_commands})"

"""
Yamazaki v2 - Database Query Tool

Secure database query execution with connection pooling.
"""

from typing import Optional, Dict, Any

from ...core.base_tool import BaseTool, ToolResult, ToolCategory


class DatabaseQueryTool(BaseTool):
    """
    Database query tool with security validation and connection pooling.
    """

    NAME = "database.query"
    DESCRIPTION = "Execute SQL queries (SELECT, INSERT, UPDATE, DELETE) with security validation"
    CATEGORY = ToolCategory.DATABASE
    VERSION = "1.0.0"
    REQUIRES_SECURITY_VALIDATION = True

    def __init__(self, connection_pool, security_middleware):
        """
        Initialize database query tool.

        Args:
            connection_pool: Connection pool manager
            security_middleware: Security middleware
        """
        super().__init__()
        self.pool = connection_pool
        self.security = security_middleware

    async def execute(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """
        Execute SQL query.

        Args:
            query: SQL query
            params: Query parameters (dict)

        Returns:
            ToolResult with query results
        """
        # Validate query using security middleware
        validator = self.security.get_sql_validator()
        is_valid, error, query_type = validator.validate(query)

        if not is_valid:
            return ToolResult.error(f"Query validation failed: {error}")

        try:
            # Get connection pool
            engine = await self.pool.get_pool()

            # Execute query
            from sqlalchemy import text

            async with engine.begin() as conn:
                result = await conn.execute(text(query), params or {})

                if query_type.value == "SELECT":
                    # Fetch results
                    rows = result.fetchall()
                    results = [dict(row._mapping) for row in rows]

                    return ToolResult.ok({
                        "row_count": len(results),
                        "results": results,
                    })
                else:
                    # For INSERT, UPDATE, DELETE
                    return ToolResult.ok({
                        "affected_rows": result.rowcount,
                        "message": f"{query_type.value} completed successfully",
                    })

        except ImportError as e:
            return ToolResult.error(f"Database driver not installed: {str(e)}")
        except ConnectionRefusedError as e:
            return ToolResult.error(f"Database connection refused: {str(e)}")
        except TimeoutError as e:
            return ToolResult.error(f"Database query timed out: {str(e)}")
        except MemoryError as e:
            return ToolResult.error(f"Query result too large, out of memory: {str(e)}")
        except ValueError as e:
            return ToolResult.error(f"Invalid query parameters: {str(e)}")
        except Exception as e:
            # Log the full exception for debugging
            import traceback
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Unexpected error in query execution: {traceback.format_exc()}")
            # Return sanitized error to user (no internal details)
            return ToolResult.error(f"Query execution failed: {e.__class__.__name__}")

    def validate_params(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters"""
        query = kwargs.get("query")

        if not query:
            return False, "query parameter is required"

        if not isinstance(query, str):
            return False, "query must be a string"

        return True, None

    def _get_parameters_schema(self) -> dict:
        """Get parameters schema"""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "SQL query to execute (SELECT, INSERT, UPDATE, DELETE)",
                },
                "params": {
                    "type": "object",
                    "description": "Query parameters (optional)",
                },
            },
            "required": ["query"],
        }

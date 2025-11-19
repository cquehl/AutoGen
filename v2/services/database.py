"""
Yamazaki v2 - Database Service

Database connection pooling and query execution.
"""

from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy import pool, text

from ..config.models import DatabaseConfig


class ConnectionPoolManager:
    """
    Manages database connection pools.

    Provides connection pooling for improved performance.
    """

    def __init__(self, config: DatabaseConfig):
        """
        Initialize connection pool manager.

        Args:
            config: Database configuration
        """
        self.config = config
        self._pools: Dict[str, AsyncEngine] = {}

    async def get_pool(self, connection_string: Optional[str] = None) -> AsyncEngine:
        """
        Get or create connection pool.

        Args:
            connection_string: Database URL (uses config if not provided)

        Returns:
            SQLAlchemy AsyncEngine with connection pooling
        """
        conn_str = connection_string or self.config.url

        # Return cached pool if exists
        if conn_str in self._pools:
            return self._pools[conn_str]

        # Convert to async URL
        async_url = self._convert_to_async_url(conn_str)

        # Create async engine with connection pooling
        engine = create_async_engine(
            async_url,
            poolclass=pool.QueuePool,
            pool_size=self.config.pool_size,
            max_overflow=self.config.max_overflow,
            pool_timeout=self.config.pool_timeout,
            pool_recycle=self.config.pool_recycle,
            echo=False,  # Set to True for SQL debugging
        )

        # Cache the pool
        self._pools[conn_str] = engine

        return engine

    def _convert_to_async_url(self, connection_string: str) -> str:
        """Convert standard database URL to async version"""
        if connection_string.startswith("sqlite:///"):
            return connection_string.replace("sqlite:///", "sqlite+aiosqlite:///")
        elif connection_string.startswith("postgresql://"):
            return connection_string.replace("postgresql://", "postgresql+asyncpg://")
        elif connection_string.startswith("mysql://"):
            return connection_string.replace("mysql://", "mysql+aiomysql://")
        else:
            raise ValueError(f"Unsupported database type: {connection_string}")

    async def dispose(self):
        """Dispose of all connection pools"""
        for engine in self._pools.values():
            await engine.dispose()
        self._pools.clear()


class DatabaseService:
    """
    High-level database service.

    Provides query execution with connection pooling and security.
    """

    def __init__(self, pool: ConnectionPoolManager, security):
        """
        Initialize database service.

        Args:
            pool: Connection pool manager
            security: Security middleware
        """
        self.pool = pool
        self.security = security

    async def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        connection_string: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute SQL query with security validation.

        Args:
            query: SQL query
            params: Query parameters (dict)
            connection_string: Optional database URL

        Returns:
            Query results or error info
        """
        # Get SQL validator
        validator = self.security.get_sql_validator()

        # Validate query
        is_valid, error, query_type = validator.validate(query)
        if not is_valid:
            return {
                "success": False,
                "error": f"Query validation failed: {error}",
                "query": query[:100],
            }

        try:
            # Get connection pool
            engine = await self.pool.get_pool(connection_string)

            # Execute query
            async with engine.begin() as conn:
                result = await conn.execute(text(query), params or {})

                if query_type.value == "SELECT":
                    # Fetch results
                    rows = result.fetchall()
                    results = [dict(row._mapping) for row in rows]

                    return {
                        "success": True,
                        "row_count": len(results),
                        "results": results,
                    }
                else:
                    # For INSERT, UPDATE, DELETE
                    return {
                        "success": True,
                        "affected_rows": result.rowcount,
                        "message": f"{query_type.value} completed successfully",
                    }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query": query[:100],
            }

    async def list_tables(self, connection_string: Optional[str] = None) -> Dict[str, Any]:
        """List all tables in database"""
        # Determine database type
        conn_str = connection_string or self.pool.config.url

        if "sqlite" in conn_str:
            query = "SELECT name FROM sqlite_master WHERE type='table'"
        elif "postgresql" in conn_str:
            query = "SELECT tablename FROM pg_tables WHERE schemaname='public'"
        elif "mysql" in conn_str:
            query = "SHOW TABLES"
        else:
            return {"success": False, "error": "Unsupported database type"}

        result = await self.execute_query(query, connection_string=connection_string)

        if result.get("success"):
            tables = [list(row.values())[0] for row in result["results"]]
            return {"success": True, "tables": tables, "count": len(tables)}
        else:
            return result

    async def describe_table(
        self,
        table_name: str,
        connection_string: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get table schema information"""
        # Validate table name (alphanumeric and underscore only)
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
            return {"success": False, "error": "Invalid table name"}

        # Determine database type
        conn_str = connection_string or self.pool.config.url

        # Use parameterized queries to prevent SQL injection
        if "sqlite" in conn_str:
            # SQLite PRAGMA doesn't support parameters, but table name is validated
            query = f"PRAGMA table_info({table_name})"
            params = None
        elif "postgresql" in conn_str:
            # Use parameterized query for PostgreSQL
            query = "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = :table_name"
            params = {"table_name": table_name}
        elif "mysql" in conn_str:
            # MySQL DESCRIBE doesn't support parameters, but table name is validated
            query = f"DESCRIBE {table_name}"
            params = None
        else:
            return {"success": False, "error": "Unsupported database type"}

        result = await self.execute_query(query, params=params, connection_string=connection_string)

        if result.get("success"):
            return {"success": True, "table": table_name, "schema": result["results"]}
        else:
            return result

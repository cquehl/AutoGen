"""
Data Access Tools for AutoGen CLI Agent

Provides database connectivity, file reading, and CSV parsing capabilities.

Security Features:
- SQL query validation and whitelisting
- Path traversal protection
- Database connection pooling
- Query timeouts
"""

import os
import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
import sqlite3
import re
from enum import Enum
from sqlalchemy import create_engine, text, pool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
import asyncio


# Security: Allowed directories for file operations
ALLOWED_FILE_DIRECTORIES = [
    Path.cwd(),  # Current working directory
    Path.home() / "agent_output",  # Safe output directory
    Path.home() / "data",  # Data directory
]

# Security: Maximum query execution time (seconds)
QUERY_TIMEOUT = 30

# Connection Pool Configuration
POOL_SIZE = 5           # Number of connections to maintain
MAX_OVERFLOW = 10       # Additional connections beyond pool_size
POOL_TIMEOUT = 30       # Timeout for getting connection from pool
POOL_RECYCLE = 3600     # Recycle connections after 1 hour

# Global connection pool cache
_connection_pools: Dict[str, AsyncEngine] = {}

# Security: Query validation patterns
class QueryType(Enum):
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"  # Allowed but logged
    UNKNOWN = "UNKNOWN"


def _validate_sql_query(query: str) -> tuple[bool, Optional[str], QueryType]:
    """
    Validate SQL query to prevent SQL injection and dangerous operations.

    Returns:
        (is_valid, error_message, query_type) tuple
    """
    query_upper = query.strip().upper()

    # Determine query type
    if query_upper.startswith("SELECT"):
        query_type = QueryType.SELECT
    elif query_upper.startswith("INSERT"):
        query_type = QueryType.INSERT
    elif query_upper.startswith("UPDATE"):
        query_type = QueryType.UPDATE
    elif query_upper.startswith("DELETE"):
        query_type = QueryType.DELETE
    else:
        return False, "Only SELECT, INSERT, UPDATE, DELETE queries allowed", QueryType.UNKNOWN

    # Block dangerous SQL commands
    dangerous_patterns = [
        r'\bDROP\b',
        r'\bTRUNCATE\b',
        r'\bALTER\b',
        r'\bCREATE\b',
        r'\bEXEC\b',
        r'\bEXECUTE\b',
        r'--',  # SQL comments can hide malicious code
        r'/\*',  # Block comment
        r'\bSHUTDOWN\b',
        r'\bGRANT\b',
        r'\bREVOKE\b',
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, query_upper):
            return False, f"Query contains blocked SQL command: {pattern}", query_type

    # Block multiple statements (prevents query chaining)
    if ';' in query and not query.strip().endswith(';'):
        return False, "Multiple SQL statements not allowed", query_type

    return True, None, query_type


def _validate_file_path(file_path: str, operation: str = "read") -> tuple[bool, Optional[str], Optional[Path]]:
    """
    Validate file path to prevent path traversal attacks.

    Args:
        file_path: Path to validate
        operation: "read" or "write"

    Returns:
        (is_valid, error_message, resolved_path) tuple
    """
    try:
        path = Path(file_path).expanduser().resolve()

        # Check if path is within allowed directories
        allowed = False
        for allowed_dir in ALLOWED_FILE_DIRECTORIES:
            allowed_dir = allowed_dir.resolve()
            try:
                path.relative_to(allowed_dir)
                allowed = True
                break
            except ValueError:
                continue

        if not allowed:
            allowed_str = ", ".join(str(d) for d in ALLOWED_FILE_DIRECTORIES)
            return False, f"Access denied. File must be within allowed directories: {allowed_str}", None

        # Additional checks for read operations
        if operation == "read":
            # Block sensitive files
            sensitive_patterns = [
                r'\.ssh',
                r'\.aws',
                r'\.env',
                r'id_rsa',
                r'password',
                r'secret',
                r'/etc/',
                r'\.key$',
            ]

            path_str = str(path).lower()
            for pattern in sensitive_patterns:
                if re.search(pattern, path_str):
                    return False, f"Access to sensitive files blocked: {pattern}", None

        return True, None, path

    except Exception as e:
        return False, f"Invalid file path: {str(e)}", None


def _convert_to_async_url(connection_string: str) -> str:
    """
    Convert standard database URL to async version.

    Args:
        connection_string: Standard database URL

    Returns:
        Async-compatible database URL
    """
    if connection_string.startswith("sqlite:///"):
        # SQLite: sqlite:/// -> sqlite+aiosqlite:///
        return connection_string.replace("sqlite:///", "sqlite+aiosqlite:///")
    elif connection_string.startswith("postgresql://"):
        # PostgreSQL: postgresql:// -> postgresql+asyncpg://
        return connection_string.replace("postgresql://", "postgresql+asyncpg://")
    elif connection_string.startswith("mysql://"):
        # MySQL: mysql:// -> mysql+aiomysql://
        return connection_string.replace("mysql://", "mysql+aiomysql://")
    else:
        raise ValueError(f"Unsupported database type: {connection_string}")


async def _get_connection_pool(connection_string: str) -> AsyncEngine:
    """
    Get or create a connection pool for the given database.

    Uses caching to reuse pools across multiple queries.

    Args:
        connection_string: Database connection string

    Returns:
        SQLAlchemy AsyncEngine with connection pooling
    """
    # Check if pool already exists
    if connection_string in _connection_pools:
        return _connection_pools[connection_string]

    # Convert to async URL
    async_url = _convert_to_async_url(connection_string)

    # Create async engine with connection pooling
    engine = create_async_engine(
        async_url,
        poolclass=pool.QueuePool,
        pool_size=POOL_SIZE,
        max_overflow=MAX_OVERFLOW,
        pool_timeout=POOL_TIMEOUT,
        pool_recycle=POOL_RECYCLE,
        echo=False,  # Set to True for SQL debugging
    )

    # Cache the pool
    _connection_pools[connection_string] = engine

    return engine


class DatabaseTool:
    """
    Database connection and query tool.

    Supports SQLite, PostgreSQL, MySQL with connection string configuration.
    """

    def __init__(self, connection_string: str = None):
        """
        Initialize database connection.

        Args:
            connection_string: Database connection string
                - SQLite: "sqlite:///path/to/db.sqlite"
                - PostgreSQL: "postgresql://user:pass@host:port/db"
                - MySQL: "mysql://user:pass@host:port/db"
        """
        self.connection_string = connection_string or os.getenv("DATABASE_URL")
        self.conn = None
        self.db_type = None

        if self.connection_string:
            self._parse_connection_string()

    def _parse_connection_string(self):
        """Parse connection string to determine database type."""
        if self.connection_string.startswith("sqlite"):
            self.db_type = "sqlite"
        elif self.connection_string.startswith("postgresql"):
            self.db_type = "postgresql"
        elif self.connection_string.startswith("mysql"):
            self.db_type = "mysql"
        else:
            raise ValueError(f"Unsupported database type in: {self.connection_string}")

    def connect(self) -> bool:
        """
        Establish database connection.

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.db_type == "sqlite":
                # Extract path from sqlite:///path/to/db
                db_path = self.connection_string.replace("sqlite:///", "")
                self.conn = sqlite3.connect(db_path)
                self.conn.row_factory = sqlite3.Row  # Enable dict-like access
                return True

            elif self.db_type == "postgresql":
                import psycopg2
                import psycopg2.extras
                self.conn = psycopg2.connect(self.connection_string)
                return True

            elif self.db_type == "mysql":
                import mysql.connector
                # Parse connection string for mysql.connector
                # This is simplified - in production use proper parsing
                self.conn = mysql.connector.connect(self.connection_string)
                return True

        except Exception as e:
            print(f"Database connection error: {e}")
            return False

    def execute_query(self, query: str, params: tuple = None) -> Dict[str, Any]:
        """
        Execute a SQL query with security validation.

        Args:
            query: SQL query string
            params: Optional query parameters (for prepared statements)

        Returns:
            Dictionary with results or error info
        """
        # Security: Validate query before execution
        is_valid, error_msg, query_type = _validate_sql_query(query)
        if not is_valid:
            return {
                "success": False,
                "error": f"Query validation failed: {error_msg}",
                "query": query[:100]  # Only return first 100 chars for security
            }

        if not self.conn:
            if not self.connect():
                return {"error": "Failed to connect to database"}

        try:
            cursor = self.conn.cursor()

            # Set query timeout for SQLite
            if self.db_type == "sqlite":
                self.conn.execute(f"PRAGMA busy_timeout = {QUERY_TIMEOUT * 1000}")

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Determine if this is a SELECT query or modification
            query_type_str = query_type.value

            if query_type == QueryType.SELECT:
                # Fetch all results
                if self.db_type == "sqlite":
                    rows = cursor.fetchall()
                    # Convert Row objects to dicts
                    results = [dict(row) for row in rows]
                else:
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    results = [dict(zip(columns, row)) for row in rows]

                return {
                    "success": True,
                    "row_count": len(results),
                    "results": results
                }

            else:
                # For INSERT, UPDATE, DELETE
                self.conn.commit()

                # Log DELETE operations for audit
                if query_type == QueryType.DELETE:
                    print(f"⚠️  DELETE operation executed: affected {cursor.rowcount} rows")

                return {
                    "success": True,
                    "affected_rows": cursor.rowcount,
                    "message": f"{query_type_str} completed successfully"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query": query
            }

        finally:
            if cursor:
                cursor.close()

    def list_tables(self) -> List[str]:
        """
        List all tables in the database.

        Returns:
            List of table names
        """
        if self.db_type == "sqlite":
            query = "SELECT name FROM sqlite_master WHERE type='table'"
        elif self.db_type == "postgresql":
            query = "SELECT tablename FROM pg_tables WHERE schemaname='public'"
        elif self.db_type == "mysql":
            query = "SHOW TABLES"
        else:
            return []

        result = self.execute_query(query)
        if result.get("success"):
            if self.db_type == "sqlite":
                return [row["name"] for row in result["results"]]
            else:
                return [list(row.values())[0] for row in result["results"]]
        return []

    def describe_table(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get schema information for a table.

        Args:
            table_name: Name of the table

        Returns:
            List of column information dictionaries
        """
        if self.db_type == "sqlite":
            query = f"PRAGMA table_info({table_name})"
        elif self.db_type == "postgresql":
            query = f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
            """
        elif self.db_type == "mysql":
            query = f"DESCRIBE {table_name}"
        else:
            return []

        result = self.execute_query(query)
        if result.get("success"):
            return result["results"]
        return []

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None


# Tool Functions (for AutoGen FunctionTool integration)

async def query_database(
    query: str,
    connection_string: str = None,
    params: tuple = None
) -> dict:
    """
    Execute a SQL query on the configured database with connection pooling.

    Args:
        query: SQL query to execute
        connection_string: Optional database connection string
        params: Optional query parameters

    Returns:
        Query results or error information

    Example:
        await query_database("SELECT * FROM users WHERE age > ?", params=(25,))
    """
    # Security: Validate query before execution
    is_valid, error_msg, query_type = _validate_sql_query(query)
    if not is_valid:
        return {
            "success": False,
            "error": f"Query validation failed: {error_msg}",
            "query": query[:100]
        }

    try:
        # Get connection string from environment if not provided
        conn_str = connection_string or os.getenv("DATABASE_URL")
        if not conn_str:
            return {"success": False, "error": "No database connection string provided"}

        # Get connection pool
        engine = await _get_connection_pool(conn_str)

        # Execute query with timeout
        async with asyncio.timeout(QUERY_TIMEOUT):
            async with engine.begin() as conn:
                # Convert params to dict for SQLAlchemy if needed
                if params:
                    # SQLAlchemy uses :param syntax, but we'll use positional
                    result = await conn.execute(text(query), params if isinstance(params, dict) else {})
                else:
                    result = await conn.execute(text(query))

                if query_type == QueryType.SELECT:
                    # Fetch results
                    rows = result.fetchall()
                    # Convert to list of dicts
                    results = [dict(row._mapping) for row in rows]

                    return {
                        "success": True,
                        "row_count": len(results),
                        "results": results
                    }
                else:
                    # For INSERT, UPDATE, DELETE
                    # Log DELETE operations
                    if query_type == QueryType.DELETE:
                        print(f"⚠️  DELETE operation executed: affected {result.rowcount} rows")

                    return {
                        "success": True,
                        "affected_rows": result.rowcount,
                        "message": f"{query_type.value} completed successfully"
                    }

    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": f"Query timed out after {QUERY_TIMEOUT} seconds",
            "query": query[:100]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "query": query[:100]
        }


async def list_database_tables(connection_string: str = None) -> dict:
    """
    List all tables in the database using connection pooling.

    Args:
        connection_string: Optional database connection string

    Returns:
        Dictionary with list of table names
    """
    try:
        # Get connection string from environment if not provided
        conn_str = connection_string or os.getenv("DATABASE_URL")
        if not conn_str:
            return {"success": False, "error": "No database connection string provided"}

        # Determine database type
        if "sqlite" in conn_str:
            query = "SELECT name FROM sqlite_master WHERE type='table'"
        elif "postgresql" in conn_str:
            query = "SELECT tablename FROM pg_tables WHERE schemaname='public'"
        elif "mysql" in conn_str:
            query = "SHOW TABLES"
        else:
            return {"success": False, "error": "Unsupported database type"}

        # Use query_database to leverage connection pooling
        result = await query_database(query, conn_str)

        if result.get("success"):
            tables = [list(row.values())[0] for row in result["results"]]
            return {"success": True, "tables": tables, "count": len(tables)}
        else:
            return result

    except Exception as e:
        return {"success": False, "error": str(e)}


async def describe_database_table(table_name: str, connection_string: str = None) -> dict:
    """
    Get schema information for a database table using connection pooling.

    Args:
        table_name: Name of the table to describe
        connection_string: Optional database connection string

    Returns:
        Table schema information
    """
    try:
        # Get connection string from environment if not provided
        conn_str = connection_string or os.getenv("DATABASE_URL")
        if not conn_str:
            return {"success": False, "error": "No database connection string provided"}

        # Determine database type and build query
        if "sqlite" in conn_str:
            query = f"PRAGMA table_info({table_name})"
        elif "postgresql" in conn_str:
            query = f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
            """
        elif "mysql" in conn_str:
            query = f"DESCRIBE {table_name}"
        else:
            return {"success": False, "error": "Unsupported database type"}

        # Use query_database to leverage connection pooling
        result = await query_database(query, conn_str)

        if result.get("success"):
            return {"success": True, "table": table_name, "schema": result["results"]}
        else:
            return result

    except Exception as e:
        return {"success": False, "error": str(e), "table": table_name}


async def read_file(file_path: str, encoding: str = "utf-8") -> dict:
    """
    Read contents of a text file with path traversal protection.

    Args:
        file_path: Path to the file
        encoding: File encoding (default: utf-8)

    Returns:
        Dictionary with file contents or error

    Example:
        await read_file("/path/to/config.json")
    """
    try:
        # Security: Validate file path
        is_valid, error_msg, path = _validate_file_path(file_path, operation="read")
        if not is_valid:
            return {"success": False, "error": error_msg, "file_path": file_path}

        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        if not path.is_file():
            return {"error": f"Not a file: {file_path}"}

        content = path.read_text(encoding=encoding)

        return {
            "success": True,
            "file_path": str(path),
            "content": content,
            "size_bytes": path.stat().st_size,
            "lines": len(content.splitlines())
        }

    except Exception as e:
        return {"error": str(e), "file_path": file_path}


async def read_csv(file_path: str, max_rows: int = 1000) -> dict:
    """
    Read and parse a CSV file with path validation.

    Args:
        file_path: Path to the CSV file
        max_rows: Maximum number of rows to read (default: 1000)

    Returns:
        Dictionary with CSV data

    Example:
        await read_csv("/path/to/data.csv", max_rows=100)
    """
    try:
        # Security: Validate file path
        is_valid, error_msg, path = _validate_file_path(file_path, operation="read")
        if not is_valid:
            return {"success": False, "error": error_msg, "file_path": file_path}

        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        rows = []
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames

            for i, row in enumerate(reader):
                if i >= max_rows:
                    break
                rows.append(row)

        return {
            "success": True,
            "file_path": str(path),
            "headers": headers,
            "rows": rows,
            "row_count": len(rows),
            "truncated": len(rows) == max_rows
        }

    except Exception as e:
        return {"error": str(e), "file_path": file_path}


async def list_directory(directory_path: str, pattern: str = "*") -> dict:
    """
    List files in a directory with optional pattern matching.

    Args:
        directory_path: Path to the directory
        pattern: Glob pattern to filter files (default: "*" for all)

    Returns:
        Dictionary with file listings

    Example:
        await list_directory("/path/to/data", pattern="*.csv")
    """
    try:
        path = Path(directory_path).expanduser()

        if not path.exists():
            return {"error": f"Directory not found: {directory_path}"}

        if not path.is_dir():
            return {"error": f"Not a directory: {directory_path}"}

        files = []
        directories = []

        for item in path.glob(pattern):
            info = {
                "name": item.name,
                "path": str(item),
                "size": item.stat().st_size if item.is_file() else None
            }

            if item.is_file():
                files.append(info)
            elif item.is_dir():
                directories.append(info)

        return {
            "success": True,
            "directory": str(path),
            "pattern": pattern,
            "files": files,
            "directories": directories,
            "file_count": len(files),
            "directory_count": len(directories)
        }

    except Exception as e:
        return {"error": str(e), "directory_path": directory_path}


async def write_file(file_path: str, content: str, overwrite: bool = False) -> dict:
    """
    Write content to a file with path validation and safe permissions.

    Args:
        file_path: Path to the file
        content: Content to write
        overwrite: Whether to overwrite if file exists (default: False)

    Returns:
        Success/error information

    Example:
        await write_file("/path/to/output.txt", "Hello World", overwrite=True)
    """
    try:
        # Security: Validate file path
        is_valid, error_msg, path = _validate_file_path(file_path, operation="write")
        if not is_valid:
            return {"success": False, "error": error_msg, "file_path": file_path}

        if path.exists() and not overwrite:
            return {
                "error": "File already exists. Set overwrite=True to replace it.",
                "file_path": str(path)
            }

        # Create parent directories with safe permissions
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

        # Write file with safe permissions
        path.write_text(content, encoding='utf-8')
        path.chmod(0o600)  # Owner read/write only

        return {
            "success": True,
            "file_path": str(path),
            "bytes_written": len(content.encode('utf-8'))
        }

    except Exception as e:
        return {"error": str(e), "file_path": file_path}


async def write_csv(file_path: str, data: List[Dict[str, Any]], overwrite: bool = False) -> dict:
    """
    Write data to a CSV file with path validation.

    Args:
        file_path: Path to the CSV file
        data: List of dictionaries (each dict is a row)
        overwrite: Whether to overwrite if file exists (default: False)

    Returns:
        Success/error information

    Example:
        await write_csv("/path/to/output.csv", [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25}
        ])
    """
    try:
        # Security: Validate file path
        is_valid, error_msg, path = _validate_file_path(file_path, operation="write")
        if not is_valid:
            return {"success": False, "error": error_msg, "file_path": file_path}

        if path.exists() and not overwrite:
            return {
                "error": "File already exists. Set overwrite=True to replace it.",
                "file_path": str(path)
            }

        if not data:
            return {"error": "No data provided"}

        # Create parent directories with safe permissions
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

        # Get headers from first row
        headers = list(data[0].keys())

        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)

        # Set safe file permissions
        path.chmod(0o600)

        return {
            "success": True,
            "file_path": str(path),
            "rows_written": len(data),
            "columns": headers
        }

    except Exception as e:
        return {"error": str(e), "file_path": file_path}

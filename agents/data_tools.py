"""
Data Access Tools for AutoGen CLI Agent

Provides database connectivity, file reading, and CSV parsing capabilities.
"""

import os
import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
import sqlite3


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
        Execute a SQL query.

        Args:
            query: SQL query string
            params: Optional query parameters (for prepared statements)

        Returns:
            Dictionary with results or error info
        """
        if not self.conn:
            if not self.connect():
                return {"error": "Failed to connect to database"}

        try:
            cursor = self.conn.cursor()

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Determine if this is a SELECT query or modification
            query_type = query.strip().upper().split()[0]

            if query_type == "SELECT":
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
                return {
                    "success": True,
                    "affected_rows": cursor.rowcount,
                    "message": f"{query_type} completed successfully"
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
    Execute a SQL query on the configured database.

    Args:
        query: SQL query to execute
        connection_string: Optional database connection string
        params: Optional query parameters

    Returns:
        Query results or error information

    Example:
        await query_database("SELECT * FROM users WHERE age > ?", params=(25,))
    """
    db = DatabaseTool(connection_string)
    result = db.execute_query(query, params)
    db.close()
    return result


async def list_database_tables(connection_string: str = None) -> dict:
    """
    List all tables in the database.

    Args:
        connection_string: Optional database connection string

    Returns:
        Dictionary with list of table names
    """
    db = DatabaseTool(connection_string)
    db.connect()
    tables = db.list_tables()
    db.close()
    return {"tables": tables, "count": len(tables)}


async def describe_database_table(table_name: str, connection_string: str = None) -> dict:
    """
    Get schema information for a database table.

    Args:
        table_name: Name of the table to describe
        connection_string: Optional database connection string

    Returns:
        Table schema information
    """
    db = DatabaseTool(connection_string)
    db.connect()
    schema = db.describe_table(table_name)
    db.close()
    return {"table": table_name, "schema": schema}


async def read_file(file_path: str, encoding: str = "utf-8") -> dict:
    """
    Read contents of a text file.

    Args:
        file_path: Path to the file
        encoding: File encoding (default: utf-8)

    Returns:
        Dictionary with file contents or error

    Example:
        await read_file("/path/to/config.json")
    """
    try:
        path = Path(file_path).expanduser()

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
    Read and parse a CSV file.

    Args:
        file_path: Path to the CSV file
        max_rows: Maximum number of rows to read (default: 1000)

    Returns:
        Dictionary with CSV data

    Example:
        await read_csv("/path/to/data.csv", max_rows=100)
    """
    try:
        path = Path(file_path).expanduser()

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
    Write content to a file.

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
        path = Path(file_path).expanduser()

        if path.exists() and not overwrite:
            return {
                "error": "File already exists. Set overwrite=True to replace it.",
                "file_path": str(path)
            }

        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        path.write_text(content, encoding='utf-8')

        return {
            "success": True,
            "file_path": str(path),
            "bytes_written": len(content.encode('utf-8'))
        }

    except Exception as e:
        return {"error": str(e), "file_path": file_path}


async def write_csv(file_path: str, data: List[Dict[str, Any]], overwrite: bool = False) -> dict:
    """
    Write data to a CSV file.

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
        path = Path(file_path).expanduser()

        if path.exists() and not overwrite:
            return {
                "error": "File already exists. Set overwrite=True to replace it.",
                "file_path": str(path)
            }

        if not data:
            return {"error": "No data provided"}

        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        # Get headers from first row
        headers = list(data[0].keys())

        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)

        return {
            "success": True,
            "file_path": str(path),
            "rows_written": len(data),
            "columns": headers
        }

    except Exception as e:
        return {"error": str(e), "file_path": file_path}

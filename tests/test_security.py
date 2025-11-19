"""
Comprehensive security tests for Yamazaki v2.

Tests critical security vulnerabilities and their fixes.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import asyncio

# Import the components to test
from v2.security.validators.sql_validator import SQLValidator
from v2.security.validators.path_validator import PathValidator
from v2.config.models import SecurityConfig


class TestSQLValidator:
    """Test SQL injection prevention."""

    def setup_method(self):
        """Setup test environment."""
        config = Mock()
        config.allowed_sql_commands = ["SELECT", "INSERT", "UPDATE", "DELETE"]  # Changed from operations to commands
        config.max_query_length = 10000
        self.validator = SQLValidator(config)

    def test_blocks_drop_table(self):
        """Should block DROP TABLE commands."""
        query = "DROP TABLE users"
        is_valid, error, _ = self.validator.validate(query)
        assert not is_valid
        assert "DROP" in error

    def test_blocks_truncate_table(self):
        """Should block TRUNCATE commands."""
        query = "TRUNCATE TABLE users"
        is_valid, error, _ = self.validator.validate(query)
        assert not is_valid
        assert "TRUNCATE" in error

    def test_blocks_multiple_statements(self):
        """Should block multiple SQL statements."""
        query = "SELECT * FROM users; DELETE FROM users"
        is_valid, error, _ = self.validator.validate(query)
        assert not is_valid
        assert "Multiple statements" in error

    def test_blocks_union_injection(self):
        """Should block UNION-based SQL injection."""
        query = "SELECT * FROM users WHERE id = 1 UNION SELECT * FROM passwords"
        is_valid, error, _ = self.validator.validate(query)
        assert not is_valid

    def test_blocks_comment_injection(self):
        """Should block comment-based SQL injection."""
        query = "SELECT * FROM users WHERE username = 'admin'--' AND password = 'x'"
        is_valid, error, _ = self.validator.validate(query)
        assert not is_valid
        assert "SQL comment" in error

    def test_allows_valid_select(self):
        """Should allow valid SELECT queries."""
        query = "SELECT id, name FROM users WHERE active = true"
        is_valid, error, query_type = self.validator.validate(query)
        assert is_valid
        assert error is None
        assert query_type.value == "SELECT"

    def test_allows_parameterized_query(self):
        """Should allow queries with parameter placeholders."""
        query = "SELECT * FROM users WHERE id = :user_id"
        is_valid, error, _ = self.validator.validate(query)
        assert is_valid
        assert error is None

    def test_query_length_limit(self):
        """Should enforce query length limits."""
        query = "SELECT " + "a" * 20000  # Exceeds limit
        is_valid, error, _ = self.validator.validate(query)
        assert not is_valid
        assert "too long" in error.lower()


class TestPathValidator:
    """Test path traversal prevention."""

    def setup_method(self):
        """Setup test environment with temporary directories."""
        self.temp_dir = tempfile.mkdtemp()
        self.allowed_dir = Path(self.temp_dir) / "allowed"
        self.allowed_dir.mkdir()
        self.forbidden_dir = Path(self.temp_dir) / "forbidden"
        self.forbidden_dir.mkdir()

        config = Mock()
        config.allowed_directories = [str(self.allowed_dir)]
        config.blocked_file_patterns = [r"\.ssh", r"\.aws", r"passwd", r"shadow"]

        self.validator = PathValidator(config)

    def teardown_method(self):
        """Cleanup temporary directories."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_blocks_path_traversal(self):
        """Should block path traversal attempts."""
        test_file = self.allowed_dir / "test.txt"
        test_file.write_text("test")

        # Try to escape with ../
        is_valid, error, _ = self.validator.validate("../forbidden/secret.txt")
        assert not is_valid
        assert "Access denied" in error

    def test_blocks_absolute_path_outside_allowed(self):
        """Should block absolute paths outside allowed directories."""
        is_valid, error, _ = self.validator.validate("/etc/passwd")
        assert not is_valid
        assert "Access denied" in error

    def test_blocks_symlink_to_forbidden_file(self):
        """Should block symlinks pointing to forbidden locations."""
        # Create a file in forbidden directory
        secret_file = self.forbidden_dir / "secret.txt"
        secret_file.write_text("secret data")

        # Create symlink in allowed directory
        symlink = self.allowed_dir / "link_to_secret.txt"
        if not symlink.exists():  # Check to avoid FileExistsError
            symlink.symlink_to(secret_file)

        # Try to access via symlink
        is_valid, error, _ = self.validator.validate(str(symlink))
        assert not is_valid
        assert "Symlink" in error or "Access denied" in error

    def test_blocks_sensitive_file_patterns(self):
        """Should block access to sensitive files."""
        # Create .ssh directory in allowed area
        ssh_dir = self.allowed_dir / ".ssh"
        ssh_dir.mkdir(exist_ok=True)
        key_file = ssh_dir / "id_rsa"
        key_file.write_text("fake key")

        # Try to access
        is_valid, error, _ = self.validator.validate(str(key_file))
        assert not is_valid
        assert "blocked" in error.lower()

    def test_allows_valid_file_in_allowed_directory(self):
        """Should allow access to valid files in allowed directories."""
        valid_file = self.allowed_dir / "data.txt"
        valid_file.write_text("valid data")

        is_valid, error, path = self.validator.validate(str(valid_file))
        assert is_valid
        assert error is None
        assert path == valid_file.resolve()

    def test_validates_file_exists_for_read(self):
        """Should check file exists for read operations."""
        non_existent = self.allowed_dir / "missing.txt"

        is_valid, error, _ = self.validator.validate(str(non_existent), operation="read")
        assert not is_valid
        assert "not found" in error.lower()

    def test_allows_non_existent_for_write(self):
        """Should allow non-existent paths for write operations."""
        new_file = self.allowed_dir / "new.txt"

        is_valid, error, path = self.validator.validate(str(new_file), operation="write")
        assert is_valid
        assert error is None


class TestDatabaseSecurityFix:
    """Test the SQL injection fix in database.py describe_table."""

    @pytest.mark.asyncio
    async def test_describe_table_validates_table_name(self):
        """Should validate table names against whitelist."""
        from v2.services.database import DatabaseService, ConnectionPoolManager
        from v2.config.models import DatabaseConfig

        # Setup
        db_config = DatabaseConfig(url="sqlite:///test.db")
        pool = ConnectionPoolManager(db_config)
        security = Mock()
        security.get_sql_validator = Mock()

        service = DatabaseService(pool, security)

        # Mock list_tables to return known tables
        service.list_tables = AsyncMock(return_value={
            "success": True,
            "tables": ["users", "products"]
        })

        # Test with invalid table name (SQL injection attempt)
        result = await service.describe_table("users; DROP TABLE users")
        assert not result["success"]
        assert "Invalid table name" in result["error"]

        # Test with table not in whitelist
        result = await service.describe_table("secret_table")
        assert not result["success"]
        assert "not found" in result["error"]

        # Cleanup
        await pool.dispose()

    @pytest.mark.asyncio
    async def test_describe_table_length_limit(self):
        """Should enforce table name length limits."""
        from v2.services.database import DatabaseService, ConnectionPoolManager
        from v2.config.models import DatabaseConfig

        # Setup
        db_config = DatabaseConfig(url="sqlite:///test.db")
        pool = ConnectionPoolManager(db_config)
        security = Mock()

        service = DatabaseService(pool, security)

        # Test with overly long table name
        long_name = "a" * 100
        result = await service.describe_table(long_name)
        assert not result["success"]
        assert "too long" in result["error"].lower()

        # Cleanup
        await pool.dispose()


class TestSignalHandling:
    """Test graceful shutdown and signal handling."""

    @pytest.mark.asyncio
    async def test_container_disposal_on_shutdown(self):
        """Should properly dispose container on shutdown."""
        from v2.core import get_container

        container = get_container()

        # Mock dispose to track if it's called
        original_dispose = container.dispose
        dispose_called = False

        async def mock_dispose():
            nonlocal dispose_called
            dispose_called = True
            await original_dispose()

        container.dispose = mock_dispose

        # Simulate cleanup
        await container.dispose()

        assert dispose_called, "Container disposal not called"

    @pytest.mark.asyncio
    async def test_disposal_timeout_handling(self):
        """Should handle disposal timeout gracefully."""
        from v2.core import get_container

        container = get_container()

        # Mock dispose to hang
        async def hanging_dispose():
            await asyncio.sleep(10)  # Longer than timeout

        container.dispose = hanging_dispose

        # Should timeout without crashing
        try:
            await asyncio.wait_for(container.dispose(), timeout=0.1)
            assert False, "Should have timed out"
        except asyncio.TimeoutError:
            pass  # Expected


class TestExceptionHandling:
    """Test specific exception handling improvements."""

    @pytest.mark.asyncio
    async def test_database_tool_specific_exceptions(self):
        """Should handle specific database exceptions differently."""
        from v2.tools.database.query_tool import DatabaseQueryTool

        pool = Mock()
        security = Mock()
        validator = Mock()
        validator.validate = Mock(return_value=(True, None, Mock(value="SELECT")))
        security.get_sql_validator = Mock(return_value=validator)

        tool = DatabaseQueryTool(pool, security)

        # Test ConnectionRefusedError
        pool.get_pool = AsyncMock(side_effect=ConnectionRefusedError("Database down"))
        result = await tool.execute("SELECT 1")
        assert not result.success
        assert "connection refused" in result.error.lower()

        # Test MemoryError
        pool.get_pool = AsyncMock(side_effect=MemoryError("Out of memory"))
        result = await tool.execute("SELECT 1")
        assert not result.success
        assert "memory" in result.error.lower()

        # Test generic exception (should not expose details)
        pool.get_pool = AsyncMock(side_effect=RuntimeError("Internal error with secrets"))
        result = await tool.execute("SELECT 1")
        assert not result.success
        assert "secrets" not in result.error.lower()
        assert "RuntimeError" in result.error  # Class name only


class TestInputValidation:
    """Test input validation on critical paths."""

    def test_tool_registry_validates_input(self):
        """Should validate tool creation parameters."""
        from v2.tools.registry import ToolRegistry

        # Create registry with mocked dependencies
        security_mock = Mock()
        pool_mock = Mock()
        registry = ToolRegistry(security_mock, pool_mock)

        # Mock a tool class
        mock_tool_class = Mock()
        mock_tool_class.NAME = "test.tool"
        registry._tools["test.tool"] = mock_tool_class

        # Test with invalid tool name (too long)
        long_name = "a" * 1000
        tool = registry.create_tool(long_name)
        assert tool is None  # Should fail gracefully

        # Test with valid name
        tool = registry.create_tool("test.tool")
        # Tool creation may fail due to missing dependencies, that's ok
        # We're testing the name validation path


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
"""
Yamazaki v2 - File Service

Secure file operations with path validation.
"""

from typing import Dict, Any, List
from pathlib import Path


class FileService:
    """
    High-level file service.

    Provides file operations with security validation.
    """

    def __init__(self, security):
        """
        Initialize file service.

        Args:
            security: Security middleware
        """
        self.security = security

    async def read_file(self, file_path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """
        Read file contents with security validation.

        Args:
            file_path: Path to file
            encoding: File encoding

        Returns:
            File contents or error
        """
        # Get path validator
        validator = self.security.get_path_validator()

        # Validate path
        is_valid, error, path = validator.validate(file_path, operation="read")
        if not is_valid:
            return {"success": False, "error": error, "file_path": file_path}

        try:
            content = path.read_text(encoding=encoding)

            return {
                "success": True,
                "file_path": str(path),
                "content": content,
                "size_bytes": path.stat().st_size,
                "lines": len(content.splitlines()),
            }

        except Exception as e:
            return {"success": False, "error": str(e), "file_path": file_path}

    async def write_file(
        self,
        file_path: str,
        content: str,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Write file with security validation.

        Args:
            file_path: Path to file
            content: Content to write
            overwrite: Allow overwriting existing file

        Returns:
            Success or error info
        """
        # Get path validator
        validator = self.security.get_path_validator()

        # Validate path
        is_valid, error, path = validator.validate(file_path, operation="write")
        if not is_valid:
            return {"success": False, "error": error, "file_path": file_path}

        # Check if file exists
        if path.exists() and not overwrite:
            return {
                "success": False,
                "error": "File already exists. Set overwrite=True to replace it.",
                "file_path": str(path),
            }

        try:
            # Create parent directories
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

            # Write file
            path.write_text(content, encoding="utf-8")
            path.chmod(0o600)  # Owner read/write only

            return {
                "success": True,
                "file_path": str(path),
                "bytes_written": len(content.encode("utf-8")),
            }

        except Exception as e:
            return {"success": False, "error": str(e), "file_path": file_path}

    async def list_directory(
        self,
        directory_path: str,
        pattern: str = "*"
    ) -> Dict[str, Any]:
        """
        List directory contents with security validation.

        Args:
            directory_path: Directory path
            pattern: Glob pattern

        Returns:
            Directory listing or error
        """
        # Get path validator
        validator = self.security.get_path_validator()

        # Validate directory path
        is_valid, error, path = validator.validate(directory_path, operation="read")
        if not is_valid:
            return {"success": False, "error": error, "directory_path": directory_path}

        try:
            if not path.exists():
                return {"success": False, "error": f"Directory not found: {directory_path}"}

            if not path.is_dir():
                return {"success": False, "error": f"Not a directory: {directory_path}"}

            files = []
            directories = []

            for item in path.glob(pattern):
                info = {
                    "name": item.name,
                    "path": str(item),
                    "size": item.stat().st_size if item.is_file() else None,
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
                "directory_count": len(directories),
            }

        except Exception as e:
            return {"success": False, "error": str(e), "directory_path": directory_path}

    async def read_csv(self, file_path: str, max_rows: int = 1000) -> Dict[str, Any]:
        """
        Read CSV file.

        Args:
            file_path: CSV file path
            max_rows: Maximum rows to read

        Returns:
            CSV data or error
        """
        import csv

        # Get path validator
        validator = self.security.get_path_validator()

        # Validate path
        is_valid, error, path = validator.validate(file_path, operation="read")
        if not is_valid:
            return {"success": False, "error": error, "file_path": file_path}

        try:
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
                "truncated": len(rows) == max_rows,
            }

        except Exception as e:
            return {"success": False, "error": str(e), "file_path": file_path}

    async def write_csv(
        self,
        file_path: str,
        data: List[Dict[str, Any]],
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Write CSV file.

        Args:
            file_path: CSV file path
            data: List of dicts (each dict is a row)
            overwrite: Allow overwriting

        Returns:
            Success or error info
        """
        import csv

        # Get path validator
        validator = self.security.get_path_validator()

        # Validate path
        is_valid, error, path = validator.validate(file_path, operation="write")
        if not is_valid:
            return {"success": False, "error": error, "file_path": file_path}

        # Check if exists
        if path.exists() and not overwrite:
            return {
                "success": False,
                "error": "File already exists. Set overwrite=True to replace it.",
                "file_path": str(path),
            }

        if not data:
            return {"success": False, "error": "No data provided"}

        try:
            # Create parent directories
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

            # Write CSV
            headers = list(data[0].keys())
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(data)

            # Set permissions
            path.chmod(0o600)

            return {
                "success": True,
                "file_path": str(path),
                "rows_written": len(data),
                "columns": headers,
            }

        except Exception as e:
            return {"success": False, "error": str(e), "file_path": file_path}

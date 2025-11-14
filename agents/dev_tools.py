"""
Development Tools for AutoGen CLI Agent - V2

Atomic, reusable tools for software development tasks.
Each tool does ONE thing well.
"""

import subprocess
import ast
from pathlib import Path
from typing import Dict, Any, List, Optional


async def read_source_file(file_path: str) -> Dict[str, Any]:
    """
    Read a source code file.

    Args:
        file_path: Path to the file to read

    Returns:
        dict: success, content, lines, file_type
    """
    try:
        path = Path(file_path)

        if not path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}"
            }

        content = path.read_text(encoding='utf-8')
        lines = content.split('\n')

        # Detect file type
        suffix = path.suffix
        file_type_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.md': 'markdown',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
        }
        file_type = file_type_map.get(suffix, 'text')

        return {
            "success": True,
            "content": content,
            "lines": len(lines),
            "file_type": file_type,
            "path": str(path.absolute())
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Error reading file: {str(e)}"
        }


async def write_source_file(file_path: str, content: str, create_backup: bool = True) -> Dict[str, Any]:
    """
    Write content to a source file.

    Args:
        file_path: Path to write to
        content: Content to write
        create_backup: Create .bak file if file exists

    Returns:
        dict: success, path, backup_path
    """
    try:
        path = Path(file_path)

        # Create backup if file exists
        backup_path = None
        if create_backup and path.exists():
            backup_path = path.with_suffix(path.suffix + '.bak')
            backup_path.write_text(path.read_text())

        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        path.write_text(content, encoding='utf-8')

        return {
            "success": True,
            "path": str(path.absolute()),
            "backup_path": str(backup_path) if backup_path else None,
            "bytes_written": len(content.encode('utf-8'))
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Error writing file: {str(e)}"
        }


async def run_tests(test_path: str = "tests/", pattern: str = "test_*.py", verbose: bool = True) -> Dict[str, Any]:
    """
    Run pytest tests.

    Args:
        test_path: Path to tests directory or specific test file
        pattern: Pattern to match test files
        verbose: Show verbose output

    Returns:
        dict: success, passed, failed, output
    """
    try:
        cmd = ["python", "-m", "pytest", test_path]

        if verbose:
            cmd.append("-v")

        if pattern and Path(test_path).is_dir():
            cmd.extend(["-k", pattern])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        output = result.stdout + result.stderr

        # Parse pytest output for results
        passed = 0
        failed = 0
        for line in output.split('\n'):
            if ' passed' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'passed' and i > 0:
                        try:
                            passed = int(parts[i-1])
                        except:
                            pass
            if ' failed' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'failed' and i > 0:
                        try:
                            failed = int(parts[i-1])
                        except:
                            pass

        return {
            "success": result.returncode == 0,
            "passed": passed,
            "failed": failed,
            "exit_code": result.returncode,
            "output": output
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Tests timed out after 60 seconds"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error running tests: {str(e)}"
        }


async def check_syntax(file_path: str) -> Dict[str, Any]:
    """
    Check Python syntax without executing.

    Args:
        file_path: Path to Python file

    Returns:
        dict: valid, errors, ast_nodes
    """
    try:
        path = Path(file_path)

        if not path.exists():
            return {
                "valid": False,
                "error": f"File not found: {file_path}"
            }

        if path.suffix != '.py':
            return {
                "valid": False,
                "error": f"Not a Python file: {file_path}"
            }

        content = path.read_text()

        # Try to parse the AST
        try:
            tree = ast.parse(content, filename=str(path))

            # Count different node types
            node_counts = {}
            for node in ast.walk(tree):
                node_type = type(node).__name__
                node_counts[node_type] = node_counts.get(node_type, 0) + 1

            return {
                "valid": True,
                "file": str(path),
                "node_counts": node_counts,
                "functions": node_counts.get('FunctionDef', 0),
                "classes": node_counts.get('ClassDef', 0),
            }

        except SyntaxError as se:
            return {
                "valid": False,
                "syntax_error": {
                    "message": se.msg,
                    "line": se.lineno,
                    "offset": se.offset,
                    "text": se.text
                }
            }

    except Exception as e:
        return {
            "valid": False,
            "error": f"Error checking syntax: {str(e)}"
        }


async def run_linter(file_path: str, tool: str = "pylint") -> Dict[str, Any]:
    """
    Run a linter on a file.

    Args:
        file_path: Path to file
        tool: Linter to use (pylint, flake8, black --check)

    Returns:
        dict: success, issues, output
    """
    try:
        path = Path(file_path)

        if not path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}"
            }

        # Choose linter command
        if tool == "pylint":
            cmd = ["pylint", str(path), "--output-format=text"]
        elif tool == "flake8":
            cmd = ["flake8", str(path)]
        elif tool == "black":
            cmd = ["black", "--check", str(path)]
        else:
            return {
                "success": False,
                "error": f"Unknown linter: {tool}. Use pylint, flake8, or black"
            }

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        output = result.stdout + result.stderr

        # Count issues (simple heuristic)
        issues = len([line for line in output.split('\n') if line.strip() and not line.startswith('***')])

        return {
            "success": result.returncode == 0,
            "tool": tool,
            "issues_found": issues,
            "output": output,
            "clean": result.returncode == 0 and issues == 0
        }

    except FileNotFoundError:
        return {
            "success": False,
            "error": f"Linter '{tool}' not installed. Install with: pip install {tool}"
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Linter timed out after 30 seconds"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error running linter: {str(e)}"
        }


async def list_files(directory: str = ".", pattern: str = "*.py", recursive: bool = True) -> Dict[str, Any]:
    """
    List files matching a pattern.

    Args:
        directory: Directory to search
        pattern: Glob pattern (e.g., "*.py", "test_*.py")
        recursive: Search subdirectories

    Returns:
        dict: files list with metadata
    """
    try:
        path = Path(directory)

        if not path.exists():
            return {
                "success": False,
                "error": f"Directory not found: {directory}"
            }

        if not path.is_dir():
            return {
                "success": False,
                "error": f"Not a directory: {directory}"
            }

        # Find files
        if recursive:
            files = list(path.rglob(pattern))
        else:
            files = list(path.glob(pattern))

        # Get metadata
        file_info = []
        for f in files:
            try:
                stat = f.stat()
                file_info.append({
                    "path": str(f),
                    "name": f.name,
                    "size": stat.st_size,
                    "lines": len(f.read_text().split('\n')) if f.suffix in ['.py', '.js', '.ts', '.md'] else None
                })
            except:
                file_info.append({
                    "path": str(f),
                    "name": f.name,
                    "error": "Could not read file"
                })

        return {
            "success": True,
            "count": len(file_info),
            "files": file_info,
            "pattern": pattern,
            "directory": str(path.absolute())
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Error listing files: {str(e)}"
        }


async def get_file_structure(directory: str = ".", max_depth: int = 3) -> Dict[str, Any]:
    """
    Get project file structure.

    Args:
        directory: Root directory
        max_depth: Maximum directory depth

    Returns:
        dict: tree structure
    """
    try:
        path = Path(directory)

        if not path.exists():
            return {
                "success": False,
                "error": f"Directory not found: {directory}"
            }

        def build_tree(current_path: Path, depth: int = 0) -> Dict[str, Any]:
            if depth > max_depth:
                return {"truncated": True}

            result = {
                "name": current_path.name or str(current_path),
                "type": "directory" if current_path.is_dir() else "file",
                "path": str(current_path)
            }

            if current_path.is_dir():
                children = []
                try:
                    for child in sorted(current_path.iterdir()):
                        # Skip hidden files and common ignore patterns
                        if child.name.startswith('.') or child.name in ['__pycache__', 'node_modules', 'venv', '.git']:
                            continue
                        children.append(build_tree(child, depth + 1))
                    result["children"] = children
                except PermissionError:
                    result["error"] = "Permission denied"

            return result

        tree = build_tree(path)

        return {
            "success": True,
            "tree": tree,
            "root": str(path.absolute())
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Error getting structure: {str(e)}"
        }

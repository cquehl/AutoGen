# Critical Security Fixes Required for MCP Integration

**Priority**: CRITICAL 🔴
**Before**: Production deployment or merge to main
**Estimated Time**: 1-2 days

---

## Issue #1: Command Injection Vulnerability

### Files to Fix
- `src/core/mcp/client.py:40`
- `src/core/mcp/supervisor.py:~70`

### Current Code
```python
# VULNERABLE
cmd = self.command.split() + self.args
self.process = await asyncio.create_subprocess_exec(*cmd, ...)
```

### Fixed Code
```python
import shlex

# SECURE
cmd = shlex.split(self.command) + self.args

# Add command allowlist
ALLOWED_COMMANDS = {
    "npx", "node", "python3", "python",
    "/usr/bin/npx", "/usr/bin/node"
}

if cmd[0] not in ALLOWED_COMMANDS:
    raise SecurityError(f"Command not in allowlist: {cmd[0]}")

self.process = await asyncio.create_subprocess_exec(*cmd, ...)
```

---

## Issue #2: Environment Variable Injection

### Files to Fix
- `src/core/mcp/client.py:35-37`
- `src/core/mcp/supervisor.py`

### Current Code
```python
# UNSAFE
import os
env = os.environ.copy()
env.update(self.env)  # User-controlled
```

### Fixed Code
```python
import fnmatch

ALLOWED_ENV_VARS = {
    "ALLOWED_DIRECTORIES",
    "GITHUB_TOKEN",
    "DATABASE_URL",
    "CONNECTION_STRING",
    "MCP_*",
    "NODE_*"
}

DANGEROUS_ENV_VARS = {
    "LD_PRELOAD", "LD_LIBRARY_PATH",
    "PYTHONPATH", "PATH",
    "HOME", "USER"
}

def sanitize_env(user_env: Dict[str, str]) -> Dict[str, str]:
    """Validate and sanitize environment variables"""
    safe_env = {}

    for key, value in user_env.items():
        # Block dangerous vars
        if key in DANGEROUS_ENV_VARS:
            raise SecurityError(f"Dangerous env var not allowed: {key}")

        # Check allowlist
        allowed = any(
            fnmatch.fnmatch(key, pattern)
            for pattern in ALLOWED_ENV_VARS
        )
        if not allowed:
            logger.warning(f"Env var not in allowlist: {key}")
            continue

        # Sanitize value
        if any(char in value for char in "&|;`$()<>"):
            raise SecurityError(f"Unsafe characters in env var {key}")

        safe_env[key] = value

    return safe_env

# Use it
safe_env = {
    "PATH": "/usr/bin:/bin",
    "HOME": "/tmp"
}
safe_env.update(sanitize_env(self.env))
```

---

## Issue #3: Path Traversal

### File to Fix
- `src/core/mcp/config.py:74-77`

### Add Validator
```python
@validator('working_directory')
def validate_working_directory(cls, v):
    """Ensure working directory is safe"""
    if v is None:
        return v

    # Resolve to absolute path
    abs_path = os.path.abspath(os.path.expanduser(v))

    # Forbidden directories
    FORBIDDEN_DIRS = [
        "/etc", "/bin", "/sbin", "/root", "/boot",
        "/usr/bin", "/usr/sbin", "/sys", "/proc"
    ]

    # Check if path is in forbidden area
    for forbidden in FORBIDDEN_DIRS:
        if abs_path.startswith(forbidden):
            raise ValueError(
                f"Working directory not allowed: {abs_path} "
                f"(forbidden: {forbidden})"
            )

    # Ensure directory exists
    if not os.path.isdir(abs_path):
        raise ValueError(f"Working directory does not exist: {abs_path}")

    # Check write permissions
    if not os.access(abs_path, os.W_OK):
        raise ValueError(f"Working directory not writable: {abs_path}")

    return abs_path
```

---

## Issue #4: Insecure Credential Storage

### File to Fix
- `src/core/mcp/config.py:112-115`

### Fixed Code
```python
from pydantic import SecretStr, SecretBytes

class MCPServerConfig(BaseModel):
    # ... other fields ...

    authentication: Optional[Dict[str, SecretStr]] = Field(
        None,
        description="Authentication credentials (stored securely)"
    )

    def dict(self, **kwargs):
        """Override dict to redact secrets"""
        d = super().dict(**kwargs)
        if d.get("authentication"):
            d["authentication"] = {
                k: "***REDACTED***"
                for k in d["authentication"].keys()
            }
        return d

    def __repr__(self):
        """Redact secrets from repr"""
        d = self.dict()
        if d.get("authentication"):
            d["authentication"] = "***REDACTED***"
        if d.get("env") and "TOKEN" in str(d["env"]):
            d["env"] = {
                k: ("***REDACTED***" if "TOKEN" in k.upper() or "KEY" in k.upper() else v)
                for k, v in d["env"].items()
            }
        return f"MCPServerConfig({d})"
```

### Also Add to Logger
```python
# In telemetry.py or wherever logging is configured
import logging

class SanitizingFormatter(logging.Formatter):
    """Formatter that sanitizes sensitive data"""

    SENSITIVE_PATTERNS = [
        (r'(token["\']?\s*[:=]\s*["\']?)([^"\'}\s]+)', r'\1***REDACTED***'),
        (r'(password["\']?\s*[:=]\s*["\']?)([^"\'}\s]+)', r'\1***REDACTED***'),
        (r'(api[_-]?key["\']?\s*[:=]\s*["\']?)([^"\'}\s]+)', r'\1***REDACTED***'),
    ]

    def format(self, record):
        msg = super().format(record)
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            msg = re.sub(pattern, replacement, msg, flags=re.IGNORECASE)
        return msg
```

---

## Testing the Fixes

### Create Security Test File
`tests/test_mcp_security.py`:

```python
import pytest
from src.core.mcp import MCPServerConfig, ServerType, TransportType
from src.core.mcp.client import StdioTransport, sanitize_env
from src.core.errors import SuntoryError

class TestCommandInjection:
    """Test command injection protection"""

    def test_malicious_command_blocked(self):
        """Malicious commands should be rejected"""
        config = MCPServerConfig(
            name="malicious",
            type=ServerType.CUSTOM,
            transport=TransportType.STDIO,
            command="npx; rm -rf /"  # Attack attempt
        )

        transport = StdioTransport(
            command=config.command,
            env=config.env
        )

        with pytest.raises(SecurityError):
            asyncio.run(transport.connect())


class TestEnvironmentInjection:
    """Test environment variable injection protection"""

    def test_dangerous_env_vars_blocked(self):
        """Dangerous env vars should be rejected"""
        dangerous_envs = {
            "LD_PRELOAD": "/tmp/evil.so",
            "PATH": "/tmp/evil:/usr/bin",
            "PYTHONPATH": "/tmp/evil"
        }

        with pytest.raises(SecurityError):
            sanitize_env(dangerous_envs)

    def test_shell_metacharacters_blocked(self):
        """Shell metacharacters in values should be rejected"""
        malicious_env = {
            "ALLOWED_DIRECTORIES": "/tmp; rm -rf /"
        }

        with pytest.raises(SecurityError):
            sanitize_env(malicious_env)


class TestPathTraversal:
    """Test path traversal protection"""

    def test_forbidden_directory_blocked(self):
        """Forbidden directories should be rejected"""
        with pytest.raises(ValueError):
            MCPServerConfig(
                name="evil",
                type=ServerType.FILESYSTEM,
                transport=TransportType.STDIO,
                command="npx test",
                working_directory="/etc"  # Forbidden
            )

    def test_path_traversal_blocked(self):
        """Path traversal attempts should be blocked"""
        with pytest.raises(ValueError):
            MCPServerConfig(
                name="evil",
                type=ServerType.FILESYSTEM,
                transport=TransportType.STDIO,
                command="npx test",
                working_directory="/tmp/../../../etc"
            )


class TestCredentialProtection:
    """Test credential protection"""

    def test_credentials_redacted_in_logs(self):
        """Credentials should not appear in logs"""
        config = MCPServerConfig(
            name="test",
            type=ServerType.GITHUB,
            transport=TransportType.STDIO,
            command="npx test",
            env={"GITHUB_TOKEN": "secret_token_123"}
        )

        # Check string representation
        repr_str = repr(config)
        assert "secret_token_123" not in repr_str
        assert "REDACTED" in repr_str

    def test_credentials_redacted_in_dict(self):
        """Credentials should not appear in dict"""
        config = MCPServerConfig(
            name="test",
            type=ServerType.GITHUB,
            transport=TransportType.STDIO,
            command="npx test",
            authentication={"token": "secret_123"}
        )

        config_dict = config.dict()
        assert "secret_123" not in str(config_dict)
        assert "REDACTED" in str(config_dict)
```

### Run Security Tests
```bash
cd v3
pytest tests/test_mcp_security.py -v
```

---

## Verification Checklist

- [ ] Command injection vulnerability fixed
- [ ] Environment variable validation implemented
- [ ] Path traversal protection added
- [ ] Credential redaction implemented
- [ ] All security tests pass
- [ ] Manual penetration testing performed
- [ ] Code review by security expert
- [ ] Documentation updated

---

## Additional Hardening (Recommended)

### 1. Add Resource Limits
```python
# In supervisor.py
import resource

def set_resource_limits():
    """Set conservative resource limits for MCP servers"""
    # Limit CPU time (10 minutes)
    resource.setrlimit(resource.RLIMIT_CPU, (600, 600))

    # Limit memory (1GB)
    resource.setrlimit(resource.RLIMIT_AS, (1024*1024*1024, 1024*1024*1024))

    # Limit file descriptors (1024)
    resource.setrlimit(resource.RLIMIT_NOFILE, (1024, 1024))

# Use before starting subprocess
```

### 2. Implement Sandboxing
```python
# Consider using Docker or similar for isolation
async def start_server_sandboxed(config: MCPServerConfig):
    """Start MCP server in sandboxed environment"""
    if config.docker_enabled:
        # Run in Docker container
        cmd = [
            "docker", "run",
            "--rm",
            "--network=none",  # No network access
            "--memory=1g",     # Memory limit
            "--cpus=1",        # CPU limit
            "--read-only",     # Read-only filesystem
            "mcp-server-image",
            config.command
        ]
    else:
        # Regular subprocess with limits
        cmd = shlex.split(config.command)

    # ... rest of startup
```

### 3. Add Audit Logging
```python
def audit_log(event: str, details: Dict[str, Any]):
    """Log security-relevant events"""
    audit_logger = logging.getLogger("security.audit")
    audit_logger.info(
        f"AUDIT: {event}",
        extra={
            "event_type": event,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details
        }
    )

# Use it
audit_log("mcp_server_start", {
    "server": config.name,
    "command": config.command,
    "user": get_current_user()
})
```

---

## Timeline

**Day 1**:
- Morning: Fix command injection (#1)
- Afternoon: Fix environment injection (#2)

**Day 2**:
- Morning: Fix path traversal (#3) and credentials (#4)
- Afternoon: Write and run security tests

**Total**: 2 days maximum

---

## Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://python.readthedocs.io/en/latest/library/security_warnings.html)
- [Subprocess Security](https://docs.python.org/3/library/subprocess.html#security-considerations)
- [Pydantic SecretStr](https://docs.pydantic.dev/latest/usage/types/#secret-types)

---

**Remember**: Security is not optional. These fixes MUST be implemented before production use.
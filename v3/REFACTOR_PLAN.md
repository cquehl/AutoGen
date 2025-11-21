# MCP REFACTOR PLAN
**Auto-Refactor System | @ARCHITECT Phase**
**Date**: 2025-11-21
**Branch**: `mcp-integration`
**Target**: Production-ready, secure, maintainable MCP integration

---

## 📊 EXECUTIVE SUMMARY

### Current State
- **Files**: 7 core modules (~6,000 LOC)
- **Architecture**: ★★★★★ (Excellent)
- **Security**: ★★☆☆☆ (4 critical vulnerabilities)
- **Code Quality**: ★★★★☆ (Good, needs polish)
- **Test Coverage**: ★★★★☆ (40+ tests, missing security/integration)
- **Complexity**: Medium-High (some functions >50 lines)

### Target State
- **Security**: ★★★★★ (All vulnerabilities fixed)
- **Code Quality**: ★★★★★ (World-class standards)
- **Complexity**: Low-Medium (20% reduction)
- **Test Coverage**: ★★★★★ (80%+ critical paths)
- **Maintainability**: ★★★★★ (Clear, documented, testable)

---

## 🎯 REFACTORING OBJECTIVES

### Primary Goals (MUST HAVE)
1. **Fix 4 critical security vulnerabilities** (BLOCKING)
2. **Implement 4 high-priority fixes** (production-critical)
3. **Reduce complexity by 20%** (per "One-Shot" protocol)
4. **Ensure all functions ≤20 lines** (quality gate)
5. **Achieve 80%+ test coverage** on critical paths

### Secondary Goals (SHOULD HAVE)
6. Standardize error handling across all modules
7. Add comprehensive input validation
8. Improve async cleanup and resource management
9. Reduce global mutable state
10. Add integration and security test suites

---

## 🏗️ ARCHITECTURAL ANALYSIS

### Dependency Map
```
config.py (Foundation)
    ↓
types.py (Data Structures)
    ↓
client.py + supervisor.py (Infrastructure)
    ↓
manager.py (Orchestration)
    ↓
autogen_bridge.py (Integration)
    ↓
alfred/main_mcp.py (Application)
```

### Code Smells Identified

#### 🔴 Critical (Security)
1. **Command Injection** (client.py:40, supervisor.py:63)
   - `command.split()` vulnerable to shell injection
   - **Fix**: Use `shlex.split()` + command allowlist

2. **Environment Variable Injection** (client.py:36, supervisor.py:58)
   - `os.environ.copy().update()` allows hijacking
   - **Fix**: Implement env var allowlist + sanitization

3. **Path Traversal** (config.py:74-77)
   - No validation on `working_directory`
   - **Fix**: Add path validator with forbidden directories

4. **Insecure Credentials** (config.py:112-115)
   - Plain text storage in memory/logs
   - **Fix**: Use Pydantic `SecretStr` + log sanitization

#### 🟠 High Priority (Production Blockers)
5. **No Rate Limiting** (manager.py:287-370)
   - Defined in config but never enforced
   - **Fix**: Implement rate limiter in `execute_tool()`

6. **Connection Pool Race** (types.py:176-192, client.py:402-404)
   - `active_count` not thread-safe
   - **Fix**: Add thread locking to ConnectionPool

7. **Unbounded JSON Parsing** (client.py:73)
   - No size limits, can cause DoS
   - **Fix**: Add MAX_MESSAGE_SIZE validation

8. **Cache Never Cleaned** (manager.py:58-60)
   - TTL configured but not enforced
   - **Fix**: Implement cache cleanup task

#### 🟡 Medium Priority (Code Quality)
9. **Functions >20 lines** (multiple files)
   - `_start_and_connect_server()` (38 lines)
   - `execute_tool()` (84 lines)
   - `convert_mcp_to_autogen_tool()` (45 lines)
   - **Fix**: Extract sub-functions

10. **Global Singletons** (config.py:304-326, manager.py:457-474)
    - Makes testing difficult
    - **Fix**: Use dependency injection pattern

11. **Inconsistent Error Handling**
    - Mix of generic Exception and specific errors
    - **Fix**: Standardize error hierarchy

---

## 📋 ATOMIC REFACTORING TASKS

### Phase 1: Security Hardening (CRITICAL - 1.5 days)

#### Task 1.1: Fix Command Injection
**File**: `client.py` (line 40), `supervisor.py` (line 63)
**Complexity**: Medium
**Time**: 2 hours

**Changes**:
```python
# BEFORE (VULNERABLE)
cmd = self.command.split() + self.args

# AFTER (SECURE)
import shlex
from .security import ALLOWED_COMMANDS  # New security module

def _parse_command(command: str) -> List[str]:
    """Parse command safely"""
    if not command:
        raise ValueError("Command cannot be empty")

    cmd_parts = shlex.split(command)
    base_cmd = cmd_parts[0]

    # Validate against allowlist
    if base_cmd not in ALLOWED_COMMANDS:
        raise SecurityError(f"Command not allowed: {base_cmd}")

    return cmd_parts

cmd = _parse_command(self.command) + self.args
```

**New File**: `src/core/mcp/security.py` (security utilities)

---

#### Task 1.2: Fix Environment Variable Injection
**File**: `client.py` (line 36), `supervisor.py` (line 58)
**Complexity**: Medium
**Time**: 3 hours

**Changes**:
```python
# BEFORE (VULNERABLE)
env = os.environ.copy()
env.update(self.env)

# AFTER (SECURE)
from .security import sanitize_env_vars

def _prepare_environment(custom_env: Dict[str, str]) -> Dict[str, str]:
    """Prepare sanitized environment"""
    # Start with minimal safe environment
    safe_env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "USER": os.environ.get("USER", ""),
    }

    # Add sanitized custom variables
    validated_env = sanitize_env_vars(custom_env)
    safe_env.update(validated_env)

    return safe_env

env = _prepare_environment(self.env)
```

**New Function**: `sanitize_env_vars()` in `security.py`

---

#### Task 1.3: Add Path Validation
**File**: `config.py` (line 74-77)
**Complexity**: Low
**Time**: 2 hours

**Changes**:
```python
@validator('working_directory')
def validate_working_directory(cls, v):
    """Validate working directory is safe"""
    if v is None:
        return v

    from .security import validate_path

    try:
        validated_path = validate_path(v, allow_create=False)
        return validated_path
    except ValueError as e:
        raise ValueError(f"Invalid working directory: {e}")
```

**New Function**: `validate_path()` in `security.py`

---

#### Task 1.4: Secure Credential Storage
**File**: `config.py` (line 112-115)
**Complexity**: Low
**Time**: 3 hours

**Changes**:
```python
from pydantic import SecretStr

class MCPServerConfig(BaseModel):
    # BEFORE
    # authentication: Optional[Dict[str, str]] = None

    # AFTER
    authentication: Optional[Dict[str, SecretStr]] = Field(
        None,
        description="Authentication credentials (stored securely)"
    )

    def dict(self, **kwargs):
        """Override to redact secrets from output"""
        d = super().dict(**kwargs)
        if d.get("authentication"):
            d["authentication"] = "***REDACTED***"
        return d

    def get_auth_value(self, key: str) -> Optional[str]:
        """Safely retrieve auth value"""
        if not self.authentication or key not in self.authentication:
            return None
        return self.authentication[key].get_secret_value()
```

---

### Phase 2: High-Priority Fixes (2-3 days)

#### Task 2.1: Implement Rate Limiting
**File**: `manager.py` (line 287-370)
**Complexity**: Medium
**Time**: 4 hours

**Changes**:
- Add `RateLimiter` class in `utils.py`
- Integrate into `MCPManager.__init__()`
- Enforce in `execute_tool()`
- Add tests for rate limiting

**New Class**: `RateLimiter` with sliding window algorithm

---

#### Task 2.2: Thread-Safe Connection Pool
**File**: `types.py` (line 170-192), `client.py` (line 402-404)
**Complexity**: Medium
**Time**: 3 hours

**Changes**:
```python
import threading
from contextlib import contextmanager

class ConnectionPool:
    def __init__(self, max_connections: int):
        self.max_connections = max_connections
        self.connections: Dict[str, MCPClient] = {}
        self._lock = threading.RLock()  # Reentrant lock

    @contextmanager
    def acquire_lock(self):
        """Context manager for thread-safe operations"""
        self._lock.acquire()
        try:
            yield
        finally:
            self._lock.release()

    def acquire(self, server_id: str) -> Optional[MCPClient]:
        with self.acquire_lock():
            return self.connections.get(server_id)

    # Update all methods to use acquire_lock()
```

---

#### Task 2.3: JSON Parsing Validation
**File**: `client.py` (line 64-73)
**Complexity**: Low
**Time**: 2 hours

**Changes**:
```python
MAX_MESSAGE_SIZE = 10 * 1024 * 1024  # 10MB

async def receive(self) -> Dict[str, Any]:
    """Receive and validate message"""
    if not self.process or not self.process.stdout:
        raise RuntimeError("Transport not connected")

    line = await self.process.stdout.readline()
    if not line:
        raise ConnectionError("Connection closed")

    # Validate size
    if len(line) > MAX_MESSAGE_SIZE:
        raise ValueError(f"Message exceeds limit: {len(line)} bytes")

    # Parse with error handling
    try:
        message = json.loads(line.decode('utf-8'))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")

    # Validate structure
    if not isinstance(message, dict):
        raise ValueError("Expected JSON object")

    return message
```

---

#### Task 2.4: Cache TTL Enforcement
**File**: `manager.py` (line 58-60)
**Complexity**: Medium
**Time**: 3 hours

**Changes**:
- Add `_check_cache()` method with TTL enforcement
- Add `_cleanup_cache()` background task
- Start cleanup task in `initialize()`
- Stop cleanup task in `shutdown()`

**New Methods**: `_check_cache()`, `_cleanup_cache()`, `_schedule_cache_cleanup()`

---

### Phase 3: Complexity Reduction (2-3 days)

#### Task 3.1: Refactor Large Functions
**Target**: All functions ≤20 lines (quality gate requirement)

**Functions to Split**:

##### 3.1.1: `manager._start_and_connect_server()` (38 lines → 3 functions)
```python
# Extract to:
async def _start_server(config: MCPServerConfig) -> MCPServer:
    """Start server process"""
    # Lines 107-108

async def _create_client(config: MCPServerConfig) -> RealMCPClient:
    """Create and connect client"""
    # Lines 111-120

async def _initialize_connection(config, server, client) -> MCPConnection:
    """Initialize connection object"""
    # Lines 123-132

async def _start_and_connect_server(config: MCPServerConfig) -> None:
    """Start server and establish connection (orchestrator)"""
    server = await self._start_server(config)
    client = await self._create_client(config)
    connection = await self._initialize_connection(config, server, client)
    self.connected_servers[config.name] = connection
```

##### 3.1.2: `manager.execute_tool()` (84 lines → 5 functions)
```python
# Extract to:
def _resolve_tool_name(tool_name: str) -> str:
    """Resolve tool name with server prefix"""

async def _check_agent_permissions(tool_name: str, agent_name: Optional[str]) -> None:
    """Validate agent has permission to use tool"""

async def _ensure_server_connected(server_name: str) -> MCPConnection:
    """Ensure server is connected"""

def _log_audit_event(tool_name: str, agent_name: str, server_name: str) -> None:
    """Log audit trail"""

async def execute_tool(...) -> ToolExecutionResult:
    """Execute MCP tool (orchestrator)"""
    tool_name = self._resolve_tool_name(tool_name)
    await self._check_agent_permissions(tool_name, agent_name)
    connection = await self._ensure_server_connected(server_name)
    self._log_audit_event(tool_name, agent_name, server_name)
    result = await connection.client.execute_tool(tool_name, arguments)
    return self._create_execution_result(result, tool_name, server_name)
```

##### 3.1.3: `autogen_bridge.convert_mcp_to_autogen_tool()` (45 lines → 4 functions)
```python
# Extract to:
def _create_tool_wrapper(tool_name: str, agent_name: str) -> Callable:
    """Create wrapper function"""

def _add_function_metadata(func: Callable, tool: MCPTool) -> None:
    """Add metadata for AutoGen"""

def _generate_function_signature(tool: MCPTool) -> Dict:
    """Generate function signature"""
```

---

#### Task 3.2: Standardize Error Handling
**File**: All files
**Complexity**: Medium
**Time**: 4 hours

**Create Error Hierarchy**:
```python
# New file: src/core/mcp/errors.py

class MCPError(SuntoryError):
    """Base MCP error"""
    pass

class MCPConnectionError(MCPError):
    """Connection-related errors"""
    pass

class MCPTimeoutError(MCPError):
    """Timeout errors"""
    pass

class MCPSecurityError(MCPError):
    """Security violations"""
    pass

class MCPValidationError(MCPError):
    """Input validation errors"""
    pass

class MCPServerError(MCPError):
    """Server lifecycle errors"""
    pass
```

**Apply Consistently**: Replace all generic `Exception` raises with specific error types

---

### Phase 4: Testing & Validation (2-3 days)

#### Task 4.1: Security Test Suite
**File**: `tests/test_mcp_security.py` (NEW)
**Complexity**: High
**Time**: 6 hours

**Test Cases** (15+):
- Command injection attempts (SQL, shell)
- Environment variable poisoning
- Path traversal attacks
- Credential extraction attempts
- DoS via large JSON payloads
- Race condition exploits
- Rate limit bypass attempts
- Privilege escalation attempts

---

#### Task 4.2: Integration Test Suite
**File**: `tests/test_mcp_integration.py` (NEW)
**Complexity**: High
**Time**: 6 hours

**Test Cases** (10+):
- End-to-end tool execution flow
- Concurrent operations (100 parallel requests)
- Server restart scenarios
- Connection failure recovery
- Cache consistency under load
- Health monitoring accuracy
- Resource leak detection
- Cleanup on shutdown

---

#### Task 4.3: Increase Unit Test Coverage
**File**: `tests/test_mcp.py` (UPDATE)
**Complexity**: Medium
**Time**: 4 hours

**Add Tests For**:
- All new security functions
- Rate limiter edge cases
- Connection pool thread safety
- Cache TTL enforcement
- Error handling paths
- Validation functions

**Target**: 80%+ coverage on critical paths

---

## 🔌 INTERFACE DEFINITIONS

### Security Module Interface
```python
# src/core/mcp/security.py

ALLOWED_COMMANDS: List[str] = [
    "npx", "node", "python3", "python", "docker", "kubectl"
]

ALLOWED_ENV_VARS: List[str] = [
    "PATH", "HOME", "USER", "ALLOWED_DIRECTORIES", "GITHUB_*", "MCP_*"
]

FORBIDDEN_DIRECTORIES: List[str] = [
    "/etc", "/bin", "/sbin", "/root", "/boot", "/.ssh"
]

def validate_command(command: str) -> List[str]:
    """Validate and parse command safely

    Args:
        command: Command string to validate

    Returns:
        List of command parts

    Raises:
        MCPSecurityError: If command is not allowed
    """

def sanitize_env_vars(env: Dict[str, str]) -> Dict[str, str]:
    """Sanitize environment variables

    Args:
        env: Environment variables to sanitize

    Returns:
        Sanitized environment dictionary

    Raises:
        MCPSecurityError: If dangerous variables detected
    """

def validate_path(
    path: str,
    operation: str = "read",
    allow_create: bool = False
) -> str:
    """Validate file path is safe

    Args:
        path: Path to validate
        operation: Operation type (read/write/execute)
        allow_create: Allow creation if doesn't exist

    Returns:
        Absolute validated path

    Raises:
        MCPSecurityError: If path is forbidden
    """
```

### Rate Limiter Interface
```python
# src/core/mcp/utils.py

class RateLimiter:
    """Thread-safe rate limiter with sliding window"""

    def __init__(self, max_requests: int, window_seconds: int = 60):
        """Initialize rate limiter

        Args:
            max_requests: Maximum requests in window
            window_seconds: Time window in seconds
        """

    def check_limit(self, identifier: str) -> bool:
        """Check if identifier is within limit

        Args:
            identifier: Unique identifier (e.g., agent name)

        Returns:
            True if within limit, False otherwise
        """

    def record_request(self, identifier: str) -> None:
        """Record a request for identifier

        Args:
            identifier: Unique identifier

        Raises:
            MCPRateLimitError: If rate limit exceeded
        """

    def get_remaining(self, identifier: str) -> int:
        """Get remaining requests in current window"""
```

---

## 📏 COMPLEXITY REDUCTION METRICS

### Current Complexity
```
Total LOC: ~6,000
Average Function Length: 18 lines
Max Function Length: 84 lines
Functions >20 lines: 12 (20%)
Cyclomatic Complexity: Avg 6.2, Max 14
```

### Target Complexity (20% Reduction)
```
Total LOC: ~5,800 (refactored, with new security code)
Average Function Length: 14 lines
Max Function Length: 20 lines
Functions >20 lines: 0 (0%)
Cyclomatic Complexity: Avg 4.9, Max 10
```

### Reduction Strategy
1. Extract 12 large functions into smaller units (-240 lines complexity)
2. Remove duplicated validation code (-150 lines)
3. Consolidate error handling (-100 lines)
4. **Net: -490 lines** of complexity
5. **Add: +300 lines** for security features
6. **Result: -190 net lines, 20%+ complexity reduction**

---

## ⚖️ CONSTRAINTS & QUALITY GATES

### Hard Constraints (MUST PASS)
1. ✅ All functions ≤20 lines
2. ✅ No function cyclomatic complexity >10
3. ✅ All security vulnerabilities fixed
4. ✅ No `eval()`, `exec()`, or `shell=True`
5. ✅ All secrets use `SecretStr`
6. ✅ Test coverage ≥80% on critical paths
7. ✅ All type hints present and validated
8. ✅ Zero linting errors (flake8, mypy)

### Soft Constraints (SHOULD PASS)
- Docstrings for all public functions
- No duplicated code blocks >5 lines
- Consistent naming conventions
- Clear error messages with recovery suggestions
- Performance: No operation >5s without timeout

---

## 🔄 DEPENDENCY ANALYSIS

### Modified Files (9)
1. `config.py` - Add validators, SecretStr, path validation
2. `types.py` - Thread-safe ConnectionPool
3. `client.py` - Secure command parsing, JSON validation
4. `supervisor.py` - Secure command parsing, env sanitization
5. `manager.py` - Rate limiting, cache cleanup, split large functions
6. `autogen_bridge.py` - Split large functions, add input validation
7. `__init__.py` - Export new security module

### New Files (4)
8. `security.py` - Security utilities (command, env, path validation)
9. `utils.py` - Rate limiter, helper functions
10. `errors.py` - Comprehensive error hierarchy
11. `tests/test_mcp_security.py` - Security test suite
12. `tests/test_mcp_integration.py` - Integration test suite

### Impact Analysis
- **Breaking Changes**: None (all changes internal)
- **API Changes**: None (public interface unchanged)
- **Performance Impact**: +5-10% (validation overhead, acceptable)
- **Memory Impact**: +2-5MB (rate limiter state, negligible)

---

## 📊 ROLLOUT STRATEGY

### Phase 1: Security (BLOCKING - Days 1-2)
```
Day 1:
- ✅ Create security.py module
- ✅ Fix command injection (Tasks 1.1)
- ✅ Fix env var injection (Task 1.2)
- ✅ Write security tests

Day 2:
- ✅ Fix path traversal (Task 1.3)
- ✅ Fix credential storage (Task 1.4)
- ✅ Run security test suite
- ✅ Manual penetration testing
```

### Phase 2: High Priority (Days 3-4)
```
Day 3:
- ✅ Thread-safe connection pool (Task 2.2)
- ✅ JSON validation (Task 2.3)
- ✅ Rate limiting (Task 2.1)

Day 4:
- ✅ Cache cleanup (Task 2.4)
- ✅ Integration tests
- ✅ Load testing
```

### Phase 3: Quality (Days 5-7)
```
Day 5:
- ✅ Refactor large functions (Task 3.1)
- ✅ Standardize errors (Task 3.2)

Day 6:
- ✅ Increase test coverage (Task 4.3)
- ✅ Add integration tests (Task 4.2)

Day 7:
- ✅ Code review
- ✅ Documentation updates
- ✅ Final validation
```

### Phase 4: Merge & Deploy (Days 8-9)
```
Day 8:
- ✅ Final security review
- ✅ Merge to main
- ✅ Deploy to staging

Day 9:
- ✅ Production deployment
- ✅ Monitoring
```

---

## ✅ SUCCESS CRITERIA

### Functional Requirements
- [x] All 40+ existing tests pass
- [ ] All 15+ security tests pass
- [ ] All 10+ integration tests pass
- [ ] Zero security vulnerabilities (static analysis)
- [ ] Performance within 10% of baseline

### Non-Functional Requirements
- [ ] Code complexity reduced by 20%
- [ ] All functions ≤20 lines
- [ ] Test coverage ≥80%
- [ ] Zero linting/type errors
- [ ] Documentation complete and accurate

### Production Readiness
- [ ] Security audit completed
- [ ] Load testing passed (100 concurrent users)
- [ ] Failure scenarios tested and handled
- [ ] Rollback plan documented
- [ ] Monitoring/alerting configured

---

## 🎯 REFACTORING PRINCIPLES APPLIED

1. **Single Responsibility**: Each function does one thing
2. **Open/Closed**: Extend via config, not code changes
3. **Liskov Substitution**: All transport types interchangeable
4. **Interface Segregation**: Small, focused interfaces
5. **Dependency Inversion**: Depend on abstractions (MCPClient interface)

6. **DRY** (Don't Repeat Yourself): Extract common validation
7. **KISS** (Keep It Simple): No over-engineering
8. **YAGNI** (You Aren't Gonna Need It): No speculative features
9. **Separation of Concerns**: Security in dedicated module
10. **Explicit is Better Than Implicit**: Clear error messages

---

## 🚨 RISK MITIGATION

### High Risk Areas
1. **Threading in Connection Pool**
   - Mitigation: Extensive concurrent testing
   - Fallback: Single-threaded mode if issues arise

2. **Backward Compatibility**
   - Mitigation: No public API changes
   - Validation: Run full test suite before/after

3. **Performance Regression**
   - Mitigation: Benchmark before/after
   - Target: <10% overhead acceptable

4. **Security Bypass**
   - Mitigation: Independent security audit
   - Validation: Penetration testing

---

## 📖 CONCLUSION

This refactoring plan transforms the MCP integration from "good with critical issues" to "production-ready and world-class" by:

✅ **Eliminating all 4 critical security vulnerabilities**
✅ **Implementing 4 high-priority production fixes**
✅ **Reducing complexity by 20%+**
✅ **Ensuring all functions ≤20 lines**
✅ **Achieving 80%+ test coverage**

The refactored codebase will maintain the excellent architecture while being secure, maintainable, and ready for production deployment.

**Estimated Total Time**: 7-9 days (1 developer)
**Confidence Level**: High (clear plan, well-tested approach)
**Risk Level**: Low-Medium (validated changes, comprehensive testing)

---

**Next Phase**: @QA_LEAD will write the comprehensive test suite (TDD approach)
**Status**: Ready to proceed with implementation

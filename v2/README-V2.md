# 🥃 Yamazaki v2 - Modern AutoGen Framework

> Like the whiskey distillery it's named after: smooth, refined, and carefully crafted.

Yamazaki v2 is a production-ready AutoGen implementation featuring modern software engineering practices:

- **Plugin-Based Architecture** - No code duplication, easy extensibility
- **Tool Marketplace** - Reusable, discoverable tools
- **Security Middleware** - Centralized validation and audit
- **Dependency Injection** - Modular, testable, swappable components
- **Type-Safe Configuration** - Pydantic + YAML validation
- **Structured Logging** - JSON or console, OpenTelemetry ready
- **Comprehensive Testing** - Unit, integration, and performance tests

## 📋 Table of Contents

- [Why Yamazaki v2?](#why-yamazaki-v2)
- [Architecture Overview](#architecture-overview)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
- [Creating Custom Agents](#creating-custom-agents)
- [Creating Custom Tools](#creating-custom-tools)
- [Configuration](#configuration)
- [Security](#security)
- [Observability](#observability)
- [Testing](#testing)
- [Migration from v1](#migration-from-v1)

## 🎯 Why Yamazaki v2?

### Problems Solved

| Problem (v1) | Solution (v2) | Benefit |
|--------------|---------------|---------|
| 535 lines of duplicated agent code | Plugin registry | 90% less code |
| Hard-coded tool imports | Tool marketplace | Add tools in 5 min |
| Scattered security validation | Security middleware | Single audit point |
| env vars + dict config | Pydantic + YAML | Type-safe, validated |
| Global state everywhere | DI container | Testable, swappable |
| print() debugging | Structured logging | Searchable, traceable |
| Difficult to test | Mocked dependencies | Fast, isolated tests |

### Key Improvements

```python
# v1: Creating agents (535 lines, lots of duplication)
async def create_weather_agent_team(llm_config: dict):
    component_config = {"provider": "azure_openai_chat_completion_client", ...}
    ai_client = ChatCompletionClient.load_component(component_config)
    weather_agent = create_weather_agent(ai_client)
    # ... repeat for each agent

# v2: Creating agents (3 lines, zero duplication)
factory = container.get_agent_factory()
weather_agent = factory.create("weather")
```

## 🏗️ Architecture Overview

```
v2/
├── config/              # Type-safe configuration (Pydantic + YAML)
│   ├── models.py        # Configuration models
│   └── settings.yaml    # YAML configuration
│
├── core/                # Core abstractions
│   ├── base_agent.py    # Base agent class
│   ├── base_tool.py     # Base tool class
│   └── container.py     # Dependency injection
│
├── agents/              # Agent plugins
│   ├── registry.py      # Agent registry (marketplace)
│   ├── factory.py       # Agent factory
│   ├── weather_agent.py # Example: Weather agent
│   └── data_analyst_agent.py  # Example: Data analyst
│
├── tools/               # Tool plugins
│   ├── registry.py      # Tool registry (marketplace)
│   ├── weather/         # Weather tools
│   ├── database/        # Database tools
│   ├── file/            # File operation tools
│   └── web/             # Web tools (future)
│
├── security/            # Centralized security
│   ├── middleware.py    # Security middleware
│   └── validators/      # SQL, path, URL validators
│
├── services/            # High-level services
│   ├── database.py      # Database service + connection pooling
│   └── file_service.py  # File service
│
├── observability/       # Logging, tracing, metrics
│   ├── logger.py        # Structured logging
│   └── manager.py       # Observability manager
│
└── main.py              # Entry point + demos
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install autogen-agentchat autogen-core autogen-ext
pip install pydantic pydantic-settings
pip install sqlalchemy aiosqlite
pip install httpx pyyaml
```

### 2. Configure Environment

Create `.env`:

```bash
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment
```

### 3. Run Interactive CLI

```bash
# From project root
python -m v2.cli

# Or use the convenience script
./run_cli.sh
```

This starts an interactive session where you can:
- Chat with agents
- Use `/help` to see available commands
- Use `/agents` to list all agents
- Use `/tools` to see available tools
- Use `/info` for system information

### 4. Run Demo (Showcase Features)

```bash
python -m v2.main
```

### 5. Use Agents Programmatically

```python
import asyncio
from v2.core import get_container

async def main():
    # Get container
    container = get_container()

    # Initialize observability
    obs = container.get_observability_manager()
    obs.initialize()

    # Get agent factory
    factory = container.get_agent_factory()

    # Create a team
    team = factory.create_team("weather_team")

    # Run task
    result = await team.run(task="What's the weather in Seattle?")

    # Cleanup
    await container.dispose()

asyncio.run(main())
```

## 💡 Core Concepts

### 1. Dependency Injection Container

The container manages all services and their dependencies:

```python
from v2.core import get_container

# Get container (singleton)
container = get_container()

# Get services
agent_factory = container.get_agent_factory()
tool_registry = container.get_tool_registry()
security = container.get_security_middleware()
db_service = container.get_database_service()

# Cleanup on shutdown
await container.dispose()
```

### 2. Agent Registry (Plugin System)

Register agents once, create many times:

```python
from v2.core import BaseAgent
from v2.agents import AgentRegistry

class MyAgent(BaseAgent):
    NAME = "my_agent"
    DESCRIPTION = "My custom agent"
    CATEGORY = "custom"
    VERSION = "1.0.0"

    @property
    def system_message(self) -> str:
        return "You are a helpful agent..."

# Register (done automatically via discovery)
registry = container.get_agent_registry()

# Create instances
agent1 = registry.get_agent("my_agent")
agent2 = registry.get_agent("my_agent")  # New instance
```

### 3. Tool Marketplace

Register tools once, use everywhere:

```python
from v2.core import BaseTool, ToolResult, ToolCategory

class MyTool(BaseTool):
    NAME = "my.tool"
    DESCRIPTION = "Does something cool"
    CATEGORY = ToolCategory.GENERAL

    async def execute(self, **kwargs) -> ToolResult:
        # Do work
        return ToolResult.ok({"result": "success"})

    def validate_params(self, **kwargs) -> tuple[bool, str]:
        # Validate inputs
        return True, None

# Use in agents via config
agents:
  my_agent:
    tools:
      - my.tool
```

### 4. Security Middleware

Centralized security validation:

```python
from v2.security import SecurityMiddleware, Operation, OperationType

# Get middleware
security = container.get_security_middleware()

# Create operation
operation = Operation(
    type=OperationType.SQL_QUERY,
    params={"query": "SELECT * FROM users WHERE id = :id", "params": {"id": 1}},
    executor=db_service.execute_query
)

# Execute with validation, timeout, and audit
result = await security.validate_and_execute(operation)

if result.success:
    print(f"Query completed in {result.execution_time_ms}ms")
else:
    print(f"Blocked or failed: {result.error}")
```

## 🎨 Creating Custom Agents

### Step 1: Create Agent Class

```python
# v2/agents/my_agent.py
from v2.core import BaseAgent

class MyAgent(BaseAgent):
    NAME = "my_agent"
    DESCRIPTION = "My custom agent that does X"
    CATEGORY = "custom"
    VERSION = "1.0.0"

    @property
    def system_message(self) -> str:
        return """
        You are a specialized agent that...

        Your capabilities:
        - Thing 1
        - Thing 2

        Your tools:
        - tool.name - description
        """
```

### Step 2: Configure Agent

```yaml
# v2/config/settings.yaml
agents:
  my_agent:
    name: My_Agent
    model_provider: azure
    temperature: 0.7
    tools:
      - my.tool
    reflect_on_tool_use: true
```

### Step 3: Use Agent

```python
factory = container.get_agent_factory()
my_agent = factory.create("my_agent")

# Or create a team
team = factory.create_custom_team(
    agent_names=["my_agent", "orchestrator"],
    max_turns=20
)
```

## 🛠️ Creating Custom Tools

### Step 1: Create Tool Class

```python
# v2/tools/my_category/my_tool.py
from v2.core import BaseTool, ToolResult, ToolCategory
from typing import Optional

class MyTool(BaseTool):
    NAME = "my.tool"
    DESCRIPTION = "Does something useful"
    CATEGORY = ToolCategory.GENERAL
    VERSION = "1.0.0"
    REQUIRES_SECURITY_VALIDATION = False  # Set True if needed

    async def execute(self, param1: str, param2: int = 10) -> ToolResult:
        """Execute tool logic"""
        try:
            # Do work
            result = {"output": f"Processed {param1} with {param2}"}
            return ToolResult.ok(result)
        except Exception as e:
            return ToolResult.error(str(e))

    def validate_params(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters before execution"""
        param1 = kwargs.get("param1")
        if not param1:
            return False, "param1 is required"
        return True, None

    def _get_parameters_schema(self) -> dict:
        """OpenAI function schema"""
        return {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "Description of param1"
                },
                "param2": {
                    "type": "integer",
                    "description": "Description of param2",
                    "default": 10
                }
            },
            "required": ["param1"]
        }
```

### Step 2: Register Tool (Auto-discovery)

Tools are auto-discovered by the registry. Just import in `tools/my_category/__init__.py`:

```python
from .my_tool import MyTool
__all__ = ["MyTool"]
```

### Step 3: Use Tool

The tool is now available to any agent via configuration!

## ⚙️ Configuration

### Configuration Sources (Priority Order)

1. Environment variables (highest priority)
2. `.env` file
3. `settings.yaml`
4. Default values (lowest priority)

### Example Configuration

```yaml
# v2/config/settings.yaml
environment: development
default_provider: azure

database:
  url: sqlite:///./data/yamazaki.db
  pool_size: 10
  query_timeout: 60

security:
  allowed_directories:
    - ./data
    - ~/agent_output
  enable_audit_log: true

observability:
  log_level: INFO
  log_format: console
  enable_telemetry: true

agents:
  weather:
    temperature: 0.7
    tools:
      - weather.forecast
```

### Environment Variables

```bash
# LLM Provider
AZURE_OPENAI_API_KEY=xxx
AZURE_OPENAI_ENDPOINT=https://xxx.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o

# Database
DATABASE_URL=sqlite:///./data/custom.db

# Observability
LOG_LEVEL=DEBUG
ENABLE_TELEMETRY=true
```

## 🔒 Security

### Security Features

1. **SQL Injection Prevention**
   - Blocks DROP, TRUNCATE, ALTER, EXEC, etc.
   - Prevents query chaining
   - Validates DELETE has WHERE clause

2. **Path Traversal Protection**
   - Validates paths within allowed directories
   - Blocks sensitive files (.ssh, .env, etc.)
   - Resolves symlinks and relative paths

3. **Audit Logging**
   - Logs all security events
   - Tracks blocked operations
   - Records execution times

4. **Operation Timeouts**
   - Prevents long-running operations
   - Configurable per operation type
   - Automatic cleanup

### Security Example

```python
# Security middleware validates and audits
security = container.get_security_middleware()

# SQL validation
validator = security.get_sql_validator()
is_valid, error, query_type = validator.validate(query)

# Path validation
path_validator = security.get_path_validator()
is_valid, error, path = path_validator.validate("/some/file.txt", "read")

# View audit log
events = security.get_audit_events(limit=100)
```

## 📊 Observability

### Structured Logging

```python
from v2.observability import get_logger, log_agent_action

logger = get_logger("my_module")

# Standard logging
logger.info("Processing request")
logger.error("Failed to process", exc_info=True)

# Structured event logging
log_agent_action(logger, "weather", "forecast_requested", location="Seattle")
```

### Log Formats

**Console (default):**
```
[INFO] 2025-01-15 10:30:15 - yamazaki.agents - Created weather agent
```

**JSON (for production):**
```json
{
  "timestamp": "2025-01-15T10:30:15.123Z",
  "level": "INFO",
  "logger": "yamazaki.agents",
  "message": "Created weather agent",
  "agent_name": "weather"
}
```

### OpenTelemetry Integration

```python
# Auto-configured when enable_telemetry=true
from opentelemetry import trace

tracer = trace.get_tracer("yamazaki")

with tracer.start_as_current_span("process_request") as span:
    span.set_attribute("user_id", "123")
    # Do work
```

## 🧪 Testing

### Test Structure

```
tests/
├── unit/              # Fast, isolated tests
├── integration/       # Database, API tests
├── performance/       # Benchmarks
└── security/          # Security regression tests
```

### Example Tests

```python
import pytest
from v2.core import Container
from v2.config import AppSettings

@pytest.fixture
def test_container():
    """Test container with mocked dependencies"""
    settings = AppSettings(
        environment="test",
        database={"url": "sqlite:///:memory:"},
    )
    container = Container(settings=settings)
    yield container
    # Cleanup

def test_agent_creation(test_container):
    """Test agent creation"""
    factory = test_container.get_agent_factory()
    agent = factory.create("weather")
    assert agent is not None
    assert agent.config.name == "Weather_Agent"

def test_sql_injection_blocked():
    """Ensure SQL injection is blocked"""
    from v2.security.validators import SQLValidator
    from v2.config.models import SecurityConfig

    validator = SQLValidator(SecurityConfig())

    dangerous = "SELECT * FROM users; DROP TABLE users;"
    is_valid, error, _ = validator.validate(dangerous)

    assert not is_valid
    assert "Multiple SQL statements not allowed" in error
```

## 🔄 Migration from v1

### v1 → v2 Comparison

| Task | v1 | v2 |
|------|----|----|
| Create agent | ~50 lines per agent | 1 class + config |
| Add tool | Edit multiple files | 1 class file |
| Configure | env vars scattered | 1 YAML file |
| Security | Duplicated in each tool | 1 middleware |
| Logging | print() everywhere | Structured logger |
| Testing | Hard to test | DI + mocks |

### Migration Steps

1. **Move old code** (already done)
   ```bash
   mv agents config services v1/
   ```

2. **Port agents** to v2 plugin system
   ```python
   # v1: Function-based
   def create_weather_agent(model_client):
       return AssistantAgent(...)

   # v2: Class-based plugin
   class WeatherAgent(BaseAgent):
       @property
       def system_message(self) -> str:
           return "..."
   ```

3. **Port tools** to tool marketplace
   ```python
   # v1: Function
   async def query_database(query):
       ...

   # v2: Tool class
   class DatabaseQueryTool(BaseTool):
       async def execute(self, query):
           ...
   ```

4. **Update configuration**
   - Consolidate env vars into `.env`
   - Create `settings.yaml` for structured config
   - Remove hardcoded values

5. **Update imports**
   ```python
   # v1
   from agents.weather_agents import create_weather_agent

   # v2
   from v2.core import get_container
   factory = get_container().get_agent_factory()
   agent = factory.create("weather")
   ```

## 📚 Additional Resources

- [AutoGen Documentation](https://microsoft.github.io/autogen/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/)

## 🎯 Next Steps

1. **Add More Agents**
   - Web QA team (browser automation)
   - Content creation team
   - Research assistants

2. **Add MCP Tools**
   - Google MCP integration
   - Browser MCP tools
   - Custom MCP servers

3. **Enhance Observability**
   - Grafana dashboards
   - Prometheus metrics
   - Distributed tracing

4. **Production Hardening**
   - Rate limiting
   - Circuit breakers
   - Chaos testing

---

**Built with** ❤️ **using AutoGen 0.7.5 and modern Python practices**

*Like Yamazaki whiskey: refined through careful craftsmanship, balanced in design, smooth in execution.*

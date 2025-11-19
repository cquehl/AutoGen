# Yamazaki v2 - AutoGen Multi-Agent Framework

A production-ready, plugin-based multi-agent framework built on Microsoft AutoGen, featuring centralized security, dependency injection, and a clean tool marketplace architecture.

## What is Yamazaki v2?

Yamazaki v2 is a sophisticated framework for building AI agent systems with:

- **Plugin-Based Architecture** - Tools and agents auto-register via registries
- **Centralized Security** - All operations validated through security middleware with audit logging
- **Dependency Injection** - Clean service lifecycle management via IoC container
- **Type-Safe Configuration** - Pydantic models with YAML/env override support
- **Team Orchestration** - Multiple patterns (Sequential, Graph, Swarm)
- **Production-Ready** - Async/await throughout, structured logging, error handling

## Quick Start

### Prerequisites

- Python 3.10+
- Azure OpenAI API credentials (or OpenAI API key)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd AutoGen

# Install v2 dependencies
pip install -r v2/requirements.txt

# Set up configuration
cp .env.example .env
# Edit .env with your Azure OpenAI credentials
```

### Run a Demo

```bash
# Interactive CLI
python -m v2.cli

# Run demos
python -m v2.main
```

## Current Features

### Implemented Agents (4)

| Agent | Purpose | Status |
|-------|---------|--------|
| **Alfred** | Meta-agent concierge, capability discovery, task delegation | ✅ Implemented |
| **Weather Agent** | Weather forecasts via weather.gov API | ✅ Implemented |
| **Data Analyst** | Database queries and file analysis | ✅ Implemented |
| **Orchestrator** | Multi-agent task coordination | ✅ Implemented |

### Implemented Tools (6)

| Tool | Category | Description | Status |
|------|----------|-------------|--------|
| `weather.forecast` | WEATHER | Get weather forecasts from weather.gov | ✅ |
| `database.query` | DATABASE | Execute SQL queries with validation | ✅ |
| `file.read` | FILE | Read file contents | ✅ |
| `alfred.list_capabilities` | META | System capability discovery | ✅ |
| `alfred.show_history` | META | Conversation history | ✅ |
| `alfred.delegate_to_team` | META | Multi-agent delegation | ✅ |

### Team Orchestration Patterns (3)

- **Sequential Team** - Linear agent conversation
- **Graph Flow Team** - DAG-based workflows with conditional branching
- **Swarm Team** - Parallel agent execution

## Architecture Highlights

### Security-First Design

All security-critical operations go through centralized validation:

- **SQL Injection Prevention** - Pattern matching and dangerous command blocking
- **Path Traversal Protection** - Blocks `..` and access to sensitive files
- **Audit Logging** - Tamper-evident audit trail with checksums
- **Configurable Timeouts** - Prevents runaway operations

### Plugin Architecture

```python
# Tools auto-register
class MyTool(BaseTool):
    NAME = "my.tool"
    CATEGORY = ToolCategory.GENERAL

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult.ok(data={"result": "success"})

# Agents auto-register
class MyAgent(BaseAgent):
    async def generate_system_message(self) -> str:
        return "I am a helpful agent"
```

### Dependency Injection

```python
# Clean service management
container = get_container()
agent_factory = container.get_agent_factory()
tool_registry = container.get_tool_registry()

# Services auto-injected into tools/agents
agent = agent_factory.create("weather")
```

## Documentation

### Core Documentation

- **[v2/README-V2.md](v2/README-V2.md)** - Complete v2 framework documentation
- **[ARCHITECTURE_FIXES.md](ARCHITECTURE_FIXES.md)** - Recent architecture improvements
- **[CRITICAL_FIXES.md](CRITICAL_FIXES.md)** - Production security fixes

### Planning Documents (Future Features)

> **⚠️ Note:** These describe PLANNED features, not current implementation

- **[ROADMAP.md](ROADMAP.md)** - Planned feature development
- **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** - Design specs for future tools

## Project Structure

```
AutoGen/
├── v2/                      # Current production version
│   ├── core/               # Base abstractions (agents, tools, DI)
│   ├── agents/             # Agent implementations
│   ├── tools/              # Tool marketplace
│   ├── teams/              # Orchestration patterns
│   ├── security/           # Security middleware & validators
│   ├── config/             # Configuration management
│   ├── services/           # High-level business logic
│   ├── memory/             # Agent memory & state
│   ├── messaging/          # Event-driven messaging
│   ├── workflows/          # Workflow orchestration
│   └── cli.py              # Interactive CLI
│
├── v1/                      # Legacy version (archived)
├── tests/                   # Test suite
└── .env.example            # Configuration template
```

## Configuration

Yamazaki v2 supports multiple configuration sources with the following priority:

1. **Environment variables** (highest priority)
2. `.env` file
3. `v2/config/settings.yaml`
4. Hardcoded defaults (lowest priority)

### Example Configuration

```yaml
# v2/config/settings.yaml
default_provider: azure

agents:
  weather:
    model_provider: azure
    temperature: 0.7
    tools:
      - weather.forecast
```

## Development

### Running Tests

```bash
pytest tests/
```

### Adding a New Tool

1. Create tool class inheriting from `BaseTool`
2. Place in appropriate `v2/tools/<category>/` directory
3. Tool auto-registers on import

See [v2/README-V2.md](v2/README-V2.md) for detailed development guide.

## What's Planned (Not Implemented)

The following features are designed but **not yet implemented**:

- Shell/Bash execution tools
- Git/GitHub integration tools
- Web search and scraping tools
- File write operations
- Database schema inspection tools
- Multimodal (image/PDF) tools

See [ROADMAP.md](ROADMAP.md) for complete planned feature list.

## Contributing

This is a maintained codebase. Contributions should:

- Follow the plugin architecture pattern
- Include security validation where appropriate
- Add tests for new features
- Update documentation

## License

[Add your license here]

## Credits

Built on [Microsoft AutoGen](https://github.com/microsoft/autogen) framework.

---

**For detailed v2 documentation, see [v2/README-V2.md](v2/README-V2.md)**

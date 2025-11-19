# 🥃 Suntory System v3

> **Alfred, your Distinguished AI Concierge**

A production-grade multi-agent AI system built on AutoGen, featuring intelligent task routing, specialist team orchestration, and autonomous execution capabilities.

## ✨ What Makes Suntory v3 Special

**Simplified Architecture, Enhanced Capabilities:**
- ✅ **Dual-Mode Operation**: Direct Proxy (quick queries) + Team Orchestrator (complex tasks)
- ✅ **Multi-Provider LLM Support**: OpenAI, Anthropic Claude, Google Gemini with automatic fallback
- ✅ **Magentic-One Architecture**: Autonomous web research, file navigation, code generation, terminal execution
- ✅ **Production-Ready**: Docker sandboxing, structured logging, persistence, observability
- ✅ **Beautiful TUI**: Rich terminal interface with markdown rendering
- ✅ **Premium Experience**: Think premium consulting platform, not chatbot

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** (required)
- **Docker** (recommended for sandboxing)
- **API Keys** for at least one provider:
  - OpenAI (`OPENAI_API_KEY`)
  - Anthropic (`ANTHROPIC_API_KEY`)
  - Google (`GOOGLE_API_KEY`)

### Installation

```bash
# 1. Navigate to v3 directory
cd v3/

# 2. Copy environment template
cp .env.example .env

# 3. Add your API keys to .env
# Edit .env and add at least one API key

# 4. Run Suntory (handles all setup automatically)
./Suntory.sh
```

That's it! The script will:
- ✓ Check Python version
- ✓ Create virtual environment
- ✓ Install dependencies
- ✓ Start Docker containers
- ✓ Initialize database
- ✓ Launch Alfred

## 🎯 How It Works

### Alfred's Two Modes

#### 1. **Direct Proxy Mode** (Default)
Alfred handles simple queries directly, acting as an intelligent middleware:

```
User: "What's the weather like?"
Alfred: [Direct mode] → LLM → Response
```

**Use for:**
- Questions and answers
- Simple code explanations
- Quick lookups
- Conversational interactions

#### 2. **Team Orchestrator Mode** (Automatic)
Alfred assembles specialist agents for complex tasks:

```
User: "Build a data pipeline for manufacturing metrics"
Alfred: [Team mode] → Assemble: [Product, Data Scientist, Engineer, QA]
        → Coordinate execution → Deliver result
```

**Triggers automatically for:**
- Keywords: "build", "create", "implement", "design", "analyze"
- Complex multi-step tasks
- Explicit request: `/team <task>`

### Specialist Agents

| Agent | Expertise | When to Use |
|-------|-----------|-------------|
| **Engineer** | Software architecture, coding, system design | Feature development, code review |
| **QA** | Test strategy, quality assurance | Testing, bug detection |
| **Product** | Requirements, user stories, prioritization | Feature planning, roadmap |
| **UX** | User experience, interface design | UI/UX design, accessibility |
| **Data Scientist** | Data analysis, ETL, ML | Data pipelines, analytics |
| **Security** | OWASP Top 10, threat modeling | Security audit, compliance |
| **Operations** | Infrastructure, DevOps, monitoring | Deployment, scaling |

### Magentic-One Agents

Based on Microsoft's Magentic-One architecture:

| Agent | Capability | Use Case |
|-------|------------|----------|
| **Web Surfer** | Autonomous web research | Competitive analysis, research |
| **File Surfer** | Codebase navigation | Code exploration, documentation |
| **Coder** | Code generation, debugging | Automated coding tasks |
| **Terminal** | Sandboxed command execution | Build, test, deploy |

## 💬 Using Alfred

### Basic Conversation

```
[alfred] > Hello!

┌─ Alfred ─────────────────────────────────────────────┐
│ Good evening, Me'Lord. Shall we build something      │
│ remarkable tonight?                                   │
└───────────────────────────────────────────────────────┘

[alfred] > What can you do?

┌─ Alfred ─────────────────────────────────────────────┐
│ I oversee the Suntory System with two modes:         │
│                                                       │
│ **Direct Mode**: I handle queries directly           │
│ **Team Mode**: I assemble specialist teams           │
│                                                       │
│ Available specialists: Engineer, QA, Product,        │
│ UX, Data Scientist, Security, Operations             │
└───────────────────────────────────────────────────────┘
```

### Commands

| Command | Description |
|---------|-------------|
| `/model` | Show current model and available providers |
| `/model <name>` | Switch LLM (e.g., `gpt-4o`, `claude-3-5-sonnet-20241022`) |
| `/team <task>` | Force team orchestration mode |
| `/mode` | Show current operating mode |
| `/history` | Show conversation history |
| `/clear` | Clear conversation history |
| `/help` | Show all commands |
| `exit` or `quit` | Exit gracefully |

### Example Workflows

#### Simple Query (Direct Mode)
```
[alfred] > Explain what a closure is in JavaScript

[Direct mode activates automatically]
Alfred provides clear explanation
```

#### Complex Task (Team Mode)
```
[alfred] > Build a secure REST API for user authentication with JWT

[Team mode triggers automatically]
Alfred: Assembling specialist team...

PRODUCT: Defining requirements...
ENGINEER: Designing API architecture...
SECURITY: Reviewing authentication flow...
QA: Creating test strategy...

[Team delivers complete solution]
```

#### Model Switching
```
[alfred] > /model claude-3-5-sonnet-20241022
Switched from gpt-4o to claude-3-5-sonnet-20241022

[alfred] > /model
Current model: claude-3-5-sonnet-20241022
Available providers: openai, anthropic, google
```

## 🏗️ Architecture

```
v3/
├── Suntory.sh              # Entry point (run this!)
├── .env                     # Your API keys (git-ignored)
├── requirements.txt         # Python dependencies
├── docker-compose.yml       # Container orchestration
│
├── src/
│   ├── alfred/              # Alfred's brain
│   │   ├── main.py          # Conversation orchestration
│   │   ├── modes.py         # Direct & Team modes
│   │   └── personality.py   # Greetings & character
│   │
│   ├── agents/              # Specialist & Magentic-One agents
│   │   ├── specialist/      # Domain experts
│   │   └── magentic/        # Autonomous agents
│   │
│   ├── core/                # Foundation
│   │   ├── config.py        # Pydantic settings
│   │   ├── llm_gateway.py   # Multi-provider LLM access
│   │   ├── persistence.py   # SQLite + ChromaDB
│   │   └── telemetry.py     # Structured logging
│   │
│   └── interface/           # User interface
│       └── tui.py           # Rich terminal UI
│
├── workspace/               # Agent working directory
├── data/                    # Database & vector store
└── logs/                    # Structured logs
```

## 🔧 Configuration

All configuration is in `.env`:

```bash
# LLM Providers (add at least one)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Default Model
DEFAULT_MODEL=claude-3-5-sonnet-20241022

# System Settings
ENVIRONMENT=development
LOG_LEVEL=INFO
DOCKER_ENABLED=true
ENABLE_AGENT_MEMORY=true

# Alfred's Personality
ALFRED_GREETING_STYLE=time_aware  # formal, casual, time_aware
ALFRED_PERSONALITY=balanced       # professional, witty, balanced
```

## 🐳 Docker Services

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Start with observability (Prometheus + Grafana)
docker-compose --profile observability up -d
```

**Services:**
- **agent-sandbox**: Isolated Python environment for code execution
- **chromadb**: Vector database for agent memory
- **prometheus**: Metrics collection (optional)
- **grafana**: Visualization dashboard (optional)

## 📊 Features

### ✅ Implemented

- [x] Multi-provider LLM support (OpenAI, Claude, Gemini)
- [x] Direct Proxy mode (Alfred as middleware)
- [x] Team Orchestrator mode (specialist coordination)
- [x] 7 Specialist agents (Engineer, QA, Product, UX, Data, Security, Ops)
- [x] 4 Magentic-One agents (Web Surfer, File Surfer, Coder, Terminal)
- [x] Docker sandboxing for security
- [x] SQLite + ChromaDB persistence
- [x] Structured logging with correlation IDs
- [x] Rich terminal UI with markdown rendering
- [x] Session history and agent memory
- [x] Graceful error handling and fallback
- [x] Model switching at runtime

### 🚧 Roadmap

- [ ] Full Playwright integration for Web Surfer
- [ ] Code execution in sandboxed containers
- [ ] RAG for agent memory retrieval
- [ ] Teachable agents (learning from interactions)
- [ ] Multi-modal support (images, diagrams)
- [ ] API server mode (REST API)
- [ ] Web UI (in addition to terminal)
- [ ] Cloud deployment (AWS, GCP, Azure)

## 🧪 Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test
pytest tests/test_alfred.py
```

## 🔒 Security

**Built-in Security Features:**

1. **Docker Sandboxing**: All code execution isolated
2. **Resource Limits**: Memory and CPU constraints
3. **Input Validation**: Pydantic models for all inputs
4. **Secrets Management**: API keys from .env only
5. **Audit Logging**: All actions logged with correlation IDs
6. **No Host Access**: Containers cannot access host filesystem

## 🎯 Use Cases

### Software Consulting
- Full-stack application development
- Code review and refactoring
- Architecture design and review
- Security audits

### Data Engineering
- ETL pipeline design
- Data analysis and visualization
- Database optimization
- ML model development

### Operations
- Infrastructure as code
- CI/CD pipeline setup
- Monitoring and alerting
- Incident response

### Product Development
- Feature planning and prioritization
- User story writing
- UX/UI design feedback
- Quality assurance

## 🤝 Contributing

This is a v3 rewrite focused on simplicity and robustness. Contributions welcome!

**Key Principles:**
- Keep it simple (less abstraction than v2)
- Production-ready (logs, tests, docs)
- Premium experience (think consulting platform)
- Security first (sandboxing, validation)

## 📝 License

MIT License - see LICENSE file

## 🙏 Acknowledgments

Built with:
- [AutoGen](https://microsoft.github.io/autogen/) - Multi-agent framework
- [LiteLLM](https://docs.litellm.ai/) - Unified LLM API
- [Rich](https://rich.readthedocs.io/) - Beautiful terminal UI
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [Pydantic](https://docs.pydantic.dev/) - Data validation

Inspired by:
- Microsoft's Magentic-One architecture
- Traditional English butler service (Alfred's character)
- Premium Japanese whisky craftsmanship (Suntory's philosophy)

---

**Built with care by the Suntory team.**

*"Smooth, refined, production-ready."*

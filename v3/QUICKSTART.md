# 🚀 Suntory v3 - Quick Start Guide

Get Alfred up and running in 5 minutes!

## Prerequisites

✅ **Python 3.11 or later**
✅ **At least one API key** (OpenAI, Anthropic, or Google)
⚠️ **Docker** (optional but recommended)

## Step-by-Step Setup

### 1. Navigate to v3 Directory

```bash
cd v3/
```

### 2. Create Environment File

```bash
cp .env.example .env
```

### 3. Add Your API Keys

Edit `.env` and add at least one API key:

```bash
# Choose ONE or MORE:

# OpenAI
OPENAI_API_KEY=sk-your-key-here

# Anthropic Claude (Recommended!)
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Google Gemini
GOOGLE_API_KEY=your-key-here
```

**Getting API Keys:**
- OpenAI: https://platform.openai.com/api-keys
- Anthropic: https://console.anthropic.com/
- Google: https://makersuite.google.com/app/apikey

### 4. Launch Alfred!

```bash
./Suntory.sh
```

That's it! The script automatically:
- ✓ Creates virtual environment
- ✓ Installs all dependencies
- ✓ Starts Docker containers (if available)
- ✓ Initializes database
- ✓ Launches Alfred

## First Conversation

```
[alfred] > Hello!

┌─ Alfred ─────────────────────────────────────────────┐
│ Good morning, Me'Lord. Alfred at your service.       │
│ How may I assist you today?                          │
└───────────────────────────────────────────────────────┘

[alfred] > What can you do?

┌─ Alfred ─────────────────────────────────────────────┐
│ I oversee the Suntory System with two capabilities:  │
│                                                       │
│ **Direct Mode**: Quick queries and conversations     │
│ **Team Mode**: Complex tasks with specialist agents  │
│                                                       │
│ I can help with:                                      │
│ • Software development                                │
│ • Data analysis and pipelines                         │
│ • Security audits                                     │
│ • UX/UI design                                        │
│ • DevOps and infrastructure                           │
│                                                       │
│ Type /help to see all commands.                       │
└───────────────────────────────────────────────────────┘
```

## Essential Commands

| Command | What It Does |
|---------|--------------|
| `/help` | Show all commands |
| `/model` | See current model |
| `/model gpt-4o` | Switch to GPT-4 |
| `/model claude-3-5-sonnet-20241022` | Switch to Claude |
| `/team <task>` | Force team mode |
| `exit` or `quit` | Exit Alfred |

## Example Tasks

### Simple Query (Direct Mode)

```
[alfred] > Explain Python decorators in simple terms
```

Alfred responds immediately with a clear explanation.

### Complex Task (Team Mode - Automatic)

```
[alfred] > Build a secure REST API for user authentication with JWT tokens and rate limiting
```

Alfred automatically:
1. Detects complexity
2. Assembles team: Product, Engineer, Security, QA
3. Coordinates their work
4. Delivers complete solution

### Force Team Mode

```
[alfred] > /team Create a data visualization dashboard for sales metrics
```

Forces team orchestration even for simpler tasks.

### Switch Models

```
[alfred] > /model
Current model: claude-3-5-sonnet-20241022
Available providers: openai, anthropic

[alfred] > /model gpt-4o
Switched from claude-3-5-sonnet-20241022 to gpt-4o
```

## Troubleshooting

### "No API keys found"

**Solution:** Add at least one API key to `.env`:

```bash
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### "Python 3.11 required"

**Solution:** Install Python 3.11+:

```bash
# macOS
brew install python@3.11

# Ubuntu/Debian
sudo apt install python3.11

# Windows
# Download from python.org
```

### "Docker not running"

**Solution:** Docker is optional but recommended.

**With Docker:**
```bash
# Start Docker Desktop, then:
./Suntory.sh
```

**Without Docker:**
```bash
# Edit .env and set:
DOCKER_ENABLED=false

# Then run:
./Suntory.sh
```

### Dependencies Installation Fails

**Solution:**

```bash
# Create fresh virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### Import Errors

**Solution:**

```bash
# Ensure PYTHONPATH is set (script does this automatically)
export PYTHONPATH="${PWD}:${PYTHONPATH}"
python -m src.interface.tui
```

## What's Next?

### Explore Capabilities

```
[alfred] > /help
[alfred] > What specialist agents do you have?
[alfred] > Show me what team mode can do
```

### Try Complex Tasks

```
[alfred] > Build a CI/CD pipeline for a Python project with automated testing
[alfred] > Create a data pipeline that processes CSV files and stores in PostgreSQL
[alfred] > Design a microservices architecture for an e-commerce platform
```

### Customize Alfred

Edit `.env` to customize:

```bash
# Alfred's personality
ALFRED_PERSONALITY=balanced  # professional, witty, balanced

# Greeting style
ALFRED_GREETING_STYLE=time_aware  # formal, casual, time_aware

# Default model
DEFAULT_MODEL=claude-3-5-sonnet-20241022

# Max conversation turns for teams
MAX_TEAM_TURNS=30
```

## Performance Tips

1. **Use Claude for Complex Tasks**: Claude 3.5 Sonnet excels at reasoning
2. **Use GPT-4 for Code**: GPT-4 is excellent for code generation
3. **Switch Models Dynamically**: Use `/model` to switch based on task
4. **Enable Docker**: Provides security and isolation
5. **Enable Agent Memory**: Set `ENABLE_AGENT_MEMORY=true` for learning

## Getting Help

- Read full docs: `README.md`
- View logs: `tail -f logs/suntory.log`
- Check configuration: `cat .env`
- Run tests: `pytest tests/`

## Pro Tips

💡 **Alfred auto-detects complexity** - no need to specify mode for most tasks

💡 **Use `/team` prefix** for guaranteed team orchestration

💡 **Switch models mid-conversation** - try different models for different tasks

💡 **Alfred learns from conversations** - he gets better over time (with `ENABLE_AGENT_MEMORY=true`)

💡 **Use Markdown in queries** - Alfred renders responses beautifully

---

**Ready to build something remarkable?**

```bash
./Suntory.sh
```

🥃 *Smooth, refined, production-ready.*

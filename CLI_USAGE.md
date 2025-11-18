# Yamazaki V2 - Interactive CLI Usage Guide

## Quick Start

Run the interactive CLI:

```bash
python -m v2.cli
```

Or use the convenience script:

```bash
./run_cli.sh
```

## Available Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help message with all commands |
| `/agents` | List all available agents with descriptions |
| `/tools` | List all available tools |
| `/info` | Show system configuration and status |
| `/clear` | Clear the screen |
| `/exit` or `/quit` | Exit the CLI |

## How to Use

### 1. **Ask Questions Directly**

Just type your question naturally:

```
You: What's the weather in Seattle?
Yamazaki: [Agent: weather] I would help you with: What's the weather in Seattle?
```

```
You: What can you do?
Yamazaki: [Agent: orchestrator] I can help you with various tasks...
```

### 2. **Explore Available Agents**

Use `/agents` to see what agents are available:

```
You: /agents

┌──────────────────────────────────────────────────────────────────┐
│                        Available Agents                          │
├───────────────┬────────────┬────────────────────┬─────────────────┤
│ Name          │ Category   │ Description        │ Version         │
├───────────────┼────────────┼────────────────────┼─────────────────┤
│ weather       │ weather    │ Weather expert...  │ 1.0.0           │
│ data_analyst  │ data       │ Data analyst...    │ 1.0.0           │
│ orchestrator  │ orchestr.. │ Strategic planner  │ 1.0.0           │
└───────────────┴────────────┴────────────────────┴─────────────────┘
```

### 3. **Check System Info**

Use `/info` to see configuration:

```
You: /info

System Information:

  Environment: development
  Default Provider: azure
  Database: sqlite:///./data/yamazaki.db
  Log Level: INFO
  Security Audit: Enabled

Agents: 3 registered
Tools: 0 registered
```

### 4. **Agent Selection**

The CLI automatically selects the best agent based on your query:

- **Weather queries** → `weather` agent
  - Keywords: weather, forecast, temperature, rain

- **Data queries** → `data_analyst` agent
  - Keywords: database, query, data, sql, analyze

- **General queries** → `orchestrator` agent
  - Everything else

## Examples

### Weather Questions
```
You: What's the weather in New York?
You: Will it rain tomorrow in Seattle?
You: What's the temperature in Miami?
```

### Data Questions
```
You: Query the database for user statistics
You: Analyze the sales data
You: Show me the database schema
```

### General Questions
```
You: What can you do?
You: Help me plan a project
You: List all available capabilities
```

## Tips

1. **Start with `/help`** to see all available commands
2. **Use `/agents`** to understand what each agent can do
3. **Type naturally** - the system will route to the appropriate agent
4. **Use Ctrl+C** then `/exit` if you accidentally interrupt

## Current Limitations

- Agent responses are currently placeholder text
- Full agent execution (with actual LLM calls) coming in next version
- Tool execution not yet implemented in CLI mode

## What's Next?

Future versions will include:
- Full agent execution with real LLM responses
- Conversation history
- Multi-agent collaboration
- Tool execution in CLI
- Session persistence
- Custom agent selection

---

**Enjoy using Yamazaki V2!** 🥃

# 🤖 AutoGen CLI Agent

A Claude-style command-line interface powered by your custom AutoGen multi-agent backend with Azure OpenAI.

## Features

✨ **Rich Terminal Interface** - Beautiful, interactive CLI with real-time streaming responses
🤖 **Multiple Agent Teams** - Switch between different agent configurations on the fly
💬 **Interactive Chat Mode** - Continuous conversation with conversation history
⚡ **Single-Shot Mode** - Quick one-off queries without entering interactive mode
📝 **Session Persistence** - Automatic conversation history saving
🔧 **Highly Configurable** - CLI arguments and environment-based configuration
🎯 **Tool Calling** - Agents can use tools like weather APIs with visual feedback
🌐 **Multi-Provider Support** - Azure OpenAI, OpenAI, Google Gemini

## Quick Start

### 1. Setup

```bash
# Install dependencies and setup CLI
./setup_cli.sh
```

### 2. Configure Environment

Create a `.env` file in the project root:

```bash
AZURE_OPENAI_API_KEY=your_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
```

### 3. Run the CLI

```bash
# Interactive mode
./cli.py

# Single-shot query
./cli.py "What's the weather like?"

# Use specific agent team
./cli.py --team simple "Write a Python function to calculate fibonacci numbers"

# Show help
./cli.py --help
```

## Usage

### Interactive Mode

Start an interactive session with your agents:

```bash
./cli.py
```

**Available Commands:**
- `/help` - Show help message
- `/clear` - Clear the screen
- `/history` - Show conversation history
- `/team [name]` - Switch agent team (weather, simple)
- `/config` - Show current configuration
- `/exit` or `exit` - Exit the CLI
- `TERMINATE` - End the current conversation

**Example Session:**
```
You: What's the weather?
[Weather_Agent uses get_local_forecast tool...]
[Executive_Assistant relays forecast to you...]

You: Tell me a joke about that weather
[Joke_Agent responds with weather-themed humor...]

You: exit
Goodbye! 👋
```

### Single-Shot Mode

Execute a single query and exit:

```bash
./cli.py "What's the weather forecast?"
./cli.py "Tell me a joke"
./cli.py "Explain how async/await works in Python"
```

### Command-Line Options

```
./cli.py [OPTIONS] [QUERY]

Positional Arguments:
  QUERY                 Single query to execute (omit for interactive mode)

Options:
  -t, --team {weather,simple}
                        Agent team to use (default: weather)
  -p, --provider {azure,openai,google}
                        Model provider (default: azure)
  --no-history          Disable conversation history saving
  --history             Show conversation history and exit
  -v, --verbose         Enable verbose output
  --version             Show version and exit
  -h, --help            Show help message
```

### Agent Teams

#### **Weather Team** (Default)
Multi-agent team with:
- **Weather_Agent** - Fetches weather forecasts, analyzes kite-flying conditions
- **Joke_Agent** - Tells jokes and makes puns
- **Executive_Assistant** - Routes tasks and coordinates agents
- **Human_Admin** - Human-in-the-loop interaction

Best for: General conversation, weather queries, entertainment

```bash
./cli.py --team weather
```

#### **Simple Team**
Single general-purpose assistant agent.

Best for: Coding help, explanations, single-agent tasks

```bash
./cli.py --team simple "Explain decorators in Python"
```

## Examples

### Check Weather and Get a Related Joke

```bash
./cli.py
You: What's the weather?
# [Agent fetches weather...]

You: Tell me a joke about that
# [Agent tells weather-related joke...]
```

### Quick Code Explanation

```bash
./cli.py --team simple "Explain list comprehensions in Python with examples"
```

### View Conversation History

```bash
./cli.py --history
```

### Use Different Provider

```bash
./cli.py --provider openai "Hello!"
```

## Architecture

### Component Overview

```
cli.py                          # Main CLI interface
├── CLIAgent                    # Core CLI agent class
│   ├── Interactive Mode        # Continuous conversation loop
│   ├── Single-Shot Mode        # One-off query execution
│   └── History Management      # Conversation persistence
│
agents/weather_agents.py        # Agent factory functions
├── create_weather_agent_team() # Multi-agent team builder
├── create_simple_assistant()   # Single agent builder
└── Individual agent creators   # Weather, Joke, Exec, User agents
│
config/settings.py              # Configuration management
└── get_llm_config()           # Provider-specific config loader
```

### How It Works

1. **CLI Initialization**
   - Parses command-line arguments
   - Loads configuration from environment
   - Creates CLIAgent instance

2. **Agent Team Creation**
   - Loads LLM config for specified provider
   - Creates ChatCompletionClient
   - Builds agent team (multi-agent or single-agent)

3. **Interactive Loop**
   - Prompts user for input
   - Handles commands (/help, /clear, etc.)
   - Routes queries to agent team
   - Streams responses in real-time
   - Saves to conversation history

4. **Agent Orchestration** (Weather Team)
   - SelectorGroupChat manages agent routing
   - Selector prompt determines which agent responds
   - Max 12 turns with TERMINATE condition
   - No repeated speakers for agent diversity

## Configuration

### Environment Variables

Required for Azure OpenAI:
```bash
AZURE_OPENAI_API_KEY         # Your Azure OpenAI API key
AZURE_OPENAI_ENDPOINT        # Your Azure OpenAI endpoint URL
AZURE_OPENAI_DEPLOYMENT_NAME # Deployment name (optional, defaults to StellaSource-GPT4o)
```

### Configuration Files

- `.env` - Environment variables (gitignored)
- `~/.autogen_cli/history.jsonl` - Conversation history (auto-created)

### Supported Providers

1. **Azure OpenAI** (Default)
   - Requires: AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT
   - Models: GPT-4, GPT-4o, etc.

2. **OpenAI**
   - Requires: OPENAI_API_KEY
   - Models: GPT-4, GPT-3.5-turbo, etc.

3. **Google Gemini**
   - Requires: GOOGLE_API_KEY
   - Models: Gemini Pro, etc.

## Extending the CLI

### Add a New Agent

1. Create agent factory function in `agents/weather_agents.py`:

```python
def create_code_agent(model_client: ChatCompletionClient) -> AssistantAgent:
    return AssistantAgent(
        name="Code_Agent",
        model_client=model_client,
        system_message="You are an expert programmer...",
        tools=[...]  # Add tools if needed
    )
```

2. Add to team creation function:

```python
async def create_weather_agent_team(llm_config: dict) -> SelectorGroupChat:
    # ...existing code...
    code_agent = create_code_agent(ai_client)

    team = SelectorGroupChat(
        participants=[weather_agent, code_agent, joke_agent, exec_agent, user_proxy],
        # ...rest of config...
    )
```

### Add a New Tool

1. Create tool function in `agents/` directory:

```python
async def my_new_tool(param: str) -> str:
    """Tool description for the agent."""
    # Your tool implementation
    return result
```

2. Add to agent:

```python
from autogen_core.tools import FunctionTool

agent = AssistantAgent(
    tools=[FunctionTool(my_new_tool, description="Tool description")],
    reflect_on_tool_use=True
)
```

### Add a New Team Configuration

1. Create team factory function:

```python
async def create_my_custom_team(llm_config: dict) -> SelectorGroupChat:
    # ...create your agents...
    return SelectorGroupChat(participants=[...], ...)
```

2. Update CLI to support new team:

```python
# In cli.py, add to team choices and creation logic
if self.team_name == "custom":
    team = await create_my_custom_team(llm_config)
```

## Troubleshooting

### "Error loading configuration"

- Check that `.env` file exists with required variables
- Verify API keys are correct
- Ensure endpoint URL is properly formatted

### "Error creating agent team"

- Check that all dependencies are installed
- Verify Azure/OpenAI deployment is accessible
- Try with `--verbose` flag for detailed error messages

### Import Errors

```bash
# Reinstall dependencies
pip3 install -r requirements.txt
```

### History Not Saving

- Check that `~/.autogen_cli/` directory is writable
- Try running with `--no-history` to disable

## Development

### Project Structure

```
AutoGen/
├── cli.py                    # Main CLI entry point
├── setup_cli.sh              # Setup script
├── CLI_README.md             # This file
├── main.py                   # Original entry point
├── weather_orchestrator.py   # Original orchestrator
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (create this)
│
├── agents/
│   ├── weather_agents.py     # Agent factory functions
│   └── weather_tool.py       # Weather API tool
│
├── config/
│   └── settings.py           # Configuration management
│
└── services/
    └── ai_services.py        # AI service utilities
```

### Contributing

To add new features:

1. Create a feature branch
2. Add your changes (agents, tools, commands)
3. Test thoroughly
4. Update this README
5. Submit a pull request

## License

See main project LICENSE file.

## Support

For issues or questions:
- Check the `/help` command in the CLI
- Review this README
- Check AutoGen documentation: https://microsoft.github.io/autogen/

---

**Built with:**
- [AutoGen](https://microsoft.github.io/autogen/) - Multi-agent framework
- [Azure OpenAI](https://azure.microsoft.com/en-us/products/ai-services/openai-service) - LLM backend
- [Rich](https://rich.readthedocs.io/) - Terminal UI
- [Python AsyncIO](https://docs.python.org/3/library/asyncio.html) - Async runtime

Enjoy your CLI agent! 🚀

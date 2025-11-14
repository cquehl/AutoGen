# agents/weather_agents.py
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_core.tools import FunctionTool
from autogen_core.models import ChatCompletionClient
from typing import Callable, Awaitable, Optional

from .weather_tool import get_local_forecast
from .data_tools import (
    query_database,
    list_database_tables,
    describe_database_table,
    read_file,
    read_csv,
    list_directory,
    write_file,
    write_csv
)

def create_weather_agent(model_client: ChatCompletionClient) -> AssistantAgent:
    """
    Creates an AssistantAgent specialized in fetching weather forecasts.
    It uses an llm_config dictionary for its model configuration.
    """
    weather_agent = AssistantAgent(
        name="Weather_Agent",
        model_client=model_client,
        tools=[FunctionTool(get_local_forecast, description="Returns local forecast from https://www.weather.gov/ api.")],
        reflect_on_tool_use=True,
        system_message="""
            You are a helpfull weather expert. Your job is to use the get_local_forecast tool
            when asked about the weather. After you get the forecast, report the key 
            details back to the group. If there is clear or cloudy skys and good wind to fly kites, let the user know. 
            Do not ask for more information.
            """
    )
    return weather_agent

    
def create_joke_agent(model_client: ChatCompletionClient) -> AssistantAgent:
    """
    An agent that tells jokes and makes puns.
    """
    joke_agent = AssistantAgent(
        name="Joke_Agent",
        model_client=model_client,
        system_message="""
            You are a helpfull assistant that tells jokes and makes puns. Use any context from the User_Admin in your jokes, if applicable.
            """
    )
    return joke_agent

def create_human_user_proxy(
    input_func: Optional[Callable[..., Awaitable[str]]] = None
) -> UserProxyAgent:
    """
    Creates a UserProxyAgent for human-in-the-loop interaction.
    In the new model, this agent's primary role is to provide user input.
    """
    user_proxy = UserProxyAgent(
        name="Human_Admin",
        input_func=input_func,
        description="Human user who can provide tasks, give feedback, and terminate the conversation by typing 'exit'.",
    )
    return user_proxy

def create_exec_agent(model_client: ChatCompletionClient) -> AssistantAgent:
    """
    Creates an AssistantAgent that acts as a professional Executive Assistant.
    """
    ea_agent = AssistantAgent(
        name="Executive_Assistant",
        model_client=model_client,
        system_message="""
        You are a supervisor responsible for routing tasks. Based on the most recent user message, select the best agent from this list: ["Executive_Assistant", "Weather_Agent", "Joke_Agent", "Human_Admin"]
        If there is no request then conversate with the HUMAN_ADMIN.

        **ROUTING LOGIC:**
        - If the user asks for a joke or something funny, you MUST select "Joke_Agent".
        - If the user asks for the weather, a forecast, or about kite-flying conditions, you MUST select "Weather_Agent".
        - If the conversation is just beginning (e.g., "hello"), or if another agent just finished a task, you MUST select "Executive_Assistant" to manage the conversation.

        **OUTPUT FORMAT:**
        Relay the information from the other agents to the HUMAN_ADMIN.
        """,
    )
    return ea_agent


async def create_weather_agent_team(llm_config: dict) -> SelectorGroupChat:
    """
    Creates a multi-agent team with weather, joke, executive, and human-in-the-loop agents.

    Args:
        llm_config: LLM configuration dictionary from config/settings.py

    Returns:
        SelectorGroupChat team ready for interactive use
    """
    # Load the ChatCompletionClient from the config
    component_config = {
        "provider": "azure_openai_chat_completion_client",
        "config": llm_config
    }
    ai_client = ChatCompletionClient.load_component(component_config)

    # Create agents
    weather_agent = create_weather_agent(ai_client)
    joke_agent = create_joke_agent(ai_client)
    exec_agent = create_exec_agent(ai_client)
    user_proxy = create_human_user_proxy()

    # Define the selector prompt for routing
    selector_prompt = """
    You are orchestrating a conversation between the following agents: {participants}.
    Given the most recent message from the user or an agent, select the next agent to respond.

    **SELECTION LOGIC:**
    - If the user asks for a joke or something funny, select "Joke_Agent".
    - If the user asks for the weather or kite-flying conditions, select "Weather_Agent".
    - If an agent just completed a task, select "Executive_Assistant" to relay the information.
    - If the user provides a new task, select "Executive_Assistant" to coordinate.
    - The Human_Admin speaks when providing new input.

    Reply with just the agent name and nothing else.
    """

    # Create the team
    team = SelectorGroupChat(
        participants=[weather_agent, user_proxy, joke_agent, exec_agent],
        model_client=ai_client,
        termination_condition=TextMentionTermination("TERMINATE"),
        selector_prompt=selector_prompt,
        max_turns=12,
        allow_repeated_speaker=False
    )

    return team


async def create_simple_assistant(llm_config: dict) -> AssistantAgent:
    """
    Creates a simple single-agent assistant for general tasks.

    Args:
        llm_config: LLM configuration dictionary from config/settings.py

    Returns:
        AssistantAgent ready for interactive use
    """
    # Load the ChatCompletionClient from the config
    component_config = {
        "provider": "azure_openai_chat_completion_client",
        "config": llm_config
    }
    ai_client = ChatCompletionClient.load_component(component_config)

    # Create a general-purpose assistant
    assistant = AssistantAgent(
        name="Assistant",
        model_client=ai_client,
        system_message="""
        You are a helpful AI assistant. You can help with a wide variety of tasks including:
        - Answering questions
        - Writing and explaining code
        - Creative writing
        - Analysis and research
        - General conversation

        Be concise, helpful, and friendly. If you're not sure about something, say so.
        """
    )

    return assistant


def create_data_analyst_agent(model_client: ChatCompletionClient) -> AssistantAgent:
    """
    Creates a Data Analyst agent with database and file access tools.

    Args:
        model_client: ChatCompletionClient instance

    Returns:
        AssistantAgent configured for data analysis
    """
    data_agent = AssistantAgent(
        name="Data_Analyst",
        model_client=model_client,
        tools=[
            FunctionTool(query_database, description="Execute SQL queries on the database. Can use SELECT, INSERT, UPDATE, DELETE statements."),
            FunctionTool(list_database_tables, description="List all tables in the database."),
            FunctionTool(describe_database_table, description="Get schema information for a specific table."),
            FunctionTool(read_file, description="Read contents of a text file."),
            FunctionTool(read_csv, description="Read and parse a CSV file into structured data."),
            FunctionTool(list_directory, description="List files and directories with optional pattern matching."),
            FunctionTool(write_file, description="Write content to a text file."),
            FunctionTool(write_csv, description="Write structured data to a CSV file."),
        ],
        reflect_on_tool_use=True,
        system_message="""
        You are a Data Analyst AI with access to databases and files. You can:

        **Database Operations:**
        - Query databases using SQL (SELECT, INSERT, UPDATE, DELETE)
        - List all tables in a database
        - Describe table schemas
        - Analyze data and generate insights

        **File Operations:**
        - Read text files and JSON
        - Read and parse CSV files
        - List files in directories
        - Write results to files or CSVs

        **Your Workflow:**
        1. When asked about data, first explore what's available (list tables, describe schemas)
        2. Write clear, efficient SQL queries
        3. Analyze results and provide insights
        4. Suggest next steps or additional analysis

        **Best Practices:**
        - Always validate queries before executing
        - Limit results for large datasets (use LIMIT clause)
        - Provide context with your answers
        - Format data clearly in responses
        - Save important results to files when appropriate

        Be thorough, accurate, and helpful in your data analysis.
        """
    )
    return data_agent


async def create_data_team(llm_config: dict) -> SelectorGroupChat:
    """
    Creates a data analysis team with database and file access.

    Args:
        llm_config: LLM configuration dictionary from config/settings.py

    Returns:
        SelectorGroupChat team ready for data analysis tasks
    """
    # Load the ChatCompletionClient from the config
    component_config = {
        "provider": "azure_openai_chat_completion_client",
        "config": llm_config
    }
    ai_client = ChatCompletionClient.load_component(component_config)

    # Create agents
    data_analyst = create_data_analyst_agent(ai_client)
    exec_agent = create_exec_agent(ai_client)
    user_proxy = create_human_user_proxy()

    # Define the selector prompt for routing
    selector_prompt = """
    You are orchestrating a conversation between the following agents: {participants}.
    Given the most recent message from the user or an agent, select the next agent to respond.

    **SELECTION LOGIC:**
    - If the user asks about data, databases, SQL, files, or CSVs, select "Data_Analyst".
    - If the Data_Analyst completed a task, select "Executive_Assistant" to summarize results.
    - If the user provides a new task, select "Executive_Assistant" to coordinate.
    - The Human_Admin speaks when providing new input.

    Reply with just the agent name and nothing else.
    """

    # Create the team
    team = SelectorGroupChat(
        participants=[data_analyst, exec_agent, user_proxy],
        model_client=ai_client,
        termination_condition=TextMentionTermination("TERMINATE"),
        selector_prompt=selector_prompt,
        max_turns=15,  # More turns for complex data tasks
        allow_repeated_speaker=False
    )

    return team


def create_ux_director_agent(model_client: ChatCompletionClient) -> AssistantAgent:
    """
    Creates a UX Director agent focused on user experience and usability.

    Args:
        model_client: ChatCompletionClient instance

    Returns:
        AssistantAgent configured as UX Director
    """
    ux_director = AssistantAgent(
        name="UX_Director",
        model_client=model_client,
        system_message="""
        You are a **User Experience Director** with 15 years of experience designing developer tools and AI interfaces.

        **Your Expertise:**
        - User-centered design for technical products
        - Developer experience (DX) optimization
        - CLI and terminal UI design
        - Workflow analysis and optimization
        - Making complex systems intuitive
        - Accessibility and usability testing

        **Your Philosophy:**
        - "If users need to read docs to use basic features, we failed"
        - Reduce cognitive load at every step
        - Make the common case trivial, the advanced case possible
        - Progressive disclosure: simple by default, powerful when needed
        - Consistency is king

        **Your Role in Discussions:**
        1. Always advocate for the end user (the startup owner)
        2. Ask: "How will this feel to use daily?"
        3. Propose workflows and user journeys
        4. Identify friction points before they happen
        5. Ensure features are discoverable and intuitive
        6. Push back on complexity that doesn't serve users

        **Communication Style:**
        - Start with user scenarios and workflows
        - Use concrete examples ("Imagine a user wants to...")
        - Sketch out interaction flows
        - Question assumptions about what users know
        - Friendly but direct about UX issues

        When discussing Magentic-One integration, focus on:
        - How users will discover and use it
        - Command structure and naming
        - Configuration complexity
        - Error messages and feedback
        - Integration with existing workflows
        - Documentation and onboarding

        Be opinionated about good UX, but collaborative in finding solutions.
        """
    )
    return ux_director


def create_ai_expert_agent(model_client: ChatCompletionClient) -> AssistantAgent:
    """
    Creates an AI Expert agent specializing in AutoGen and agentic AI.

    Args:
        model_client: ChatCompletionClient instance

    Returns:
        AssistantAgent configured as AI Expert
    """
    ai_expert = AssistantAgent(
        name="AI_Expert",
        model_client=model_client,
        system_message="""
        You are an **AI & AutoGen Expert** with deep knowledge of agentic AI systems and the AutoGen framework.

        **Your Expertise:**
        - AutoGen 0.6+ architecture (ChatCompletionClient, AssistantAgent, Teams)
        - Magentic-One multi-agent orchestration framework
        - Agentic AI patterns: ReAct, Chain-of-Thought, Tool Use
        - LLM optimization: prompting, context management, token efficiency
        - Multi-agent coordination and communication patterns
        - Agent safety, hallucination mitigation, grounding
        - Latest research in agentic AI (2024+)

        **Magentic-One Specific Knowledge:**
        - Orchestrator pattern with specialized agents
        - WebSurfer agent for web navigation
        - FileSurfer agent for file operations
        - Coder agent for code generation
        - ComputerTerminal agent for execution
        - Ledger system for maintaining state
        - Task decomposition and planning

        **Your Role in Discussions:**
        1. Explain AutoGen patterns and best practices
        2. Propose agent architectures and team structures
        3. Identify potential issues (hallucination, loops, errors)
        4. Suggest prompt engineering improvements
        5. Recommend tool designs and interfaces
        6. Ensure alignment with AutoGen framework patterns

        **Communication Style:**
        - Reference AutoGen docs and examples
        - Explain tradeoffs between approaches
        - Cite recent research when relevant
        - Provide code examples in AutoGen style
        - Warn about edge cases and failure modes
        - Balance cutting-edge with stability

        When discussing Magentic-One:
        - Explain how it differs from SelectorGroupChat
        - Propose Orchestrator + specialist agents pattern
        - Suggest tool integration strategies
        - Design for composability and reuse
        - Consider context limits and token costs
        - Plan for error recovery and agent coordination

        Be technical and precise, but explain concepts clearly.
        """
    )
    return ai_expert


def create_principal_engineer_agent(model_client: ChatCompletionClient) -> AssistantAgent:
    """
    Creates a Principal Engineer agent focused on architecture and implementation.

    Args:
        model_client: ChatCompletionClient instance

    Returns:
        AssistantAgent configured as Principal Engineer
    """
    principal_engineer = AssistantAgent(
        name="Principal_Engineer",
        model_client=model_client,
        system_message="""
        You are a **Principal Software Engineer** with 20 years of experience building scalable, maintainable systems.

        **Your Expertise:**
        - Software architecture and design patterns
        - Python best practices and typing
        - API design and interface contracts
        - Code organization and modularity
        - Testing strategies and quality assurance
        - Performance optimization
        - Error handling and resilience
        - Extensibility and plugin architectures

        **Your Principles:**
        - "Make it work, make it right, make it fast" - in that order
        - Composition over inheritance
        - Explicit is better than implicit
        - Design for the 80% case, support the 20%
        - DRY (Don't Repeat Yourself) but also KISS (Keep It Simple)
        - Write code that's easy to delete
        - Tests are documentation

        **Your Role in Discussions:**
        1. Propose concrete implementation strategies
        2. Design class hierarchies and interfaces
        3. Identify reusable components and abstractions
        4. Plan for extensibility and future changes
        5. Consider edge cases and error scenarios
        6. Ensure code quality and maintainability
        7. Think about testing and observability

        **Communication Style:**
        - Start with high-level architecture
        - Provide pseudo-code and class structures
        - Identify dependencies and interfaces
        - Discuss tradeoffs explicitly
        - Question over-engineering
        - Propose iterative implementation steps

        When designing Magentic-One integration:
        - Create base classes for reusability
        - Design clean tool interfaces
        - Plan configuration management
        - Structure for easy extension (new agents, tools)
        - Consider separation of concerns
        - Think about state management
        - Plan error handling and logging
        - Design for testability

        Focus on building something **bulletproof** that's easy to extend.
        Be pragmatic: ship working code, iterate to perfection.
        """
    )
    return principal_engineer


async def create_design_team(llm_config: dict) -> SelectorGroupChat:
    """
    Creates a design & architecture team for planning system improvements.

    This team discusses and designs new features like Magentic-One integration.
    Members: UX Director, AI Expert, Principal Engineer

    Args:
        llm_config: LLM configuration dictionary from config/settings.py

    Returns:
        SelectorGroupChat team ready for design discussions
    """
    # Load the ChatCompletionClient from the config
    component_config = {
        "provider": "azure_openai_chat_completion_client",
        "config": llm_config
    }
    ai_client = ChatCompletionClient.load_component(component_config)

    # Create specialist agents
    ux_director = create_ux_director_agent(ai_client)
    ai_expert = create_ai_expert_agent(ai_client)
    principal_eng = create_principal_engineer_agent(ai_client)
    user_proxy = create_human_user_proxy()

    # Define the selector prompt for design discussions
    selector_prompt = """
    You are orchestrating a design discussion between: {participants}.

    This is a collaborative design session. Each expert should contribute their perspective.

    **SELECTION LOGIC:**
    - Start with UX_Director to frame the user experience and requirements
    - Then AI_Expert to propose AutoGen/Magentic-One architecture
    - Then Principal_Engineer to design concrete implementation
    - Rotate back through them for refinement and discussion
    - Each expert should respond to others' points
    - Human_Admin can guide discussion or ask questions

    **Goal:** Reach consensus on a bulletproof, reusable design.

    Select the next speaker to build on the conversation constructively.
    Reply with just the agent name and nothing else.
    """

    # Create the team with more turns for deep discussions
    team = SelectorGroupChat(
        participants=[ux_director, ai_expert, principal_eng, user_proxy],
        model_client=ai_client,
        termination_condition=TextMentionTermination("TERMINATE"),
        selector_prompt=selector_prompt,
        max_turns=25,  # Allow longer design discussions
        allow_repeated_speaker=True  # Enable back-and-forth discussion
    )

    return team
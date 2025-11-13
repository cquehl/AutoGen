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
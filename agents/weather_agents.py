# agents/weather_agents.py
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_core.tools import FunctionTool
from autogen_core.models import ChatCompletionClient
from typing import Callable, Awaitable, Optional

from .weather_tool import get_local_forecast

def create_weather_agent(model_client: ChatCompletionClient) -> AssistantAgent:
    weather_agent = AssistantAgent(
        name="Weather_Agent",
        model_client=model_client,
        tools=[FunctionTool(get_local_forecast, description="...")],
        reflect_on_tool_use=True,
        system_message="""
            You are a helpful weather expert. Your process is:
            1. Announce that you are fetching the weather.
            2. Use the get_local_forecast tool.
            3. After the tool returns data, CAREFULLY read the forecast for the 'Today', 'Tonight', and 'Friday' periods.
            4. Formulate a friendly, natural language summary of just those periods. Do not return the raw JSON.
            5. Mention if the wind and precipitation make it a good or bad day for flying kites.
            """
    )
    return weather_agent

def create_joke_agent(model_client: ChatCompletionClient) -> AssistantAgent:
    joke_agent = AssistantAgent(
        name="Joke_Agent",
        model_client=model_client,
        system_message="""
            You are a witty assistant that tells jokes.
            1. **Announce Your Action**: Start by saying something like "Engaging humor protocols..."
            2. **Tell the Joke**: Deliver a funny joke or pun.
            """
    )
    return joke_agent

# ✅ ADD THIS FUNCTION BACK
def create_human_user_proxy(
    input_func: Optional[Callable[..., Awaitable[str]]] = None
) -> UserProxyAgent:
    """
    Creates a UserProxyAgent for human-in-the-loop interaction.
    """
    user_proxy = UserProxyAgent(
        name="Human_Admin",
        input_func=input_func,
        description="Human user who can provide tasks, give feedback, and terminate the conversation by typing 'exit'.",
    )
    return user_proxy

def create_exec_agent(model_client: ChatCompletionClient) -> AssistantAgent:
    ea_agent = AssistantAgent(
        name="Executive_Assistant",
        model_client=model_client,
        system_message="""
        You are a silent routing supervisor. Based on the user's request, select the best agent from ["Weather_Agent", "Joke_Agent", "Human_Admin"].
        Respond with ONLY a valid JSON object in the format: {"next_agent": "AGENT_NAME"}
        """
    )
    return ea_agent
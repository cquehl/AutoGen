# agents/weather_agents.py
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_core.tools import FunctionTool
from autogen_core.models import ChatCompletionClient
from typing import Callable, Awaitable, Optional, Any

from .weather_tool import get_local_forecast

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

        **ROUTING LOGIC:**
        - If the user asks for a joke or something funny, you MUST select "Joke_Agent".
        - If the user asks for the weather, a forecast, or about kite-flying conditions, you MUST select "Weather_Agent".
        - If the conversation is just beginning (e.g., "hello"), or if another agent just finished a task, you MUST select "Executive_Assistant" to manage the conversation.

        **OUTPUT FORMAT:**
        Respond with ONLY the name of the agent you have selected. Do not add any other text, explanation, or punctuation. For example, if the user asks for a joke, your entire response must be only "Joke_Agent".
        """,
    )
    return ea_agent
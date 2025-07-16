# agents/weather_agents.py
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_core.tools import FunctionTool
from autogen_core.models import ChatCompletionClient
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
            details back to the group. If there is rain or storms in the forcast, let the user know.
            If there is clear or cloudy skys and good wind to fly kites, let the user know. Do not ask for more information.
            """
    )
    
    
    return weather_agent

def create_human_user_proxy() -> UserProxyAgent:
    """
    Creates a UserProxyAgent for human-in-the-loop interaction.
    In the new model, this agent's primary role is to provide user input.
    """
    user_proxy = UserProxyAgent(
        name="Human_Admin",
        # human_input_mode="ALWAYS",
        # code_execution_config={"use_docker": False},
        # system_message=(
        #     "You are the user's representative. You will be prompted for input to "
        #     "continue the conversation. You must execute the tool calls."
        # )
    )
    return user_proxy

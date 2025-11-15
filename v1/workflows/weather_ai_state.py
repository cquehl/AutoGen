# workflows/weather_ai.py

import asyncio
import httpx
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

# The tool definition remains the same
async def get_local_forecast() -> dict | str:
    """
    Gets the 7-day weather forecast for a predefined location
    (Turpin Hills, OH gridpoint).
    Returns the full JSON 'properties' object from the weather.gov API.
    """
    forecast_url = "https://api.weather.gov/gridpoints/ILN/36,41/forecast"
    headers = { "User-Agent": "AutoGenWeatherAgent (contact: your_email@example.com)" }

    try:
        print("TOOL CALLED")
        async with httpx.AsyncClient(headers=headers) as client:
            response = await client.get(forecast_url)
            response.raise_for_status()
            forecast_data = response.json()
            return forecast_data["properties"]
    except httpx.HTTPStatusError as e:
        return f"Error fetching weather data: {e.response.status_code}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"

async def run(client: OpenAIChatCompletionClient):
    """
    Executes the weather agent workflow using a provided client.
    """
    print("\n--- Starting Weather Agent Workflow ---")
    
    # Use the client passed from the orchestrator
    model_client = client
    
    # Define the AssistantAgent
    agent = AssistantAgent(
        name="weather_agent",
        model_client=model_client,
        tools=[get_local_forecast],
        system_message="""You are a helpful assistant that tells the user about their local weather forecast
            in Turpin Hills, Ohio. Use the get_local_forecast tool to get the data.""",
        reflect_on_tool_use=True,
        model_client_stream=True,
    )

    # Run the agent and stream the messages to the console
    await Console(agent.run_stream(task="What is the weather in Turpin Hills, Ohio?"))
    
    print("--- Weather Agent Workflow Finished ---")
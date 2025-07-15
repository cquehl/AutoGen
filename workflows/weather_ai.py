import asyncio

import httpx
from config.settings import check_ip_address, get_gemini_client
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient


    # Define a simple function tool that the agent can use.
async def get_local_forecast() -> dict | str:
    """
    Gets the 7-day weather forecast for a predefined location
    (Turpin Hills, OH gridpoint).
    Returns the full JSON 'properties' object from the weather.gov API.
    """
    # This URL is for the specific gridpoint ILN/36,41
    forecast_url = "https://api.weather.gov/gridpoints/ILN/36,41/forecast"
    
    headers = {
        "User-Agent": "AutoGenWeatherAgent (contact: your_email@example.com)"
    }

    try:
        print("TOOL CALLED")
        async with httpx.AsyncClient(headers=headers) as client:
            response = await client.get(forecast_url)
            response.raise_for_status()  # Raise an exception for bad status codes
            forecast_data = response.json()
            # Return the useful part of the JSON response
            return forecast_data["properties"]
            
    except httpx.HTTPStatusError as e:
        return f"Error fetching weather data: {e.response.status_code}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"

async def start_workflows():
    """
    Initializes the application and runs the selected workflows.
    """
    # --- 1. Perform Startup Checks & Get Client ---
    print("--- Running Startup Checks ---")
    check_ip_address()
    gemini_client = get_gemini_client()
    print("--- Client Initialized ---\n")
    
    # Define a model client. You can use other model client that implements
    # the `ChatCompletionClient` interface.
    model_client = gemini_client
    
    # Define an AssistantAgent with the model, tool, system message, and reflection enabled.
    # The system message instructs the agent via natural language.
    agent = AssistantAgent(
        name="weather_agent",
        model_client=model_client,
        tools=[get_local_forecast],
        system_message="""You are a helpful assistant that tells the user about their local weather forecast
            in Turpin Hills, Ohio. Use the get_local_forecast tool to get the data.""",
        reflect_on_tool_use=True,
        model_client_stream=True,  # Enable streaming tokens from the model client.
    )


    # Run the agent and stream the messages to the console.
    async def main() -> None:
        await Console(agent.run_stream(task="What is the weather in Turpin Hills, Ohio?"))
        # Close the connection to the model client.
        await model_client.close()


    await main()

if __name__ == "__main__":
    asyncio.run(start_workflows())
# agents/weather_tool.py
import httpx

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
        print("--- Calling Weather Tool ---")
        async with httpx.AsyncClient(headers=headers) as client:
            response = await client.get(forecast_url)
            response.raise_for_status()
            forecast_data = response.json()
            return forecast_data["properties"]
            
    except httpx.HTTPStatusError as e:
        return f"Error fetching weather data: {e.response.status_code}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"

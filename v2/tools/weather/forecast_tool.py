"""
Yamazaki v2 - Weather Forecast Tool

Example tool using external API (weather.gov)
"""

import httpx
from typing import Optional

from ...core.base_tool import BaseTool, ToolResult, ToolCategory


class WeatherForecastTool(BaseTool):
    """
    Weather forecast tool using weather.gov API.

    Free API, no key required! Great example of external API integration.
    """

    NAME = "weather.forecast"
    DESCRIPTION = "Get weather forecast for a location using latitude/longitude from weather.gov API"
    CATEGORY = ToolCategory.WEATHER
    VERSION = "1.0.0"
    REQUIRES_SECURITY_VALIDATION = False

    async def execute(self, latitude: float, longitude: float) -> ToolResult:
        """
        Get weather forecast.

        Args:
            latitude: Latitude
            longitude: Longitude

        Returns:
            ToolResult with forecast data
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Step 1: Get grid point
                points_url = f"https://api.weather.gov/points/{latitude},{longitude}"
                response = await client.get(points_url, headers={
                    "User-Agent": "(Yamazaki v2, contact@example.com)"
                })
                response.raise_for_status()
                points_data = response.json()

                # Step 2: Get forecast
                forecast_url = points_data["properties"]["forecast"]
                response = await client.get(forecast_url, headers={
                    "User-Agent": "(Yamazaki v2, contact@example.com)"
                })
                response.raise_for_status()
                forecast_data = response.json()

                # Extract periods
                periods = forecast_data["properties"]["periods"][:5]  # Next 5 periods

                forecast = {
                    "location": {
                        "latitude": latitude,
                        "longitude": longitude,
                        "city": points_data["properties"]["relativeLocation"]["properties"]["city"],
                        "state": points_data["properties"]["relativeLocation"]["properties"]["state"],
                    },
                    "forecast": [
                        {
                            "name": p["name"],
                            "temperature": p["temperature"],
                            "temperature_unit": p["temperatureUnit"],
                            "wind_speed": p["windSpeed"],
                            "wind_direction": p["windDirection"],
                            "short_forecast": p["shortForecast"],
                            "detailed_forecast": p["detailedForecast"],
                        }
                        for p in periods
                    ]
                }

                return ToolResult.ok(forecast)

        except Exception as e:
            return ToolResult.error(f"Failed to get forecast: {str(e)}")

    def validate_params(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters"""
        latitude = kwargs.get("latitude")
        longitude = kwargs.get("longitude")

        if latitude is None or longitude is None:
            return False, "latitude and longitude are required"

        if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
            return False, "latitude and longitude must be numbers"

        if not (-90 <= latitude <= 90):
            return False, "latitude must be between -90 and 90"

        if not (-180 <= longitude <= 180):
            return False, "longitude must be between -180 and 180"

        return True, None

    def _get_parameters_schema(self) -> dict:
        """Get parameters schema"""
        return {
            "type": "object",
            "properties": {
                "latitude": {
                    "type": "number",
                    "description": "Latitude (-90 to 90)",
                    "minimum": -90,
                    "maximum": 90,
                },
                "longitude": {
                    "type": "number",
                    "description": "Longitude (-180 to 180)",
                    "minimum": -180,
                    "maximum": 180,
                },
            },
            "required": ["latitude", "longitude"],
        }


import sys
from pathlib import Path

parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

import httpx 
from config.settings import settings

async def get_weather(city: str) -> str:
    """
    Fetches the current weather for a given city.
    
    Args:
        city: The name of the city (e.g., 'London', 'Tokyo').
    """
    api_key = settings.OPENWEATHER_API_KEY
    base_url = "https://api.openweathermap.org/data/2.5/weather"
    
    # Using an AsyncClient is the standard way to handle async HTTP calls
    async with httpx.AsyncClient() as client:
        try:
            params = {
                'q': city,
                'appid': api_key,
                'units': 'metric'
            }
            
            # Use 'await' so the event loop can do other work while waiting
            response = await client.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Returning a clean string for the LLM to read
            return str({
                'city': data['name'],
                'country': data['sys']['country'],
                'temperature': f"{data['main']['temp']}°C",
                'conditions': data['weather'][0]['description'],
                'humidity': f"{data['main']['humidity']}%"
            })
            
        except httpx.HTTPStatusError as e:
            return f"Weather API error: {e.response.status_code} - {e.response.text}"
        except Exception as e:
            return f"Unexpected Error: {str(e)}"

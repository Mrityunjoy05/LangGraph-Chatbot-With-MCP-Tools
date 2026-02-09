
from config.settings import settings
import requests

def get_weather(city: str) -> str:
    """
    Get current weather for a city.
    
    Args:
        city: City name (e.g., 'London', 'Mumbai', 'New York')
    """
    api_key = settings.OPENWEATHER_API_KEY
    base_url = "https://api.openweathermap.org/data/2.5/weather"
    
    try:
        params = {
            'q': city,              # City name method (easier)
            'appid': api_key,
            'units': 'metric'       # Celsius (most common globally)
        }
        
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return str({
            'city': data['name'],
            'country': data['sys']['country'],
            'temperature': f"{data['main']['temp']}°C",  # Shows: 8.5°C
            'feels_like': f"{data['main']['feels_like']}°C",
            'conditions': data['weather'][0]['description'],
            'humidity': f"{data['main']['humidity']}%",
            'wind_speed': f"{data['wind']['speed']} m/s"
        })
        
    except Exception as e:
        return f"Error: {str(e)}"
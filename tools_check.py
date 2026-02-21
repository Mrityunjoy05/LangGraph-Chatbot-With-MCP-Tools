
from tools.weather import get_weather
from tools.search_tool import search_web_tavily

import asyncio

async def main():
    result1  = await get_weather(city="Kolkata")
    result2  = await search_web_tavily(query=" What is the capital of India")

    print(result1)
    print(result2)
    
asyncio.run(main())
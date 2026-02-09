from langchain_tavily import TavilySearch
import os
from config.settings import settings

async def search_web_tavily(query: str) -> str:
    """
    Searches the web using Tavily. Use this for real-time information.
    Args:
        query: The search string.
    """
    # Industry Practice: Set API keys via settings, but ensure environment is ready
    os.environ["TAVILY_API_KEY"] = settings.TAVILY_API_KEY
    
    try:
        search = TavilySearch(
            max_results=settings.K_SEARCH, # Use your settings variable
            topic="general"
        )
        results = await search.ainvoke(query)
    
        if not results:
            return "No search results found."
        
        formatted_parts = []
        
        # Add answer if available (Tavily AI summary)
        if isinstance(results, dict) and results.get("answer"):
            formatted_parts.append(f"Summary: {results['answer']}")
        
        # Add individual results
        # LangChain's TavilySearch usually returns a list or a dict with a 'results' key
        res_list = results.get("results") if isinstance(results, dict) else results
        
        if res_list and isinstance(res_list, list):
            for i, result in enumerate(res_list[:5], 1):
                title = result.get("title", "No title")
                content = result.get("content", "No content")
                url = result.get("url", "")
                formatted_parts.append(f"[{i}] {title}\n{content}\nSource: {url}")
        
        return "\n\n".join(formatted_parts) if formatted_parts else "No results found."
        
    except Exception as e:

        return f"Error searching Tavily: {str(e)}"
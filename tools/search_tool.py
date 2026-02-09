from langchain_tavily import TavilySearch
import os
from config.settings import settings


def search_web_tavily(query: str) -> str:
    """
    Search the web using Tavily for comprehensive results.
    
    Use this when you need detailed information from the internet.
    
    Args:
        query: The search query string
    """
    os.environ["TAVILY_API_KEY"] = settings.TAVILY_API_KEY
    try:
        
        search = TavilySearch(
            max_results = 5,
            topic = "general"
        )

        results = search.invoke(query)
    
        if not results:
            return "No search results found."
        
        formatted_parts = []
        
        # Add answer if available
        if results.get("answer"):
            formatted_parts.append(f"Summary: {results['answer']}")
        
        # Add individual results
        if results.get("results"):
            for i, result in enumerate(results["results"], 1):
                title = result.get("title", "No title")
                content = result.get("content", "No content")
                url = result.get("url", "")
                formatted_parts.append(f"[{i}] {title}\n{content}\nSource: {url}")
        
        return "\n\n".join(formatted_parts) if formatted_parts else "No results found."
    except Exception as e:
        return f"Error searching Tavily: {str(e)}"
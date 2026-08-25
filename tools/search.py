import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from langchain_core.tools import tool

from config.settings import settings

logger = logging.getLogger(__name__)


def _search_tavily(query: str) -> str:
    if not settings.TAVILY_API_KEY:
        return "Tavily: API key not configured."
    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        result = client.search(query=query, search_depth="advanced", max_results=5)
        snippets = []
        for item in result.get("results", []):
            title = item.get("title", "")
            content = item.get("content", "")
            url = item.get("url", "")
            snippets.append(f"• {title}: {content[:200]} ({url})")
        return "Tavily results:\n" + ("\n".join(snippets) if snippets else "No results.")
    except Exception as exc:
        logger.error("Tavily search failed: %s", exc)
        return f"Tavily: search failed ({exc})."


def _search_serper(query: str) -> str:
    if not settings.SERPER_API_KEY:
        return "Serper: API key not configured."
    try:
        response = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": settings.SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": 5},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        snippets = []
        for item in data.get("organic", []):
            snippets.append(f"• {item.get('title', '')}: {item.get('snippet', '')} ({item.get('link', '')})")
        return "Serper results:\n" + ("\n".join(snippets) if snippets else "No results.")
    except Exception as exc:
        logger.error("Serper search failed: %s", exc)
        return f"Serper: search failed ({exc})."


def _parallel_search(query: str) -> str:
    results = {}
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {
            pool.submit(_search_tavily, query): "tavily",
            pool.submit(_search_serper, query): "serper",
        }
        for future in as_completed(futures):
            results[futures[future]] = future.result()
    return f"{results.get('tavily', '')}\n\n{results.get('serper', '')}"


@tool
def web_health_search(query: str) -> str:
    """Search the web for current health information using Tavily and Serper in parallel.
    Use when you need up-to-date medical facts, treatment info, or general health guidance online."""
    health_query = f"health medical {query}"
    return _parallel_search(health_query)


@tool
def search_hospitals(location: str, symptoms: str = "") -> str:
    """Find hospitals and clinics near a location, optionally filtered by symptoms/specialty.
    Use when the user asks for nearby hospitals, doctors, or clinics."""
    if symptoms:
        query = f"best hospitals clinics for {symptoms} in {location} India contact address"
    else:
        query = f"hospitals clinics near {location} India contact address"
    return _parallel_search(query)

"""Tavily provider (free tier: 1000 credits/month)."""
import requests

from config import get_settings
from search.base import SearchProvider, SearchResult
from utils.logging import get_logger

log = get_logger(__name__)


class TavilyProvider(SearchProvider):
    name = "tavily"
    ENDPOINT = "https://api.tavily.com/search"

    def available(self) -> bool:
        return bool(get_settings().tavily_api_key)

    def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        cfg = get_settings()
        try:
            resp = requests.post(
                self.ENDPOINT,
                json={"api_key": cfg.tavily_api_key, "query": query, "max_results": max_results},
                timeout=cfg.request_timeout,
            )
            resp.raise_for_status()
            items = resp.json().get("results", [])
            return [SearchResult(title=i.get("title", ""), url=i.get("url", ""),
                                 snippet=i.get("content", "")) for i in items if i.get("url")]
        except Exception as exc:
            log.warning("Tavily search failed: %s", exc)
            return []

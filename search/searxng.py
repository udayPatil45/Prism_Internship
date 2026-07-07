"""SearxNG provider — fully free and open-source metasearch, no API key.
Point SEARXNG_URL at a self-hosted or public instance with JSON enabled."""
import requests

from config import get_settings
from search.base import SearchProvider, SearchResult
from utils.logging import get_logger

log = get_logger(__name__)


class SearxNGProvider(SearchProvider):
    name = "searxng"

    def available(self) -> bool:
        return bool(get_settings().searxng_url)

    def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        cfg = get_settings()
        try:
            resp = requests.get(
                cfg.searxng_url.rstrip("/") + "/search",
                params={"q": query, "format": "json"},
                headers={"User-Agent": cfg.user_agent},
                timeout=cfg.request_timeout,
            )
            resp.raise_for_status()
            items = resp.json().get("results", [])[:max_results]
            return [SearchResult(title=i.get("title", ""), url=i.get("url", ""),
                                 snippet=i.get("content", "")) for i in items if i.get("url")]
        except Exception as exc:
            log.warning("SearxNG search failed: %s", exc)
            return []

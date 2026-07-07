"""DuckDuckGo provider — fully free, no API key required. Default provider."""
from search.base import SearchProvider, SearchResult
from utils.logging import get_logger

log = get_logger(__name__)


class DuckDuckGoProvider(SearchProvider):
    name = "duckduckgo"

    def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        try:
            from ddgs import DDGS
        except ImportError:  # older package name still on some systems
            from duckduckgo_search import DDGS  # type: ignore
        results: list[SearchResult] = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    url = r.get("href") or r.get("url") or ""
                    if url:
                        results.append(SearchResult(
                            title=r.get("title", ""), url=url, snippet=r.get("body", "")))
        except Exception as exc:
            log.warning("DuckDuckGo search failed: %s", exc)
        return results

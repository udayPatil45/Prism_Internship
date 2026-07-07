"""Provider factory + automatic fallback chain (free providers only)."""
from config import get_settings
from search.base import SearchProvider, SearchResult
from search.duckduckgo import DuckDuckGoProvider
from search.searxng import SearxNGProvider
from search.tavily import TavilyProvider
from utils.logging import get_logger

log = get_logger(__name__)

_REGISTRY: dict[str, type[SearchProvider]] = {
    "duckduckgo": DuckDuckGoProvider,   # no key at all — default
    "tavily": TavilyProvider,           # free tier: 1000 credits/month, no card
    "searxng": SearxNGProvider,         # open-source, no key
}
_FALLBACK_ORDER = ["duckduckgo", "tavily", "searxng"]


def get_provider(name: str | None = None) -> SearchProvider:
    name = (name or get_settings().search_provider).lower()
    cls = _REGISTRY.get(name, DuckDuckGoProvider)
    provider = cls()
    if not provider.available():
        log.info("Provider '%s' unavailable — falling back to DuckDuckGo", name)
        provider = DuckDuckGoProvider()
    return provider


def search_with_fallback(query: str, max_results: int = 10) -> list[SearchResult]:
    """Try the configured provider first, then the remaining free providers."""
    tried: set[str] = set()
    order = [get_settings().search_provider.lower()] + _FALLBACK_ORDER
    for name in order:
        if name in tried or name not in _REGISTRY:
            continue
        tried.add(name)
        provider = _REGISTRY[name]()
        if not provider.available():
            continue
        results = provider.search(query, max_results=max_results)
        if results:
            log.info("Search via %s returned %d results", name, len(results))
            return results
    return []

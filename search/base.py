"""Abstract SearchProvider interface (Strategy pattern)."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str = ""


class SearchProvider(ABC):
    name: str = "base"

    @abstractmethod
    def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """Return a list of SearchResult for the query."""
        raise NotImplementedError

    def available(self) -> bool:
        """Whether this provider can be used (e.g. API key present)."""
        return True

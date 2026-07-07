"""Central configuration for PRISM, loaded from environment / .env file."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    search_provider: str = "duckduckgo"
    searxng_url: str = ""
    tavily_api_key: str = ""

    database_url: str = f"sqlite:///{DATA_DIR / 'prism.db'}"
    similarity_threshold: float = 0.85
    max_results_per_query: int = 10
    request_timeout: int = 15
    user_agent: str = "PRISM-ResearchBot/1.0"

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # credibility weights
    w_relevance: float = 0.45
    w_credibility: float = 0.35
    w_freshness: float = 0.20


@lru_cache
def get_settings() -> Settings:
    return Settings()

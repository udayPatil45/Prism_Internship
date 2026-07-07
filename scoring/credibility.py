"""Source credibility scoring.

FinalScore = 0.45*Relevance + 0.35*Credibility + 0.20*Freshness  (all on 0-100)

Relevance uses embedding cosine similarity between the topic and the article
(a free, deterministic stand-in for an LLM relevance judge, mapped to 0-100).
"""
from datetime import datetime, timezone

import numpy as np

from config import get_settings
from similarity.embedder import embed

DOMAIN_SCORES: dict[str, float] = {
    ".gov": 100, ".mil": 100,
    "nature.com": 98, "science.org": 97, "ieee.org": 96,
    "reuters.com": 95, "apnews.com": 94, "bbc.com": 92, "bbc.co.uk": 92,
    "arxiv.org": 90, "acm.org": 90, "nih.gov": 100, ".edu": 88,
    "nytimes.com": 85, "theguardian.com": 84, "economist.com": 86,
    "wikipedia.org": 75, "stackoverflow.com": 72, "github.com": 70,
    "medium.com": 60, "substack.com": 55, "dev.to": 55,
    "blogspot.com": 40, "wordpress.com": 40, "tumblr.com": 35,
}
UNKNOWN_SCORE = 20.0


def domain_credibility(domain: str) -> float:
    domain = domain.lower().removeprefix("www.")
    for key, score in DOMAIN_SCORES.items():
        if key.startswith("."):
            if domain.endswith(key):
                return float(score)
        elif domain == key or domain.endswith("." + key):
            return float(score)
    if "blog" in domain:
        return 40.0
    return UNKNOWN_SCORE


def freshness_score(published_date: str) -> float:
    """Today=100, ≤7d=90, ≤30d=70, ≤365d=50, older=20, unknown=50."""
    if not published_date:
        return 50.0
    try:
        pub = datetime.fromisoformat(published_date[:10]).replace(tzinfo=timezone.utc)
    except ValueError:
        return 50.0
    days = (datetime.now(timezone.utc) - pub).days
    if days <= 0:
        return 100.0
    if days <= 7:
        return 90.0
    if days <= 30:
        return 70.0
    if days <= 365:
        return 50.0
    return 20.0


def relevance_score(topic: str, article_text: str, title: str = "") -> float:
    """Cosine similarity between topic and article, mapped to 0-100."""
    if not topic.strip():
        return 50.0
    topic_vec = embed(topic)
    art_vec = embed((title + "\n" + article_text[:2000]).strip())
    cos = float(np.clip(topic_vec @ art_vec, -1.0, 1.0))
    return round(max(0.0, cos) * 100.0, 2)


def final_score(relevance: float, credibility: float, freshness: float) -> float:
    cfg = get_settings()
    score = cfg.w_relevance * relevance + cfg.w_credibility * credibility + cfg.w_freshness * freshness
    return round(min(100.0, max(0.0, score)), 2)

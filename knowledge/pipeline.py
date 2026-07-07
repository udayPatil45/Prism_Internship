"""The end-to-end PRISM research pipeline.

Search -> URL dedup -> Crawl -> Extract -> Clean -> Embed -> Semantic dedup
-> Credibility scoring -> Knowledge store.
"""
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from config import get_settings
from crawler.extractor import extract
from crawler.fetcher import fetch
from database.db import get_session, init_db
from database.repository import Repository
from scoring.credibility import (domain_credibility, final_score,
                                 freshness_score, relevance_score)
from search.factory import search_with_fallback
from similarity.dedup import is_semantic_duplicate
from similarity.embedder import embed
from utils.hashing import article_hash
from utils.logging import get_logger

log = get_logger(__name__)

STOPWORDS = set("the a an and or of to in on for with is are was were by from at as it this that these those be have has i you we they not".split())
MIN_SCORE_FOR_ACCEPT = 45.0
REVIEW_BAND = (35.0, 45.0)  # scores in this band go to review queue


@dataclass
class RunReport:
    topic: str
    searched: int = 0
    skipped_url_dup: int = 0
    crawl_failed: int = 0
    semantic_dups: int = 0
    accepted: int = 0
    rejected: int = 0
    sent_to_review: int = 0
    details: list[str] = field(default_factory=list)


def _keywords(text: str, k: int = 8) -> list[str]:
    tokens = [t for t in re.findall(r"[a-z]{3,}", text.lower()) if t not in STOPWORDS]
    return [w for w, _ in Counter(tokens).most_common(k)]


def _summary(text: str, max_chars: int = 500) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    out = ""
    for s in sentences:
        if len(out) + len(s) > max_chars:
            break
        out += s + " "
    return out.strip() or text[:max_chars]


def run_research(topic: str, max_results: int | None = None) -> RunReport:
    """Execute the full pipeline for a topic and return a report."""
    init_db()
    cfg = get_settings()
    max_results = max_results or cfg.max_results_per_query
    report = RunReport(topic=topic)

    results = search_with_fallback(topic, max_results=max_results)
    report.searched = len(results)

    with get_session() as session:
        repo = Repository(session)
        repo.log("searched", topic=topic, detail=f"{len(results)} results")

        for res in results:
            url = res.url
            domain = urlsplit(url).netloc.lower().removeprefix("www.")

            # 1. URL dedup
            if repo.is_url_visited(url):
                repo.log("skipped_duplicate", url=url, topic=topic)
                report.skipped_url_dup += 1
                continue
            repo.mark_url(url, domain, topic, "pending")

            # 2. Crawl + extract
            html = fetch(url)
            if not html:
                repo.mark_url(url, domain, topic, "failed")
                repo.log("failed", url=url, topic=topic, detail="fetch failed")
                report.crawl_failed += 1
                continue
            art = extract(url, html)
            if art is None:
                repo.mark_url(url, domain, topic, "failed")
                repo.log("failed", url=url, topic=topic, detail="extraction failed")
                report.crawl_failed += 1
                continue
            repo.mark_url(url, domain, topic, "crawled")

            # 3. Exact content dedup
            content_hash = article_hash(art.text)
            if repo.article_hash_exists(content_hash):
                repo.log("skipped_duplicate", url=url, topic=topic, detail="identical content")
                report.skipped_url_dup += 1
                continue

            # 4. Embedding + semantic dedup
            vec = embed(art.title + "\n" + art.text[:3000])
            ids, corpus = repo.all_embeddings()
            is_dup, sim = is_semantic_duplicate(vec, corpus)

            # 5. Scoring
            rel = relevance_score(topic, art.text, art.title)
            cred = domain_credibility(domain)
            fresh = freshness_score(art.date)
            score = final_score(rel, cred, fresh)

            src = repo.get_or_create_source(domain, cred)
            status, reason = "accepted", ""
            if is_dup:
                status, reason = "rejected", f"semantic duplicate (sim={sim:.3f})"
                repo.log("dedup_semantic", url=url, topic=topic, detail=reason)
                report.semantic_dups += 1
            elif score < REVIEW_BAND[0]:
                status, reason = "rejected", f"low score ({score})"
            elif score < REVIEW_BAND[1]:
                status, reason = "review", f"borderline score ({score})"

            article = repo.add_article(
                url=url, url_hash=repo.mark_url(url, domain, topic, "crawled").url_hash,
                domain=domain, source_id=src.id, topic=topic,
                title=art.title, author=art.author, published_date=art.date,
                text=art.text[:20000], images=json.dumps(art.images),
                article_hash=content_hash, status=status, reject_reason=reason,
                relevance_score=rel, credibility_score=cred,
                freshness_score=fresh, final_score=score, similarity_score=sim,
            )

            if status == "accepted":
                kn = repo.add_knowledge(
                    vec, article_id=article.id, title=art.title, topic=topic,
                    summary=_summary(art.text), keywords=",".join(_keywords(art.text)),
                    source_domain=domain,
                    citation=f"{art.author or domain}. \"{art.title}\". {domain}, {art.date or 'n.d.'}. {url}",
                    similarity_score=sim, credibility_score=score,
                )
                article.embedding_id = kn.id
                repo.log("stored", url=url, topic=topic, detail=f"score={score}")
                report.accepted += 1
            elif status == "review":
                repo.add_review(article.id, reason)
                report.sent_to_review += 1
            else:
                report.rejected += 1
            report.details.append(f"[{status}] {score:>6.2f}  {art.title[:70]}  ({domain})")

    log.info("Run complete: %s", report)
    return report

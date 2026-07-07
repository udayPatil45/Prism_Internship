"""Data-access layer: all queries go through here (keeps SQL out of business logic)."""
import json
from datetime import datetime, timezone

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.models import (Article, CrawlLog, Knowledge, ReviewItem, Source,
                             VisitedURL)
from utils.hashing import url_hash


class Repository:
    def __init__(self, session: Session):
        self.s = session

    # ---------- visited urls ----------
    def is_url_visited(self, url: str) -> bool:
        h = url_hash(url)
        return self.s.scalar(select(VisitedURL.id).where(VisitedURL.url_hash == h)) is not None

    def mark_url(self, url: str, domain: str, topic: str, status: str) -> VisitedURL:
        h = url_hash(url)
        row = self.s.scalar(select(VisitedURL).where(VisitedURL.url_hash == h))
        if row is None:
            row = VisitedURL(url=url, url_hash=h, domain=domain, topic=topic, status=status)
            self.s.add(row)
        else:
            row.status = status
        self.s.flush()
        return row

    # ---------- sources ----------
    def get_or_create_source(self, domain: str, base_credibility: float) -> Source:
        src = self.s.scalar(select(Source).where(Source.domain == domain))
        if src is None:
            src = Source(domain=domain, base_credibility=base_credibility)
            self.s.add(src)
            self.s.flush()
        return src

    # ---------- articles ----------
    def article_hash_exists(self, content_hash: str) -> bool:
        return self.s.scalar(select(Article.id).where(Article.article_hash == content_hash)) is not None

    def add_article(self, **kwargs) -> Article:
        art = Article(**kwargs)
        self.s.add(art)
        self.s.flush()
        if art.source_id:
            src = self.s.get(Source, art.source_id)
            if src:
                src.articles_count += 1
        return art

    # ---------- knowledge ----------
    def add_knowledge(self, embedding: np.ndarray, **kwargs) -> Knowledge:
        kn = Knowledge(embedding=json.dumps(embedding.tolist()), **kwargs)
        self.s.add(kn)
        self.s.flush()
        return kn

    def all_embeddings(self) -> tuple[list[int], np.ndarray]:
        rows = self.s.execute(select(Knowledge.id, Knowledge.embedding)).all()
        ids, vecs = [], []
        for kid, emb in rows:
            if emb:
                ids.append(kid)
                vecs.append(json.loads(emb))
        if not vecs:
            return [], np.zeros((0, 384), dtype=np.float32)
        return ids, np.asarray(vecs, dtype=np.float32)

    # ---------- logs / review ----------
    def log(self, event: str, url: str = "", topic: str = "", detail: str = "") -> None:
        self.s.add(CrawlLog(event=event, url=url, topic=topic, detail=detail))

    def add_review(self, article_id: int, reason: str) -> None:
        self.s.add(ReviewItem(article_id=article_id, reason=reason))

    # ---------- dashboard stats ----------
    def stats(self) -> dict:
        today = datetime.now(timezone.utc).date()
        total_urls = self.s.scalar(select(func.count(VisitedURL.id))) or 0
        todays = self.s.scalar(
            select(func.count(VisitedURL.id)).where(func.date(VisitedURL.created_at) == today.isoformat())
        ) or 0
        dup_urls = self.s.scalar(
            select(func.count(CrawlLog.id)).where(CrawlLog.event == "skipped_duplicate")
        ) or 0
        dup_insights = self.s.scalar(
            select(func.count(CrawlLog.id)).where(CrawlLog.event == "dedup_semantic")
        ) or 0
        knowledge_count = self.s.scalar(select(func.count(Knowledge.id))) or 0
        avg_cred = self.s.scalar(select(func.avg(Article.final_score)).where(Article.status == "accepted")) or 0.0
        accepted = self.s.scalar(select(func.count(Article.id)).where(Article.status == "accepted")) or 0
        rejected = self.s.scalar(select(func.count(Article.id)).where(Article.status == "rejected")) or 0
        return {
            "total_urls": total_urls,
            "todays_crawls": todays,
            "duplicate_urls": dup_urls,
            "duplicate_insights": dup_insights,
            "knowledge_entries": knowledge_count,
            "avg_credibility": round(float(avg_cred), 2),
            "accepted": accepted,
            "rejected": rejected,
        }

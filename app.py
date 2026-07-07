"""FastAPI service exposing the PRISM pipeline and knowledge base.

Run:  uvicorn app:app --reload
"""
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from database.db import get_session, init_db
from database.models import Article, Knowledge, ReviewItem
from database.repository import Repository
from knowledge.pipeline import run_research

app = FastAPI(title="PRISM", description="Progressive Research Integration and Synthesis Model", version="1.0.0")


@app.on_event("startup")
def startup() -> None:
    init_db()


class ResearchRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=300)
    max_results: int = Field(default=10, ge=1, le=25)


@app.post("/research")
def research(req: ResearchRequest):
    """Run the full pipeline synchronously and return a report."""
    report = run_research(req.topic, max_results=req.max_results)
    return report


@app.post("/research/async")
def research_async(req: ResearchRequest, background: BackgroundTasks):
    background.add_task(run_research, req.topic, req.max_results)
    return {"status": "started", "topic": req.topic}


@app.get("/stats")
def stats():
    with get_session() as session:
        return Repository(session).stats()


@app.get("/articles")
def articles(topic: str | None = None, status: str | None = None,
             limit: int = Query(default=50, le=200)):
    with get_session() as session:
        stmt = select(Article).order_by(Article.created_at.desc()).limit(limit)
        if topic:
            stmt = stmt.where(Article.topic == topic)
        if status:
            stmt = stmt.where(Article.status == status)
        rows = session.scalars(stmt).all()
        return [{
            "id": a.id, "title": a.title, "url": a.url, "domain": a.domain,
            "topic": a.topic, "status": a.status, "final_score": a.final_score,
            "published_date": a.published_date, "created_at": a.created_at.isoformat(),
        } for a in rows]


@app.get("/knowledge")
def knowledge(topic: str | None = None, limit: int = Query(default=50, le=200)):
    with get_session() as session:
        stmt = select(Knowledge).order_by(Knowledge.created_at.desc()).limit(limit)
        if topic:
            stmt = stmt.where(Knowledge.topic == topic)
        rows = session.scalars(stmt).all()
        return [{
            "id": k.id, "title": k.title, "topic": k.topic, "summary": k.summary,
            "keywords": k.keywords, "source": k.source_domain, "citation": k.citation,
            "credibility": k.credibility_score, "created_at": k.created_at.isoformat(),
        } for k in rows]


@app.post("/review/{item_id}/{decision}")
def resolve_review(item_id: int, decision: str):
    if decision not in ("approved", "rejected"):
        raise HTTPException(400, "decision must be 'approved' or 'rejected'")
    with get_session() as session:
        item = session.get(ReviewItem, item_id)
        if item is None:
            raise HTTPException(404, "review item not found")
        item.resolved = True
        item.decision = decision
        article = session.get(Article, item.article_id)
        if article:
            article.status = "accepted" if decision == "approved" else "rejected"
        return {"id": item_id, "decision": decision}

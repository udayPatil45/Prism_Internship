import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base
from database.repository import Repository


@pytest.fixture()
def repo():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield Repository(session)
    session.close()


def test_url_dedup(repo):
    assert repo.is_url_visited("https://a.com/x") is False
    repo.mark_url("https://a.com/x", "a.com", "t", "crawled")
    assert repo.is_url_visited("https://a.com/x") is True
    assert repo.is_url_visited("https://www.a.com/x/") is True  # normalized


def test_knowledge_and_embeddings(repo):
    vec = np.ones(384, dtype=np.float32) / np.sqrt(384)
    src = repo.get_or_create_source("a.com", 50)
    art = repo.add_article(url="https://a.com/x", url_hash="h", domain="a.com",
                           source_id=src.id, topic="t", title="T",
                           article_hash="ch", final_score=80.0)
    repo.add_knowledge(vec, article_id=art.id, title="T", topic="t",
                       summary="s", keywords="k", source_domain="a.com",
                       citation="c", credibility_score=80.0)
    ids, corpus = repo.all_embeddings()
    assert len(ids) == 1 and corpus.shape == (1, 384)


def test_stats(repo):
    stats = repo.stats()
    assert stats["total_urls"] == 0 and stats["accepted"] == 0

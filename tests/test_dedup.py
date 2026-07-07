import numpy as np

from similarity.dedup import is_semantic_duplicate, max_similarity
from similarity.embedder import embed


def test_empty_corpus():
    v = np.ones(384, dtype=np.float32)
    dup, sim = is_semantic_duplicate(v / np.linalg.norm(v), np.zeros((0, 384), dtype=np.float32))
    assert dup is False


def test_identical_vectors_are_duplicates():
    v = embed("machine learning improves protein folding prediction")
    corpus = v.reshape(1, -1)
    dup, sim = is_semantic_duplicate(v, corpus)
    assert dup is True
    assert sim > 0.99


def test_max_similarity_picks_best():
    a = embed("stock market crash analysis")
    b = embed("recipe for chocolate cake")
    corpus = np.stack([b, a])
    score, idx = max_similarity(a, corpus)
    assert idx == 1

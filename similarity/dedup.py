"""Semantic duplicate detection via cosine similarity.
Uses FAISS when installed, pure NumPy otherwise (identical results for
normalized vectors, since inner product == cosine similarity)."""
import numpy as np

from config import get_settings
from utils.logging import get_logger

log = get_logger(__name__)

try:
    import faiss  # type: ignore
    _HAS_FAISS = True
except ImportError:
    _HAS_FAISS = False


def max_similarity(query: np.ndarray, corpus: np.ndarray) -> tuple[float, int]:
    """Return (best cosine similarity, index in corpus). (-1.0, -1) if corpus empty."""
    if corpus.shape[0] == 0:
        return -1.0, -1
    q = query.astype(np.float32).reshape(1, -1)
    if _HAS_FAISS:
        index = faiss.IndexFlatIP(corpus.shape[1])
        index.add(corpus)
        scores, ids = index.search(q, 1)
        return float(scores[0][0]), int(ids[0][0])
    sims = corpus @ q.T
    best = int(np.argmax(sims))
    return float(sims[best][0]), best


def is_semantic_duplicate(query: np.ndarray, corpus: np.ndarray) -> tuple[bool, float]:
    score, _ = max_similarity(query, corpus)
    return score > get_settings().similarity_threshold, max(score, 0.0)

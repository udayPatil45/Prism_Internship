"""Sentence embeddings. Uses all-MiniLM-L6-v2 when available; falls back to a
deterministic TF-IDF-hash embedding so the pipeline never breaks offline."""
import hashlib
import re

import numpy as np

from config import get_settings
from utils.logging import get_logger

log = get_logger(__name__)
DIM = 384
_model = None
_model_failed = False


def _load_model():
    global _model, _model_failed
    if _model is not None or _model_failed:
        return _model
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(get_settings().embedding_model)
        log.info("Loaded embedding model %s", get_settings().embedding_model)
    except Exception as exc:
        log.warning("SentenceTransformer unavailable (%s). Using hash fallback.", exc)
        _model_failed = True
    return _model


def _hash_embed(text: str) -> np.ndarray:
    """Deterministic bag-of-words hashed embedding (fallback only)."""
    vec = np.zeros(DIM, dtype=np.float32)
    for token in re.findall(r"[a-z0-9]{2,}", text.lower()):
        idx = int(hashlib.md5(token.encode()).hexdigest(), 16) % DIM
        vec[idx] += 1.0
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def embed(text: str) -> np.ndarray:
    """Return a unit-normalized 384-d embedding for the text."""
    model = _load_model()
    if model is not None:
        vec = model.encode(text[:5000], normalize_embeddings=True)
        return np.asarray(vec, dtype=np.float32)
    return _hash_embed(text[:5000])

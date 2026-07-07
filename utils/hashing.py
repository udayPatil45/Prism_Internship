"""Hash helpers used for URL and content deduplication."""
import hashlib
from urllib.parse import urlsplit, urlunsplit


def normalize_url(url: str) -> str:
    """Normalize a URL so trivially different forms hash identically."""
    parts = urlsplit(url.strip())
    scheme = (parts.scheme or "https").lower()
    netloc = parts.netloc.lower().removeprefix("www.")
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((scheme, netloc, path, parts.query, ""))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def url_hash(url: str) -> str:
    return sha256_text(normalize_url(url))


def article_hash(text: str) -> str:
    """Hash of normalized article body for exact-content dedup."""
    normalized = " ".join(text.lower().split())
    return sha256_text(normalized)

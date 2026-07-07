"""Content extraction: Trafilatura first (best quality), BeautifulSoup fallback."""
import json
import re
from dataclasses import dataclass, field

import trafilatura
from bs4 import BeautifulSoup

from utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class ExtractedArticle:
    url: str
    title: str = ""
    author: str = ""
    date: str = ""
    text: str = ""
    images: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


def _clean_text(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def extract(url: str, html: str) -> ExtractedArticle | None:
    art = ExtractedArticle(url=url)

    extracted = trafilatura.extract(
        html, url=url, output_format="json",
        include_images=True, with_metadata=True,
    )
    if extracted:
        data = json.loads(extracted)
        art.title = data.get("title") or ""
        art.author = data.get("author") or ""
        art.date = data.get("date") or ""
        art.text = _clean_text(data.get("text") or "")
        art.metadata = {k: data.get(k) for k in ("hostname", "sitename", "categories", "tags") if data.get(k)}

    soup = BeautifulSoup(html, "lxml")
    if not art.title and soup.title:
        art.title = soup.title.get_text(strip=True)
    if not art.text:
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        body = soup.find("article") or soup.find("main") or soup.body
        if body:
            art.text = _clean_text(body.get_text(separator="\n", strip=True))
    if not art.author:
        meta = soup.find("meta", attrs={"name": "author"})
        if meta and meta.get("content"):
            art.author = meta["content"]
    if not art.date:
        meta = soup.find("meta", attrs={"property": "article:published_time"})
        if meta and meta.get("content"):
            art.date = meta["content"][:10]
    art.images = [img["src"] for img in soup.find_all("img", src=True)][:10]

    if len(art.text) < 200:
        log.info("Extraction too short for %s (%d chars)", url, len(art.text))
        return None
    return art

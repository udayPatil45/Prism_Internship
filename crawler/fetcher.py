"""HTML fetching. Uses requests for static pages, Playwright (if installed)
for JavaScript-heavy pages. Falls back gracefully when Playwright is absent."""
import requests

from config import get_settings
from utils.logging import get_logger

log = get_logger(__name__)

# Domains known to require JS rendering
DYNAMIC_HINTS = ("twitter.com", "x.com", "medium.com", "linkedin.com", "bloomberg.com")


def _looks_dynamic(url: str, html: str | None) -> bool:
    if any(h in url for h in DYNAMIC_HINTS):
        return True
    if html is not None and len(html) < 2000 and ("<noscript" in html.lower() or "enable javascript" in html.lower()):
        return True
    return False


def fetch_static(url: str) -> str | None:
    cfg = get_settings()
    try:
        resp = requests.get(url, timeout=cfg.request_timeout,
                            headers={"User-Agent": cfg.user_agent})
        resp.raise_for_status()
        ctype = resp.headers.get("content-type", "")
        if "html" not in ctype and "xml" not in ctype and ctype:
            return None
        return resp.text
    except Exception as exc:
        log.warning("requests fetch failed for %s: %s", url, exc)
        return None


def fetch_dynamic(url: str) -> str | None:
    """Render with Playwright if available; otherwise return None."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.info("Playwright not installed; skipping dynamic render for %s", url)
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=get_settings().user_agent)
            page.goto(url, timeout=get_settings().request_timeout * 1000, wait_until="domcontentloaded")
            html = page.content()
            browser.close()
            return html
    except Exception as exc:
        log.warning("Playwright fetch failed for %s: %s", url, exc)
        return None


def fetch(url: str) -> str | None:
    """Auto-select strategy: static first, dynamic when needed."""
    if _looks_dynamic(url, None):
        return fetch_dynamic(url) or fetch_static(url)
    html = fetch_static(url)
    if html and _looks_dynamic(url, html):
        return fetch_dynamic(url) or html
    return html

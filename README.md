# PRISM — Progressive Research Integration and Synthesis Model

An autonomous research assistant that searches the web, crawls pages, extracts
clean article content, removes duplicate URLs and semantically-duplicate
insights, scores source credibility, stores structured knowledge in SQLite,
and displays everything on a Streamlit dashboard. A FastAPI service exposes
the same pipeline over HTTP.

**100% free** — the default search provider is DuckDuckGo (no API key, no signup).
Tavily (free tier, no card required) and SearxNG (open-source, no key) are
drop-in alternatives via the `SEARCH_PROVIDER` setting.

## Architecture

```
Search (DuckDuckGo / Tavily / SearxNG — Strategy pattern, all free)
   ↓
Candidate URLs
   ↓
URL Deduplication (SHA-256 of normalized URL, checked in SQLite)
   ↓
Crawler (requests for static pages, Playwright auto-fallback for dynamic)
   ↓
Article Extraction (Trafilatura → BeautifulSoup fallback)
   ↓
Content Cleaning + Metadata (title, author, date, images)
   ↓
Embedding (all-MiniLM-L6-v2, 384-d, offline hash fallback)
   ↓
Semantic Dedup (cosine similarity, threshold 0.85, FAISS optional)
   ↓
Credibility Scoring (0.45·Relevance + 0.35·Domain + 0.20·Freshness)
   ↓
Knowledge Database (SQLite via SQLAlchemy)
   ↓
Dashboard (Streamlit) + API (FastAPI)
```

## Installation

```bash
git clone <repo> && cd PRISM
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # optional — works with defaults
```

Optional extras:
```bash
pip install faiss-cpu                 # faster similarity search
pip install playwright && playwright install chromium   # JS-heavy sites
```

## Running

```bash
# CLI — run a research job
python main.py "quantum error correction" --max 8

# Dashboard
streamlit run dashboard/streamlit_app.py

# API
uvicorn app:app --reload
# then: POST http://127.0.0.1:8000/research  {"topic": "solid state batteries"}
# docs: http://127.0.0.1:8000/docs
```

## Folder structure

```
PRISM/
├── app.py                 # FastAPI service
├── main.py                # CLI entry point
├── config.py              # Pydantic settings (.env)
├── requirements.txt
├── .env.example
├── search/                # SearchProvider interface + 3 free providers + fallback chain
├── crawler/               # fetcher (requests/Playwright), extractor (Trafilatura/BS4)
├── database/              # SQLAlchemy models, session, repository (DAL)
├── similarity/            # embeddings + semantic dedup (FAISS/NumPy)
├── scoring/               # domain credibility, freshness, relevance, final score
├── knowledge/             # end-to-end pipeline
├── dashboard/             # Streamlit app (Home, Analytics, Articles, KB, Review, Run)
├── utils/                 # hashing, logging
├── tests/                 # pytest unit tests
└── data/                  # SQLite database (created at runtime)
```

## Scoring model

`Final = 0.45·Relevance + 0.35·Credibility + 0.20·Freshness` (each 0–100)

- **Relevance** — cosine similarity between the topic and article embeddings, mapped to 0–100 (free, deterministic replacement for an LLM judge; swap in an LLM by editing `scoring/credibility.py:relevance_score`).
- **Credibility** — domain table: .gov 100, nature 98, IEEE 96, Reuters 95, arXiv 90, Wikipedia 75, Medium 60, blogs 40, unknown 20.
- **Freshness** — today 100, ≤7 d 90, ≤30 d 70, ≤1 y 50, older 20, unknown 50.
- Score < 35 → rejected · 35–45 → review queue · ≥ 45 → accepted into knowledge base.

## Screenshots

![Home](docs/screenshot-home.png) <!-- placeholder -->
![Analytics](docs/screenshot-analytics.png) <!-- placeholder -->

## Testing

```bash
pytest tests/ -v
```

## Future work

- Scheduled/recurring research jobs (APScheduler)
- LLM-based relevance judging and abstractive summaries
- Full-text search (SQLite FTS5) over the knowledge base
- Per-domain rate limiting and robots.txt caching
- Export knowledge base to Markdown/CSV/Notion

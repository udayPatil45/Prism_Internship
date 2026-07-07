"""PRISM Streamlit dashboard.

Run:  streamlit run dashboard/streamlit_app.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # project root importable

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import func, select

from database.db import get_session, init_db
from database.models import Article, CrawlLog, Knowledge, ReviewItem, VisitedURL
from database.repository import Repository
from knowledge.pipeline import run_research

st.set_page_config(page_title="PRISM Dashboard", page_icon="🔎", layout="wide")
init_db()

PAGES = ["Home", "Analytics", "Articles", "Knowledge Base", "Review Queue", "Run Research"]
page = st.sidebar.radio("Navigate", PAGES)


def load_df(stmt) -> pd.DataFrame:
    with get_session() as session:
        rows = session.execute(stmt).all()
        return pd.DataFrame([dict(r._mapping) for r in rows])


if page == "Home":
    st.title("🔎 PRISM — Research Dashboard")
    with get_session() as session:
        stats = Repository(session).stats()
    c = st.columns(4)
    c[0].metric("Total URLs Crawled", stats["total_urls"])
    c[1].metric("Today's Crawls", stats["todays_crawls"])
    c[2].metric("Duplicate URLs", stats["duplicate_urls"])
    c[3].metric("Duplicate Insights", stats["duplicate_insights"])
    c = st.columns(4)
    c[0].metric("Knowledge Entries", stats["knowledge_entries"])
    c[1].metric("Average Credibility", stats["avg_credibility"])
    c[2].metric("Accepted Articles", stats["accepted"])
    c[3].metric("Rejected Articles", stats["rejected"])

    st.subheader("Latest Articles")
    df = load_df(select(Article.id, Article.title, Article.domain, Article.topic,
                        Article.status, Article.final_score, Article.created_at)
                 .order_by(Article.created_at.desc()).limit(15))
    st.dataframe(df, use_container_width=True) if not df.empty else st.info("No articles yet — run a research job.")

elif page == "Analytics":
    st.title("📊 Analytics")
    with get_session() as session:
        stats = Repository(session).stats()
    col1, col2 = st.columns(2)

    pie_df = pd.DataFrame({"Status": ["Accepted", "Rejected"],
                           "Count": [stats["accepted"], stats["rejected"]]})
    if pie_df["Count"].sum() > 0:
        col1.plotly_chart(px.pie(pie_df, names="Status", values="Count",
                                 title="Accepted vs Rejected"), use_container_width=True)

    src_df = load_df(select(Article.domain, func.count(Article.id).label("count"))
                     .group_by(Article.domain).order_by(func.count(Article.id).desc()).limit(10))
    if not src_df.empty:
        col2.plotly_chart(px.bar(src_df, x="domain", y="count", title="Top Sources"),
                          use_container_width=True)

    daily = load_df(select(func.date(VisitedURL.created_at).label("day"),
                           func.count(VisitedURL.id).label("crawls"))
                    .group_by(func.date(VisitedURL.created_at)).order_by("day"))
    if not daily.empty:
        st.plotly_chart(px.line(daily, x="day", y="crawls", markers=True,
                                title="Daily Crawls"), use_container_width=True)

    logs = load_df(select(CrawlLog.event, CrawlLog.url, CrawlLog.detail, CrawlLog.created_at)
                   .order_by(CrawlLog.created_at.desc()).limit(50))
    st.subheader("Recent Pipeline Events")
    st.dataframe(logs, use_container_width=True) if not logs.empty else st.info("No events yet.")

elif page == "Articles":
    st.title("📰 Articles")
    with get_session() as session:
        topics = [t for (t,) in session.execute(select(Article.topic).distinct()).all()]
        domains = [d for (d,) in session.execute(select(Article.domain).distinct()).all()]
    c1, c2, c3 = st.columns(3)
    f_topic = c1.selectbox("Topic", ["All"] + topics)
    f_domain = c2.selectbox("Source", ["All"] + domains)
    f_status = c3.selectbox("Status", ["All", "accepted", "rejected", "review"])
    query = st.text_input("Search in titles")

    stmt = select(Article.id, Article.title, Article.url, Article.domain, Article.topic,
                  Article.status, Article.final_score, Article.published_date, Article.created_at)
    if f_topic != "All":
        stmt = stmt.where(Article.topic == f_topic)
    if f_domain != "All":
        stmt = stmt.where(Article.domain == f_domain)
    if f_status != "All":
        stmt = stmt.where(Article.status == f_status)
    if query:
        stmt = stmt.where(Article.title.ilike(f"%{query}%"))
    df = load_df(stmt.order_by(Article.created_at.desc()).limit(200))
    st.dataframe(df, use_container_width=True) if not df.empty else st.info("No matching articles.")

elif page == "Knowledge Base":
    st.title("🧠 Knowledge Base")
    with get_session() as session:
        topics = [t for (t,) in session.execute(select(Knowledge.topic).distinct()).all()]
    f_topic = st.selectbox("Topic", ["All"] + topics)
    query = st.text_input("Search")
    stmt = select(Knowledge.id, Knowledge.title, Knowledge.topic, Knowledge.summary,
                  Knowledge.keywords, Knowledge.source_domain, Knowledge.citation,
                  Knowledge.credibility_score, Knowledge.created_at)
    if f_topic != "All":
        stmt = stmt.where(Knowledge.topic == f_topic)
    if query:
        stmt = stmt.where(Knowledge.summary.ilike(f"%{query}%") | Knowledge.title.ilike(f"%{query}%"))
    df = load_df(stmt.order_by(Knowledge.created_at.desc()).limit(200))
    if df.empty:
        st.info("Knowledge base is empty.")
    else:
        for _, row in df.iterrows():
            with st.expander(f"{row['title']}  ·  {row['source_domain']}  ·  score {row['credibility_score']}"):
                st.write(row["summary"])
                st.caption(f"Keywords: {row['keywords']}")
                st.caption(f"Citation: {row['citation']}")

elif page == "Review Queue":
    st.title("✅ Review Queue")
    with get_session() as session:
        items = session.execute(
            select(ReviewItem, Article).join(Article, ReviewItem.article_id == Article.id)
            .where(ReviewItem.resolved.is_(False))
        ).all()
    if not items:
        st.success("Review queue is empty 🎉")
    for item, art in items:
        with st.expander(f"#{item.id} · {art.title[:80]} · {art.domain} · score {art.final_score}"):
            st.write(art.text[:800] + "…")
            new_title = st.text_input("Edit title", value=art.title, key=f"t{item.id}")
            c1, c2, c3 = st.columns(3)
            if c1.button("Approve", key=f"a{item.id}"):
                with get_session() as session:
                    it = session.get(ReviewItem, item.id)
                    a = session.get(Article, art.id)
                    it.resolved, it.decision, a.status, a.title = True, "approved", "accepted", new_title
                st.rerun()
            if c2.button("Reject", key=f"r{item.id}"):
                with get_session() as session:
                    it = session.get(ReviewItem, item.id)
                    a = session.get(Article, art.id)
                    it.resolved, it.decision, a.status = True, "rejected", "rejected"
                st.rerun()
            if c3.button("Save Edit", key=f"e{item.id}"):
                with get_session() as session:
                    a = session.get(Article, art.id)
                    a.title = new_title
                st.toast("Saved")

elif page == "Run Research":
    st.title("🚀 Run Research")
    topic = st.text_input("Research topic", placeholder="e.g. quantum error correction 2026")
    max_r = st.slider("Max search results", 3, 20, 8)
    if st.button("Start", type="primary") and topic.strip():
        with st.spinner("Running pipeline… (search → crawl → dedup → score → store)"):
            report = run_research(topic.strip(), max_results=max_r)
        st.success(f"Done. Accepted {report.accepted}, rejected {report.rejected}, "
                   f"duplicates {report.skipped_url_dup + report.semantic_dups}, "
                   f"review {report.sent_to_review}.")
        st.code("\n".join(report.details) or "No details.")

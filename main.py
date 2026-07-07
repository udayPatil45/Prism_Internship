"""CLI entry point.

Usage:
    python main.py "quantum computing breakthroughs" --max 8
"""
import argparse

from database.db import init_db
from knowledge.pipeline import run_research


def main() -> None:
    parser = argparse.ArgumentParser(description="PRISM autonomous research assistant")
    parser.add_argument("topic", help="Research topic / query")
    parser.add_argument("--max", type=int, default=None, help="Max search results")
    args = parser.parse_args()

    init_db()
    report = run_research(args.topic, max_results=args.max)

    print("\n===== PRISM RUN REPORT =====")
    print(f"Topic:              {report.topic}")
    print(f"Search results:     {report.searched}")
    print(f"Duplicate URLs:     {report.skipped_url_dup}")
    print(f"Crawl failures:     {report.crawl_failed}")
    print(f"Semantic dups:      {report.semantic_dups}")
    print(f"Accepted:           {report.accepted}")
    print(f"Rejected:           {report.rejected}")
    print(f"Sent to review:     {report.sent_to_review}")
    for line in report.details:
        print("  " + line)


if __name__ == "__main__":
    main()

"""
Update GitHub Repository Description & Topics via GitHub REST API.

Usage:
    python scripts/update_repo_about.py --token YOUR_GHP_TOKEN
"""
from __future__ import annotations

import argparse
import sys
import httpx


def update_repo(token: str) -> None:
    token = token.strip()
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }

    url = "https://api.github.com/repos/RitikaJain8818/job-outreach-agent"

    description = (
        "AI-powered multi-agent automated job outreach system built with FastAPI, "
        "Async SQLAlchemy, Gemini 3.6 Flash, and Gmail API."
    )
    topics = [
        "ai-agent",
        "multi-agent-system",
        "job-outreach",
        "fastapi",
        "gemini-api",
        "gmail-api",
        "python",
        "sqlalchemy",
    ]

    print("📝 Updating repository description & topics...")
    r = httpx.patch(url, headers=headers, json={"description": description, "homepage": "https://github.com/RitikaJain8818/job-outreach-agent"})

    if r.status_code == 200:
        print("✅ Description updated successfully!")
    else:
        print(f"❌ Failed to update description: {r.status_code} — {r.text}")
        sys.exit(1)

    # Set topics
    topics_url = f"{url}/topics"
    r_topics = httpx.put(topics_url, headers=headers, json={"names": topics})
    if r_topics.status_code == 200:
        print("✅ Topics updated successfully!")
    else:
        print(f"⚠️ Topics update returned {r_topics.status_code}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Update GitHub Repository Description and Topics")
    parser.add_argument("--token", required=True, help="GitHub Classic PAT token (ghp_...)")
    args = parser.parse_args()
    update_repo(args.token)


if __name__ == "__main__":
    main()

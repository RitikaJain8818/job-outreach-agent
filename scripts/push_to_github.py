"""
Push repository to GitHub using a Personal Access Token.

Usage:
    python scripts/push_to_github.py --token YOUR_GITHUB_PAT
"""
from __future__ import annotations

import argparse
import subprocess
import sys


def push(token: str) -> None:
    token = token.strip()
    if not token:
        print("❌ Token cannot be empty")
        sys.exit(1)

    remote_url = f"https://{token}@github.com/RitikaJain8818/job-outreach-agent.git"

    print("🚀 Pushing repository to GitHub...")
    cmd = ["git", "push", "-u", remote_url, "main"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print("\n✅ Successfully pushed to GitHub!")
        print("   URL: https://github.com/RitikaJain8818/job-outreach-agent")
    else:
        print(f"\n❌ Push failed: {result.stderr}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Push local git repository to GitHub")
    parser.add_argument("--token", required=True, help="GitHub Personal Access Token (Classic with repo scope)")
    args = parser.parse_args()
    push(args.token)


if __name__ == "__main__":
    main()

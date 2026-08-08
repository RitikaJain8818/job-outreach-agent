"""
Quick smoke test — sends a real test email via Gmail API.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.integrations.gmail.auth import get_gmail_credentials
from app.integrations.gmail.client import GmailClient

configure_logging("INFO")
logger = get_logger(__name__)


async def send_test_email(to: str) -> None:
    print(f"\n🔐 Loading Gmail credentials...")
    creds = get_gmail_credentials(
        credentials_file=settings.gmail_credentials_file,
        token_file=settings.gmail_token_file,
    )
    client = GmailClient.from_credentials(creds)

    subject = "✅ Job Outreach Agent — Test Email"
    body = (
        "This is a test email sent by the Job Outreach Agent.\n\n"
        "If you received this, the Gmail integration is working correctly.\n\n"
        "— Job Outreach Agent"
    )

    print(f"📤 Sending test email to: {to}")
    thread_id = await client.send(to=to, subject=subject, body=body)

    print(f"\n✅ Email sent successfully!")
    print(f"   Gmail Thread ID : {thread_id}")
    print(f"   Check your inbox at: https://mail.google.com")


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a test email via Gmail API")
    parser.add_argument("--to", required=True, help="Recipient email address")
    args = parser.parse_args()

    try:
        asyncio.run(send_test_email(args.to))
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

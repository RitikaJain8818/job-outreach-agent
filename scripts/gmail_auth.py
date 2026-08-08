"""
Gmail OAuth2 Setup Script
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.integrations.gmail.auth import get_gmail_credentials

configure_logging("INFO")
logger = get_logger(__name__)


def main() -> None:
    creds_file = settings.gmail_credentials_file
    token_file = settings.gmail_token_file

    if not Path(creds_file).exists():
        print(f"\n❌ credentials.json not found at: {creds_file}")
        print("\nTo fix this:")
        print("  1. Go to https://console.cloud.google.com/")
        print("  2. APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID")
        print("  3. Application type: Desktop app")
        print("  4. Download and save as 'credentials.json' in the project root")
        sys.exit(1)

    print(f"\n🔐 Starting Gmail OAuth2 flow...")
    print(f"   Credentials file : {creds_file}")
    print(f"   Token file       : {token_file}")
    print("\n   Your browser will open for Google consent.\n")

    try:
        creds = get_gmail_credentials(
            credentials_file=creds_file,
            token_file=token_file,
        )
        print(f"\n✅ Gmail authorization successful!")
        print(f"   Token saved to: {token_file}")
        print(f"\n   You can now run the application:")
        print(f"   uvicorn app.main:app --reload")
    except Exception as e:
        print(f"\n❌ Authorization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

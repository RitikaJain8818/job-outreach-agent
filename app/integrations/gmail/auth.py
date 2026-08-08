from __future__ import annotations

from app.core.exceptions import GmailAuthError, GmailError, GmailRateLimitError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Gmail API scopes — must match what was granted during OAuth consent
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]


def get_gmail_credentials(credentials_file: str, token_file: str) -> object:
    """
    Load OAuth2 credentials. If token.json exists, use it.
    If expired, refresh. If missing, run the browser OAuth flow.

    Returns a google.oauth2.credentials.Credentials object.
    Raises GmailAuthError on any auth failure.
    """
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as e:
        raise GmailAuthError(
            "Google auth libraries not installed. Run: pip install google-auth-oauthlib"
        ) from e

    import os

    creds = None

    if os.path.exists(token_file):
        try:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        except Exception as e:
            logger.warning("gmail.token_load_failed", token_file=token_file, error=str(e))

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_token(creds, token_file)
        except Exception as e:
            raise GmailAuthError(f"Failed to refresh Gmail token: {e}") from e

    if not creds or not creds.valid:
        if not os.path.exists(credentials_file):
            raise GmailAuthError(
                f"Gmail credentials file not found: {credentials_file}. "
                "Download it from Google Cloud Console."
            )
        try:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
            _save_token(creds, token_file)
        except Exception as e:
            raise GmailAuthError(f"Gmail OAuth flow failed: {e}") from e

    logger.info("gmail.auth_ok")
    return creds


def _save_token(creds: object, token_file: str) -> None:
    try:
        with open(token_file, "w") as f:
            f.write(creds.to_json())  # type: ignore[attr-defined]
    except OSError as e:
        logger.warning("gmail.token_save_failed", error=str(e))

from __future__ import annotations

import asyncio
import base64
import email as email_lib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import partial

from app.core.exceptions import GmailError, GmailRateLimitError
from app.core.logging import get_logger

logger = get_logger(__name__)


class GmailClient:
    """
    Async-friendly wrapper around the Gmail REST API.

    The google-api-python-client is sync, so we run its calls in a thread pool
    via asyncio.to_thread() to avoid blocking the event loop.
    """

    def __init__(self, service: object) -> None:
        """
        :param service: Authenticated Gmail API service object
                        (from googleapiclient.discovery.build)
        """
        self._service = service  # type: ignore[assignment]

    @classmethod
    def from_credentials(cls, credentials: object) -> "GmailClient":
        """Build a GmailClient from authenticated credentials."""
        try:
            from googleapiclient.discovery import build
        except ImportError as e:
            raise GmailError(
                "google-api-python-client not installed. Run: pip install google-api-python-client"
            ) from e
        service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
        return cls(service)

    async def send(self, to: str, subject: str, body: str, html: str | None = None) -> str:
        """
        Send an email. Returns the Gmail thread ID.
        Raises GmailError or GmailRateLimitError on failure.
        """
        message = self._build_message(to=to, subject=subject, body=body, html=html)
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        try:
            result = await asyncio.to_thread(
                self._service.users().messages().send(userId="me", body={"raw": raw}).execute
            )
        except Exception as e:
            self._handle_api_error(e)

        thread_id: str = result.get("threadId", "")
        logger.info("gmail.sent", to=to, thread_id=thread_id, subject=subject[:60])
        return thread_id

    async def get_replies(self, thread_id: str) -> list[dict]:
        """
        Fetch all messages in a thread. Returns list of message dicts with
        keys: gmail_message_id, body_text, direction.
        """
        try:
            thread = await asyncio.to_thread(
                self._service.users().threads().get(userId="me", id=thread_id, format="full").execute
            )
        except Exception as e:
            self._handle_api_error(e)

        messages = thread.get("messages", [])
        result = []
        for msg in messages:
            body_text = self._extract_body(msg)
            result.append({
                "gmail_message_id": msg["id"],
                "body_text": body_text,
                "direction": "inbound",  # Caller determines direction based on sender
            })

        return result

    def _build_message(
        self, to: str, subject: str, body: str, html: str | None = None
    ) -> MIMEMultipart | MIMEText:
        if html:
            message = MIMEMultipart("alternative")
            message["to"] = to
            message["subject"] = subject
            message.attach(MIMEText(body, "plain"))
            message.attach(MIMEText(html, "html"))
            return message

        message = MIMEText(body, "plain")
        message["to"] = to
        message["subject"] = subject
        return message

    def _extract_body(self, message: dict) -> str:
        """Extract plain text body from a Gmail message dict."""
        payload = message.get("payload", {})
        parts = payload.get("parts", [])

        for part in parts:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

        # Fallback: single-part message
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

        return ""

    def _handle_api_error(self, error: Exception) -> None:
        """Classify and re-raise Gmail API errors with typed exceptions."""
        err_str = str(error)
        if "429" in err_str or "rateLimitExceeded" in err_str:
            raise GmailRateLimitError(f"Gmail rate limit exceeded: {error}") from error
        raise GmailError(f"Gmail API error: {error}") from error

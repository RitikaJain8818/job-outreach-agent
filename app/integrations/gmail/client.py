from __future__ import annotations

import asyncio
import base64
import email as email_lib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.exceptions import GmailError, GmailRateLimitError
from app.core.logging import get_logger

logger = get_logger(__name__)


class GmailClient:
    """Async-friendly wrapper around the Gmail REST API."""

    def __init__(self, service: object) -> None:
        self._service = service

    @classmethod
    def from_credentials(cls, credentials: object) -> "GmailClient":
        try:
            from googleapiclient.discovery import build
        except ImportError as e:
            raise GmailError(
                "google-api-python-client not installed. Run: pip install google-api-python-client"
            ) from e
        service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
        return cls(service)

    async def get_thread_header_info(self, thread_id: str) -> tuple[str | None, str | None]:
        """Fetch last Message-ID and cumulative References for a Gmail thread."""
        try:
            thread = await asyncio.to_thread(
                self._service.users().threads().get(userId="me", id=thread_id, format="full").execute
            )
        except Exception as e:
            logger.warning("gmail.get_thread_header_info_failed", thread_id=thread_id, error=str(e))
            return None, None

        messages = thread.get("messages", [])
        if not messages:
            return None, None

        msg_ids = []
        for msg in messages:
            headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
            mid = headers.get("message-id")
            if mid:
                msg_ids.append(mid)

        if not msg_ids:
            return None, None

        last_msg_id = msg_ids[-1]
        references = " ".join(msg_ids)
        return last_msg_id, references

    async def send(
        self,
        to: str,
        subject: str,
        body: str,
        html: str | None = None,
        thread_id: str | None = None,
        in_reply_to: str | None = None,
        references: str | None = None,
    ) -> str:
        if thread_id and not in_reply_to:
            last_msg_id, ref_str = await self.get_thread_header_info(thread_id)
            if last_msg_id:
                in_reply_to = last_msg_id
            if ref_str:
                references = ref_str

        message = self._build_message(
            to=to,
            subject=subject,
            body=body,
            html=html,
            in_reply_to=in_reply_to,
            references=references,
        )
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        payload: dict[str, str] = {"raw": raw}
        if thread_id:
            payload["threadId"] = thread_id

        try:
            result = await asyncio.to_thread(
                self._service.users().messages().send(userId="me", body=payload).execute
            )
        except Exception as e:
            self._handle_api_error(e)

        res_thread_id: str = result.get("threadId", thread_id or "")
        logger.info(
            "gmail.sent",
            to=to,
            thread_id=res_thread_id,
            in_reply_to=in_reply_to,
            subject=subject[:60],
        )
        return res_thread_id

    async def get_replies(self, thread_id: str, sender_email: str | None = None) -> list[dict]:
        try:
            thread = await asyncio.to_thread(
                self._service.users().threads().get(userId="me", id=thread_id, format="full").execute
            )
        except Exception as e:
            self._handle_api_error(e)

        from app.core.config import settings
        sender_clean = (sender_email or settings.sender_email or "").lower().strip()

        messages = thread.get("messages", [])
        result = []
        for msg in messages:
            headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
            from_header = headers.get("from", "").lower()
            label_ids = msg.get("labelIds", [])

            if "SENT" in label_ids or (sender_clean and sender_clean in from_header):
                direction = "outbound"
            else:
                direction = "inbound"

            body_text = self._extract_body(msg)
            result.append({
                "gmail_message_id": msg["id"],
                "body_text": body_text,
                "direction": direction,
                "from": headers.get("from", ""),
            })

        return result

    def _build_message(
        self,
        to: str,
        subject: str,
        body: str,
        html: str | None = None,
        in_reply_to: str | None = None,
        references: str | None = None,
    ) -> MIMEMultipart | MIMEText:
        if html:
            message = MIMEMultipart("alternative")
            message["to"] = to
            message["subject"] = subject
            if in_reply_to:
                message["In-Reply-To"] = in_reply_to
            if references:
                message["References"] = references
            elif in_reply_to:
                message["References"] = in_reply_to
            message.attach(MIMEText(body, "plain"))
            message.attach(MIMEText(html, "html"))
            return message

        message = MIMEText(body, "plain")
        message["to"] = to
        message["subject"] = subject
        if in_reply_to:
            message["In-Reply-To"] = in_reply_to
        if references:
            message["References"] = references
        elif in_reply_to:
            message["References"] = in_reply_to
        return message

    def _extract_body(self, message: dict) -> str:
        payload = message.get("payload", {})
        parts = payload.get("parts", [])

        for part in parts:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

        return ""

    def _handle_api_error(self, error: Exception) -> None:
        err_str = str(error)
        if "429" in err_str or "rateLimitExceeded" in err_str:
            raise GmailRateLimitError(f"Gmail rate limit exceeded: {error}") from error
        raise GmailError(f"Gmail API error: {error}") from error

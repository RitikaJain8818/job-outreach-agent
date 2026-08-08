from __future__ import annotations

from datetime import UTC, datetime

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.core.exceptions import GmailError
from app.core.logging import get_logger
from app.integrations.gmail.client import GmailClient
from app.services.email_thread_service import EmailThreadService
from app.services.outreach_service import OutreachService

logger = get_logger(__name__)


class GmailAgent(BaseAgent):
    """
    Handles all Gmail operations with full DB persistence:

    mode="send"  — sends an email, creates EmailThread + EmailMessage records,
                   updates OutreachTarget status to "sent".
    mode="poll"  — fetches replies for a thread, records new inbound messages,
                   returns new replies for classification.
    """

    def __init__(
        self,
        gmail_client: GmailClient,
        outreach_service: OutreachService,
        thread_service: EmailThreadService,
    ) -> None:
        self._gmail = gmail_client
        self._outreach_svc = outreach_service
        self._thread_svc = thread_service

    @property
    def name(self) -> str:
        return "GmailAgent"

    async def run(self, context: AgentContext) -> AgentResult:
        mode = context.metadata.get("mode", "send")

        if mode == "send":
            return await self._send(context)
        if mode == "poll":
            return await self._poll(context)

        return AgentResult(
            success=False,
            agent_name=self.name,
            error=f"Unknown GmailAgent mode: {mode!r}",
        )

    async def _send(self, context: AgentContext) -> AgentResult:
        subject = context.metadata.get("email_subject", "")
        body = context.metadata.get("email_body", "")
        to_email = context.metadata.get("to_email", "")

        if not all([subject, body, to_email]):
            return AgentResult(
                success=False,
                agent_name=self.name,
                error="Missing email_subject, email_body, or to_email in context.metadata",
            )

        try:
            gmail_thread_id = await self._gmail.send(
                to=to_email, subject=subject, body=body
            )
        except GmailError as e:
            return AgentResult(success=False, agent_name=self.name, error=str(e))

        # Persist thread record
        thread = await self._thread_svc.create_thread(
            outreach_target_id=context.target_id,
            gmail_thread_id=gmail_thread_id,
            subject=subject,
        )

        # Persist outbound message (gmail_message_id = thread_id on first send)
        await self._thread_svc.record_outbound(
            thread_id=thread.id,
            gmail_message_id=gmail_thread_id,  # first message ID matches thread ID
            body_text=body,
            sent_at=datetime.now(UTC),
        )

        # Update target status to "sent"
        await self._outreach_svc.update_target_status(context.target_id, "sent")

        logger.info(
            "gmail.sent",
            to=to_email,
            gmail_thread_id=gmail_thread_id,
            thread_id=thread.id,
        )
        return AgentResult(
            success=True,
            agent_name=self.name,
            output={
                "thread_id": thread.id,
                "gmail_thread_id": gmail_thread_id,
            },
        )

    async def _poll(self, context: AgentContext) -> AgentResult:
        gmail_thread_id = context.metadata.get("gmail_thread_id", "")
        thread_db_id = context.metadata.get("thread_db_id", "")

        if not gmail_thread_id or not thread_db_id:
            return AgentResult(
                success=False,
                agent_name=self.name,
                error="Missing gmail_thread_id or thread_db_id in context.metadata for poll mode",
            )

        try:
            all_messages = await self._gmail.get_replies(thread_id=gmail_thread_id)
        except GmailError as e:
            return AgentResult(success=False, agent_name=self.name, error=str(e))

        # Detect only new inbound messages not yet stored
        known_ids = await self._thread_svc.get_known_message_ids(thread_db_id)
        new_replies = [
            m for m in all_messages
            if m["gmail_message_id"] not in known_ids
            and m.get("direction") == "inbound"
        ]

        for reply in new_replies:
            await self._thread_svc.record_inbound(
                thread_id=thread_db_id,
                gmail_message_id=reply["gmail_message_id"],
                body_text=reply.get("body_text", ""),
                received_at=datetime.now(UTC),
            )

        logger.info(
            "gmail.polled",
            gmail_thread_id=gmail_thread_id,
            total=len(all_messages),
            new_replies=len(new_replies),
        )
        return AgentResult(
            success=True,
            agent_name=self.name,
            output={
                "new_reply_count": str(len(new_replies)),
                "new_replies": str(new_replies),
            },
        )

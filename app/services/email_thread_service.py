from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.email_thread import EmailMessage, EmailThread

logger = get_logger(__name__)


class EmailThreadService:
    """
    Manages EmailThread and EmailMessage records.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_thread(
        self,
        outreach_target_id: str,
        gmail_thread_id: str,
        subject: str,
    ) -> EmailThread:
        thread = EmailThread(
            outreach_target_id=outreach_target_id,
            gmail_thread_id=gmail_thread_id,
            subject=subject,
        )
        self._session.add(thread)
        await self._session.commit()
        await self._session.refresh(thread)
        logger.info("thread.created", thread_id=thread.id, gmail_thread_id=gmail_thread_id)
        return thread

    async def record_outbound(
        self,
        thread_id: str,
        gmail_message_id: str,
        body_text: str,
        body_html: str | None = None,
        sent_at: datetime | None = None,
    ) -> EmailMessage:
        msg = EmailMessage(
            thread_id=thread_id,
            gmail_message_id=gmail_message_id,
            direction="outbound",
            body_text=body_text,
            body_html=body_html,
            sent_at=sent_at or datetime.now(UTC),
        )
        self._session.add(msg)
        await self._session.commit()
        await self._session.refresh(msg)
        return msg

    async def record_inbound(
        self,
        thread_id: str,
        gmail_message_id: str,
        body_text: str,
        received_at: datetime | None = None,
    ) -> EmailMessage:
        msg = EmailMessage(
            thread_id=thread_id,
            gmail_message_id=gmail_message_id,
            direction="inbound",
            body_text=body_text,
            sent_at=received_at or datetime.now(UTC),
        )
        self._session.add(msg)
        await self._session.commit()
        await self._session.refresh(msg)
        return msg

    async def get_thread_by_gmail_id(self, gmail_thread_id: str) -> EmailThread | None:
        stmt = (
            select(EmailThread)
            .where(EmailThread.gmail_thread_id == gmail_thread_id)
            .options(selectinload(EmailThread.messages))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_thread_by_target_id(self, outreach_target_id: str) -> EmailThread | None:
        """Return the EmailThread for a given outreach target (with messages eagerly loaded)."""
        stmt = (
            select(EmailThread)
            .where(EmailThread.outreach_target_id == outreach_target_id)
            .options(selectinload(EmailThread.messages))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_known_message_ids(self, thread_id: str) -> set[str]:
        """Return gmail_message_ids already stored — used to detect new replies."""
        stmt = select(EmailMessage.gmail_message_id).where(
            EmailMessage.thread_id == thread_id
        )
        result = await self._session.execute(stmt)
        return {row[0] for row in result.all()}

    async def get_threads_for_polling(self) -> list[EmailThread]:
        """Return all threads (legacy — use get_threads_for_active_targets for Phase 4)."""
        result = await self._session.execute(select(EmailThread))
        return list(result.scalars().all())

    # ── Phase 4 additions ───────────────────────────────────────────────────────────

    async def update_message_classification(
        self,
        message_id: str,
        classification: str,
        confidence: float,
    ) -> None:
        """Persist reply classification result onto an EmailMessage row."""
        msg = await self._session.get(EmailMessage, message_id)
        if msg is None:
            logger.warning("thread_svc.message_not_found", message_id=message_id)
            return
        msg.classification = classification
        msg.classification_confidence = confidence
        await self._session.commit()
        logger.info(
            "message.classified",
            message_id=message_id,
            classification=classification,
            confidence=confidence,
        )

    async def get_threads_for_active_targets(self) -> list[EmailThread]:
        """
        Return EmailThread rows whose outreach_target has status='sent'.
        Used by the scheduler poll-replies job.
        """
        from app.models.outreach import OutreachTarget  # local import avoids circular

        stmt = (
            select(EmailThread)
            .join(
                OutreachTarget,
                EmailThread.outreach_target_id == OutreachTarget.id,
            )
            .where(OutreachTarget.status == "sent")
            .options(selectinload(EmailThread.messages))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

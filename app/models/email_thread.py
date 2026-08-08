from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class EmailThread(Base):
    __tablename__ = "email_threads"

    __table_args__ = (Index("ix_email_threads_gmail_thread_id", "gmail_thread_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    outreach_target_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("outreach_targets.id"), nullable=False
    )
    gmail_thread_id: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    messages: Mapped[list["EmailMessage"]] = relationship(
        "EmailMessage", back_populates="thread", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<EmailThread id={self.id!r} gmail_thread_id={self.gmail_thread_id!r}>"


class EmailMessage(Base):
    __tablename__ = "email_messages"

    __table_args__ = (Index("ix_email_messages_gmail_message_id", "gmail_message_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    thread_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("email_threads.id"), nullable=False
    )
    gmail_message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    # Allowed: "outbound" | "inbound"
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    classification: Mapped[str | None] = mapped_column(String(50), nullable=True)
    classification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    thread: Mapped["EmailThread"] = relationship("EmailThread", back_populates="messages")

    def __repr__(self) -> str:
        return f"<EmailMessage id={self.id!r} direction={self.direction!r}>"

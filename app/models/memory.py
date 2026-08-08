from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AgentMemory(Base):
    """Key-value store for agent learnings, outcomes, and persistent context."""

    __tablename__ = "agent_memory"

    __table_args__ = (Index("ix_agent_memory_scope_key", "scope", "key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scope: Mapped[str] = mapped_column(String(100), nullable=False)
    # Examples: "global", "domain:fintech", "contact:<id>", "campaign:<id>"
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)  # JSON or plain text
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    # Which agent wrote this: "MemoryAgent", "EmailGeneratorAgent", etc.
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<AgentMemory scope={self.scope!r} key={self.key!r}>"

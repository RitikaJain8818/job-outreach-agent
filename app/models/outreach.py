from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OutreachCampaign(Base):
    __tablename__ = "outreach_campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    sender_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sender_email: Mapped[str] = mapped_column(String(255), nullable=False)
    follow_up_days: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    max_follow_ups: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    # Allowed: "draft" | "active" | "paused" | "completed"
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    targets: Mapped[list["OutreachTarget"]] = relationship(
        "OutreachTarget", back_populates="campaign", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<OutreachCampaign id={self.id!r} name={self.name!r}>"


class OutreachTarget(Base):
    __tablename__ = "outreach_targets"

    __table_args__ = (UniqueConstraint("campaign_id", "contact_id", name="uq_campaign_contact"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("outreach_campaigns.id"), nullable=False
    )
    contact_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contacts.id"), nullable=False
    )
    job_opening_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("job_openings.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    # Allowed: "pending" | "sent" | "replied" | "bounced" |
    #          "not_interested" | "interested" | "opted_out"
    follow_up_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_action_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    campaign: Mapped["OutreachCampaign"] = relationship("OutreachCampaign", back_populates="targets")

    def __repr__(self) -> str:
        return f"<OutreachTarget id={self.id!r} status={self.status!r}>"

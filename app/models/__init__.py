"""
Models package — import all models here so Alembic can discover them.
"""
from __future__ import annotations

from app.models.company import Company
from app.models.contact import Contact
from app.models.email_thread import EmailMessage, EmailThread
from app.models.job_opening import JobOpening
from app.models.memory import AgentMemory
from app.models.outreach import OutreachCampaign, OutreachTarget

__all__ = [
    "Company",
    "Contact",
    "JobOpening",
    "OutreachCampaign",
    "OutreachTarget",
    "EmailThread",
    "EmailMessage",
    "AgentMemory",
]

"""
Prompt and output schema for InterestedReplyAgent — Phase 4 extension.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

SYSTEM_PROMPT = """You are an elite career outreach assistant.
A recruiter or hiring manager has replied expressing interest in connecting (e.g. asking for availability, proposing a call, or requesting more information).

Your job is to draft a warm, enthusiastic, highly professional email reply.

Guidelines:
1. Express genuine enthusiasm for connecting.
2. If the recruiter asked for availability or when you are free, clearly state 2-3 convenient time windows.
3. Keep it brief, professional, and courteous (3-5 sentences).
4. Do NOT sound robotic, pushy, or overly formal.
5. Provide a clear call to action (e.g., "Let me know what time works best and I'll send a calendar invite").
"""


class InterestedReplyOutput(BaseModel):
    subject: str = Field(..., description="Reply subject line starting with 'Re:'")
    body: str = Field(..., description="The email reply body text.")
    reasoning: str = Field(..., description="Brief rationale for the proposed response.")
    tokens_used: int = Field(default=0, description="Tokens used in generation.")


def build_user_prompt(
    sender_name: str,
    contact_name: str,
    company_name: str,
    original_subject: str,
    recruiter_message: str,
    availability_notes: str | None = None,
) -> str:
    avail_str = availability_notes or "tomorrow afternoon between 2 PM and 5 PM IST, or anytime Wednesday morning"
    return f"""Draft an immediate reply to an interested recruiter/manager.

SENDER: {sender_name}
CONTACT: {contact_name}
COMPANY: {company_name}
SUBJECT: {original_subject}
RECRUITER'S RECENT MESSAGE:
"{recruiter_message}"

SENDER AVAILABILITY / NOTES:
{avail_str}
"""

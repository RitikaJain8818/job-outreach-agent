"""
Prompt and output schema for InterestedReplyAgent — Phase 4 extension.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

SYSTEM_PROMPT = """You are an elite career outreach assistant writing an email response to a recruiter or hiring manager who has expressed interest in connecting.

CRITICAL GREETING AND SIGN-OFF RULES:
1. GREETING: Address the RECRUITER (the person who sent the message). Use their first name. For example, if the recruiter's name is "Alex", start with "Hi Alex," or "Hello Alex,". NEVER address the email to the sender!
2. SIGN-OFF: Sign off with the applicant/sender's name. For example, "Best regards,\n[Sender Name]".

Message Guidelines:
- Express genuine enthusiasm for connecting.
- If the recruiter asked for availability, clearly state 2-3 convenient time windows.
- Keep it brief, professional, and courteous (3-5 sentences).
- Do NOT sound robotic or pushy.
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
    first_name = contact_name.split()[0] if contact_name else "there"
    return f"""Draft an immediate reply to an interested recruiter/manager.

RECRUITER/RECIPIENT NAME (to greet in email): {contact_name} (First Name: {first_name})
APPLICANT/SENDER NAME (to sign off email): {sender_name}
COMPANY: {company_name}
SUBJECT: {original_subject}

RECRUITER'S RECENT MESSAGE:
"{recruiter_message}"

SENDER AVAILABILITY / NOTES:
{avail_str}

REMINDER: Start the email with "Hi {first_name}," and end the email signed off as "{sender_name}".
"""

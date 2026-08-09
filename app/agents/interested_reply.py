"""
InterestedReplyAgent — Phase 4 Extension.

Generates an immediate, warm response when a recruiter or hiring manager expresses interest.
"""
from __future__ import annotations

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.core.exceptions import AgentError, LLMProviderError
from app.core.logging import get_logger
from app.integrations.llm.base import LLMProvider
from app.prompts.interested_reply_v1 import SYSTEM_PROMPT, InterestedReplyOutput, build_user_prompt

logger = get_logger(__name__)


DEFAULT_REPLY_TEMPLATE = """Hi {first_name},

Thanks for getting back to me! I'd love to connect.

I am available tomorrow afternoon between 2:00 PM and 5:00 PM IST, or anytime Wednesday morning. Please let me know what time works best for you and I'll send over a calendar invite.

Best regards,
{sender_name}"""


class InterestedReplyAgent(BaseAgent):
    """
    Generates a prompt response when a target responds with interest.
    """

    def __init__(self, llm: LLMProvider | None = None) -> None:
        self._llm = llm

    @property
    def name(self) -> str:
        return "InterestedReplyAgent"

    async def run(self, context: AgentContext) -> AgentResult:
        contact_name = context.metadata.get("contact_name", "there")
        first_name = contact_name.split()[0] if contact_name else "there"
        sender_name = context.metadata.get("sender_name", "Applicant")
        company_name = context.metadata.get("company_name", "your team")
        original_subject = context.metadata.get("original_subject", "Re: Connect")
        recruiter_message = context.metadata.get("recruiter_message", "")
        availability_notes = context.metadata.get("availability_notes")
        use_template = context.metadata.get("use_template", False)

        # Mode 1: Template mode (0 LLM cost) or fallback
        if use_template or self._llm is None:
            subject = original_subject if original_subject.startswith("Re:") else f"Re: {original_subject}"
            body = DEFAULT_REPLY_TEMPLATE.format(
                first_name=first_name,
                sender_name=sender_name,
            )
            return AgentResult(
                success=True,
                agent_name=self.name,
                output={"subject": subject, "body": body, "reasoning": "Generated using template"},
                tokens_used=0,
            )

        # Mode 2: AI synthesis via LLM
        user_prompt = build_user_prompt(
            sender_name=sender_name,
            contact_name=contact_name,
            company_name=company_name,
            original_subject=original_subject,
            recruiter_message=recruiter_message,
            availability_notes=availability_notes,
        )

        try:
            result: InterestedReplyOutput = await self._llm.complete_structured(
                system=SYSTEM_PROMPT,
                user=user_prompt,
                schema=InterestedReplyOutput,
            )
            return AgentResult(
                success=True,
                agent_name=self.name,
                output={
                    "subject": result.subject,
                    "body": result.body,
                    "reasoning": result.reasoning,
                },
                tokens_used=result.tokens_used,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("interested_reply.llm_failed_using_template", error=str(e))
            subject = original_subject if original_subject.startswith("Re:") else f"Re: {original_subject}"
            body = DEFAULT_REPLY_TEMPLATE.format(
                first_name=first_name,
                sender_name=sender_name,
            )
            return AgentResult(
                success=True,
                agent_name=self.name,
                output={"subject": subject, "body": body, "reasoning": f"Template fallback: {e}"},
                tokens_used=0,
            )

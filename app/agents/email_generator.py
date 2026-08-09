from __future__ import annotations

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.core.exceptions import AgentError, LLMProviderError
from app.core.logging import get_logger
from app.integrations.llm.base import LLMProvider
from app.prompts.email_generation_v1 import SYSTEM_PROMPT, EmailGenerationOutput, build_user_prompt
from app.services.contact_service import ContactService

logger = get_logger(__name__)


DEFAULT_SUBJECT_TEMPLATE = "Exploring {job_title} opportunities at {company_name} — {sender_name}"

DEFAULT_BODY_TEMPLATE = """Hi {first_name},

I noticed {company_name} is scaling its team for {job_title} roles.

With my background in {sender_background}, I have built scalable software systems and end-to-end applications. I'm really impressed by what {company_name} is building and would love to explore how my experience aligns with your team's goals.

Would you be open to a quick 10-minute chat this week?

Best regards,
{sender_name}"""


class EmailGeneratorAgent(BaseAgent):
    """
    Generates a cold outreach email using either template substitution (0 LLM cost)
    or LLM synthesis with automatic template fallback.
    """

    def __init__(
        self,
        llm: LLMProvider | None = None,
        contact_service: ContactService | None = None,
    ) -> None:
        self._llm = llm
        self._contact_svc = contact_service

    @property
    def name(self) -> str:
        return "EmailGeneratorAgent"

    def generate_from_template(
        self,
        first_name: str,
        company_name: str,
        job_title: str,
        sender_name: str,
        sender_background: str,
        subject_template: str | None = None,
        body_template: str | None = None,
    ) -> tuple[str, str]:
        """Substitute variables into template — 0 LLM API calls."""
        subj_tmpl = subject_template or DEFAULT_SUBJECT_TEMPLATE
        body_tmpl = body_template or DEFAULT_BODY_TEMPLATE

        replacements = {
            "first_name": first_name or "there",
            "company_name": company_name or "your company",
            "job_title": job_title or "Engineering",
            "sender_name": sender_name or "Applicant",
            "sender_background": sender_background or "software engineering",
        }

        subject = subj_tmpl.format(**replacements)
        body = body_tmpl.format(**replacements)
        return subject, body

    async def run(self, context: AgentContext) -> AgentResult:
        contact = None
        if self._contact_svc and context.contact_id:
            contact = await self._contact_svc.get_with_company(context.contact_id)

        first_name = (
            contact.first_name if contact else context.metadata.get("first_name", "")
        )
        company_name = (
            contact.company.name if (contact and contact.company) else context.metadata.get("company_name", "")
        )
        job_title = context.metadata.get("job_title", "Software Engineer")
        sender_name = context.metadata.get("sender_name", "")
        sender_background = context.metadata.get("sender_background", "")
        use_template = context.metadata.get("use_template", False)

        # Mode 1: Template mode requested explicitly (0 LLM cost)
        if use_template or self._llm is None:
            subject, body = self.generate_from_template(
                first_name=first_name,
                company_name=company_name,
                job_title=job_title,
                sender_name=sender_name,
                sender_background=sender_background,
                subject_template=context.metadata.get("subject_template"),
                body_template=context.metadata.get("body_template"),
            )
            logger.info("email.generated_from_template", contact_id=context.contact_id)
            return AgentResult(
                success=True,
                agent_name=self.name,
                output={
                    "subject": subject,
                    "body": body,
                    "reasoning": "Generated using email template (0 LLM tokens)",
                },
                tokens_used=0,
            )

        # Mode 2: AI mode with template fallback
        if contact is None:
            return AgentResult(
                success=False,
                agent_name=self.name,
                error=f"Contact {context.contact_id} not found",
            )

        user_prompt = build_user_prompt(
            sender_name=sender_name,
            sender_background=sender_background,
            contact=contact,
            personalization_notes=context.metadata.get("personalization_notes", ""),
            past_performance=context.metadata.get("past_performance", ""),
            tone=context.metadata.get("tone", "professional"),
            job_title=job_title,
        )

        try:
            result: EmailGenerationOutput = await self._llm.complete_structured(
                system=SYSTEM_PROMPT,
                user=user_prompt,
                schema=EmailGenerationOutput,
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
            logger.warning(
                "email.llm_failed_using_template_fallback",
                contact_id=context.contact_id,
                error=str(e),
            )
            subject, body = self.generate_from_template(
                first_name=first_name,
                company_name=company_name,
                job_title=job_title,
                sender_name=sender_name,
                sender_background=sender_background,
            )
            return AgentResult(
                success=True,
                agent_name=self.name,
                output={
                    "subject": subject,
                    "body": body,
                    "reasoning": f"Fallback to template due to LLM error: {e}",
                },
                tokens_used=0,
            )

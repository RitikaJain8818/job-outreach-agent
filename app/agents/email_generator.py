from __future__ import annotations

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.core.exceptions import AgentError, LLMProviderError
from app.core.logging import get_logger
from app.integrations.llm.base import LLMProvider
from app.prompts.email_generation_v1 import SYSTEM_PROMPT, EmailGenerationOutput, build_user_prompt
from app.services.contact_service import ContactService

logger = get_logger(__name__)


class EmailGeneratorAgent(BaseAgent):
    """
    Generates a personalized cold outreach email using an LLM.
    """

    def __init__(self, llm: LLMProvider, contact_service: ContactService) -> None:
        self._llm = llm
        self._contact_svc = contact_service

    @property
    def name(self) -> str:
        return "EmailGeneratorAgent"

    async def run(self, context: AgentContext) -> AgentResult:
        contact = await self._contact_svc.get_with_company(context.contact_id)
        if contact is None:
            return AgentResult(
                success=False,
                agent_name=self.name,
                error=f"Contact {context.contact_id} not found",
            )

        user_prompt = build_user_prompt(
            sender_name=context.metadata.get("sender_name", ""),
            sender_background=context.metadata.get("sender_background", ""),
            contact=contact,
            personalization_notes=context.metadata.get("personalization_notes", ""),
            past_performance=context.metadata.get("past_performance", ""),
            tone=context.metadata.get("tone", "professional"),
            job_title=context.metadata.get("job_title"),
        )

        try:
            result: EmailGenerationOutput = await self._llm.complete_structured(
                system=SYSTEM_PROMPT,
                user=user_prompt,
                schema=EmailGenerationOutput,
            )
        except LLMProviderError as e:
            raise AgentError(f"EmailGeneratorAgent LLM call failed: {e}") from e

        logger.info(
            "email.generated",
            contact_id=context.contact_id,
            subject=result.subject[:60],
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

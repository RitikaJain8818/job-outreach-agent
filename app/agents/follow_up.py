from __future__ import annotations

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.core.exceptions import AgentError, LLMProviderError
from app.core.logging import get_logger
from app.integrations.llm.base import LLMProvider
from app.prompts.follow_up_v1 import SYSTEM_PROMPT, FollowUpOutput, build_user_prompt

logger = get_logger(__name__)


class FollowUpAgent(BaseAgent):
    """
    Generates follow-up emails when a target hasn't replied.
    """

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    @property
    def name(self) -> str:
        return "FollowUpAgent"

    async def run(self, context: AgentContext) -> AgentResult:
        required = [
            "original_subject",
            "contact_name",
            "company_name",
            "sender_name",
            "follow_up_number",
            "days_since_last_email",
        ]
        missing = [k for k in required if not context.metadata.get(k)]
        if missing:
            return AgentResult(
                success=False,
                agent_name=self.name,
                error=f"Missing context.metadata keys: {missing}",
            )

        user_prompt = build_user_prompt(
            sender_name=context.metadata["sender_name"],
            contact_name=context.metadata["contact_name"],
            company_name=context.metadata["company_name"],
            original_subject=context.metadata["original_subject"],
            original_body=context.metadata.get("original_body", ""),
            follow_up_number=int(context.metadata["follow_up_number"]),
            days_since_last_email=int(context.metadata["days_since_last_email"]),
        )

        try:
            result: FollowUpOutput = await self._llm.complete_structured(
                system=SYSTEM_PROMPT,
                user=user_prompt,
                schema=FollowUpOutput,
            )
        except LLMProviderError as e:
            raise AgentError(f"FollowUpAgent LLM call failed: {e}") from e

        logger.info(
            "followup.generated",
            target_id=context.target_id,
            follow_up_number=context.metadata["follow_up_number"],
        )

        return AgentResult(
            success=True,
            agent_name=self.name,
            output={"subject": result.subject, "body": result.body},
            tokens_used=result.tokens_used,
        )

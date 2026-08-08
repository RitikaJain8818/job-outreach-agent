from __future__ import annotations

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.core.exceptions import AgentError, LLMProviderError
from app.core.logging import get_logger
from app.integrations.llm.base import LLMProvider
from app.prompts.reply_classification_v1 import (
    SYSTEM_PROMPT,
    ReplyClassificationOutput,
    build_user_prompt,
)

logger = get_logger(__name__)


class ReplyClassifierAgent(BaseAgent):
    """
    Classifies the intent of an inbound email reply using an LLM.
    """

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    @property
    def name(self) -> str:
        return "ReplyClassifierAgent"

    async def run(self, context: AgentContext) -> AgentResult:
        reply_body = context.metadata.get("reply_body", "")
        original_subject = context.metadata.get("original_subject", "")

        if not reply_body:
            return AgentResult(
                success=False,
                agent_name=self.name,
                error="Missing reply_body in context.metadata",
            )

        user_prompt = build_user_prompt(
            reply_body=reply_body,
            original_subject=original_subject,
        )

        try:
            result: ReplyClassificationOutput = await self._llm.complete_structured(
                system=SYSTEM_PROMPT,
                user=user_prompt,
                schema=ReplyClassificationOutput,
            )
        except LLMProviderError as e:
            raise AgentError(f"ReplyClassifierAgent LLM call failed: {e}") from e

        logger.info(
            "reply.classified",
            target_id=context.target_id,
            classification=result.classification,
            confidence=result.confidence,
        )

        return AgentResult(
            success=True,
            agent_name=self.name,
            output={
                "classification": result.classification,
                "confidence": str(result.confidence),
                "reasoning": result.reasoning,
            },
            tokens_used=result.tokens_used,
        )

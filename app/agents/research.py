from __future__ import annotations

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.core.logging import get_logger

logger = get_logger(__name__)


class ResearchAgent(BaseAgent):
    """
    Enriches contact and company data from available sources.
    """

    @property
    def name(self) -> str:
        return "ResearchAgent"

    async def run(self, context: AgentContext) -> AgentResult:
        logger.debug("research.stub", target_id=context.target_id)
        return AgentResult(
            success=True,
            agent_name=self.name,
            output={"enrichment": "stub — no enrichment in Phase 1"},
        )

from __future__ import annotations

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.core.logging import get_logger

logger = get_logger(__name__)


class ResearchAgent(BaseAgent):
    """
    Enriches contact and company data from available sources.

    Phase 1: Stub — returns empty enrichment.
    Phase 6: Will integrate LinkedIn, Hunter.io, Clearbit, HN Jobs.
    """

    @property
    def name(self) -> str:
        return "ResearchAgent"

    async def run(self, context: AgentContext) -> AgentResult:
        # Phase 1 stub — no external enrichment yet.
        # Future: fetch LinkedIn data, recent company news, job postings.
        logger.debug("research.stub", target_id=context.target_id)
        return AgentResult(
            success=True,
            agent_name=self.name,
            output={"enrichment": "stub — no enrichment in Phase 1"},
        )

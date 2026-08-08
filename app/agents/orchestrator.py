from __future__ import annotations

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.agents.email_generator import EmailGeneratorAgent
from app.agents.follow_up import FollowUpAgent
from app.agents.gmail_agent import GmailAgent
from app.agents.memory import MemoryAgent
from app.agents.reply_classifier import ReplyClassifierAgent
from app.agents.research import ResearchAgent
from app.core.logging import get_logger

logger = get_logger(__name__)


class OrchestratorAgent(BaseAgent):
    """
    Coordinates the outreach send pipeline for a single OutreachTarget.

    Pipeline:
        MemoryAgent (read) → ResearchAgent → EmailGeneratorAgent
        → GmailAgent (send) → MemoryAgent (write outcome)

    The orchestrator:
    - Aborts on critical failures (email gen, gmail send)
    - Continues on non-critical failures (memory read, research)
    - Bridges EmailGeneratorAgent output into GmailAgent metadata
    - Records outcome into MemoryAgent

    Reply classification and follow-ups run as separate scheduled pipelines.
    """

    def __init__(
        self,
        memory_agent: MemoryAgent,
        research_agent: ResearchAgent,
        email_generator: EmailGeneratorAgent,
        gmail_agent: GmailAgent,
        reply_classifier: ReplyClassifierAgent,
        follow_up_agent: FollowUpAgent,
    ) -> None:
        self._memory = memory_agent
        self._research = research_agent
        self._email_gen = email_generator
        self._gmail = gmail_agent
        self._reply_classifier = reply_classifier
        self._follow_up = follow_up_agent

    @property
    def name(self) -> str:
        return "OrchestratorAgent"

    async def run(self, context: AgentContext) -> AgentResult:
        results: dict[str, AgentResult] = {}

        # 1. Load memory context (non-critical)
        context.metadata["mode"] = "read"
        context.metadata["scope"] = f"campaign:{context.campaign_id}"
        results["memory_read"] = await self._memory.execute(context)

        # 2. Enrich contact/company data (non-critical)
        results["research"] = await self._research.execute(context)

        # 3. Generate personalized email (critical)
        results["email_gen"] = await self._email_gen.execute(context)
        if not results["email_gen"].success:
            return AgentResult(
                success=False,
                agent_name=self.name,
                error=f"Email generation failed: {results['email_gen'].error}",
            )

        # ── Bridge: forward email content into GmailAgent metadata ──
        email_output = results["email_gen"].output
        context.metadata["mode"] = "send"
        context.metadata["email_subject"] = str(email_output.get("subject", ""))
        context.metadata["email_body"] = str(email_output.get("body", ""))
        # to_email must be set by the caller in context.metadata before orchestrator runs

        # 4. Send email via Gmail (critical)
        results["gmail_send"] = await self._gmail.execute(context)
        if not results["gmail_send"].success:
            return AgentResult(
                success=False,
                agent_name=self.name,
                error=f"Gmail send failed: {results['gmail_send'].error}",
            )

        gmail_output = results["gmail_send"].output

        # 5. Write outcome to memory (non-critical)
        context.metadata["mode"] = "write"
        context.metadata["scope"] = f"campaign:{context.campaign_id}"
        context.metadata["memory_key"] = f"sent:target:{context.target_id}"
        context.metadata["memory_value"] = (
            f"subject={email_output.get('subject', '')} "
            f"thread_id={gmail_output.get('gmail_thread_id', '')}"
        )
        context.metadata["source"] = self.name
        results["memory_write"] = await self._memory.execute(context)

        total_tokens = sum(r.tokens_used for r in results.values())
        return AgentResult(
            success=True,
            agent_name=self.name,
            output={
                "thread_id": gmail_output.get("thread_id", ""),
                "gmail_thread_id": gmail_output.get("gmail_thread_id", ""),
                "email_subject": email_output.get("subject", ""),
            },
            tokens_used=total_tokens,
        )

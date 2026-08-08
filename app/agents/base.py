from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AgentContext:
    """Shared context passed through the agent pipeline."""

    campaign_id: str
    target_id: str
    contact_id: str
    company_id: str
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Standardized result returned by every agent."""

    success: bool
    agent_name: str
    output: dict[str, str | int | float | bool | None] = field(default_factory=dict)
    error: str | None = None
    tokens_used: int = 0


class BaseAgent(ABC):
    """
    Abstract base for all agents.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable agent name."""

    @abstractmethod
    async def run(self, context: AgentContext) -> AgentResult:
        """Execute the agent's primary task."""

    async def execute(self, context: AgentContext) -> AgentResult:
        """Wraps run() with entry/exit logging."""
        logger.info(
            "agent.start",
            agent=self.name,
            target_id=context.target_id,
            campaign_id=context.campaign_id,
        )
        result = await self.run(context)
        if result.success:
            logger.info(
                "agent.success",
                agent=self.name,
                target_id=context.target_id,
                tokens_used=result.tokens_used,
            )
        else:
            logger.error(
                "agent.failed",
                agent=self.name,
                target_id=context.target_id,
                error=result.error,
            )
        return result

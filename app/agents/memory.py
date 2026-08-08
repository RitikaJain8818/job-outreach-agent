from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.core.logging import get_logger
from app.models.memory import AgentMemory

logger = get_logger(__name__)


class MemoryAgent(BaseAgent):
    """
    Reads and writes to the agent_memory table.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def name(self) -> str:
        return "MemoryAgent"

    async def run(self, context: AgentContext) -> AgentResult:
        mode = context.metadata.get("mode", "read")
        scope = context.metadata.get("scope", f"campaign:{context.campaign_id}")

        if mode == "read":
            return await self._read(context, scope)
        if mode == "write":
            return await self._write(context, scope)

        return AgentResult(
            success=False,
            agent_name=self.name,
            error=f"Unknown MemoryAgent mode: {mode!r}",
        )

    async def _read(self, context: AgentContext, scope: str) -> AgentResult:
        stmt = select(AgentMemory).where(AgentMemory.scope == scope)
        result = await self._session.execute(stmt)
        memories = result.scalars().all()

        for mem in memories:
            context.metadata[f"memory:{mem.key}"] = mem.value

        logger.debug("memory.read", scope=scope, count=len(memories))
        return AgentResult(
            success=True,
            agent_name=self.name,
            output={"loaded_count": str(len(memories))},
        )

    async def _write(self, context: AgentContext, scope: str) -> AgentResult:
        key = context.metadata.get("memory_key", "")
        value = context.metadata.get("memory_value", "")
        source = context.metadata.get("source", self.name)

        if not key or not value:
            return AgentResult(
                success=False,
                agent_name=self.name,
                error="Write mode requires memory_key and memory_value in context.metadata",
            )

        memory = AgentMemory(scope=scope, key=key, value=value, source=source)
        self._session.add(memory)
        await self._session.commit()

        logger.info("memory.written", scope=scope, key=key, source=source)
        return AgentResult(success=True, agent_name=self.name, output={"key": key})

"""
Unit tests for ReplyClassifierAgent — Phase 4.
"""
from __future__ import annotations

import pytest

from app.agents.base import AgentContext
from app.agents.reply_classifier import ReplyClassifierAgent
from tests.conftest import MockLLMProvider


def _make_context(**metadata) -> AgentContext:
    return AgentContext(
        campaign_id="camp-1",
        target_id="tgt-1",
        contact_id="con-1",
        company_id="co-1",
        metadata=metadata,
    )


@pytest.fixture
def classifier_interested() -> ReplyClassifierAgent:
    llm = MockLLMProvider(
        response_json=(
            '{"classification": "interested", "confidence": 0.95, '
            '"reasoning": "Recipient expressed interest in connecting", '
            '"tokens_used": 80}'
        )
    )
    return ReplyClassifierAgent(llm=llm)


@pytest.fixture
def classifier_auto_reply() -> ReplyClassifierAgent:
    llm = MockLLMProvider(
        response_json=(
            '{"classification": "auto_reply", "confidence": 0.99, '
            '"reasoning": "Out-of-office message detected", '
            '"tokens_used": 50}'
        )
    )
    return ReplyClassifierAgent(llm=llm)


@pytest.mark.asyncio
async def test_classifies_interested_reply(classifier_interested: ReplyClassifierAgent) -> None:
    ctx = _make_context(
        reply_body="Hi! This sounds exciting. Let's set up a call next week.",
        original_subject="Quick question about your ML team",
    )
    result = await classifier_interested.execute(ctx)

    assert result.success is True
    assert result.agent_name == "ReplyClassifierAgent"
    assert result.output["classification"] == "interested"
    assert float(result.output["confidence"]) > 0.9  # type: ignore[arg-type]
    assert result.tokens_used == 80


@pytest.mark.asyncio
async def test_classifies_auto_reply(classifier_auto_reply: ReplyClassifierAgent) -> None:
    ctx = _make_context(
        reply_body="I am out of office until August 20th. I will reply when I return.",
        original_subject="Quick question about your ML team",
    )
    result = await classifier_auto_reply.execute(ctx)

    assert result.success is True
    assert result.output["classification"] == "auto_reply"


@pytest.mark.asyncio
async def test_missing_reply_body_returns_error(classifier_interested: ReplyClassifierAgent) -> None:
    """When reply_body is missing, the agent should return a failure result (not raise)."""
    ctx = _make_context(original_subject="Quick question about your ML team")
    result = await classifier_interested.execute(ctx)

    assert result.success is False
    assert "reply_body" in (result.error or "").lower()

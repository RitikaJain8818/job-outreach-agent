from __future__ import annotations

import pytest

from app.agents.base import AgentContext
from app.agents.reply_classifier import ReplyClassifierAgent
from tests.conftest import MockLLMProvider


@pytest.mark.asyncio
async def test_reply_classifier_classifies_interested(
    mock_llm_classify: MockLLMProvider,
) -> None:
    agent = ReplyClassifierAgent(llm=mock_llm_classify)

    context = AgentContext(
        campaign_id="camp-1",
        target_id="target-1",
        contact_id="contact-1",
        company_id="company-1",
        metadata={
            "reply_body": "Hi! Thanks for reaching out. Would love to chat more about this.",
            "original_subject": "Quick question about your ML team",
        },
    )

    result = await agent.execute(context)

    assert result.success is True
    assert result.output["classification"] == "interested"
    assert float(result.output["confidence"]) > 0.5


@pytest.mark.asyncio
async def test_reply_classifier_fails_without_reply_body(
    mock_llm_classify: MockLLMProvider,
) -> None:
    agent = ReplyClassifierAgent(llm=mock_llm_classify)

    context = AgentContext(
        campaign_id="camp-1",
        target_id="target-1",
        contact_id="contact-1",
        company_id="company-1",
        metadata={},  # Missing reply_body
    )

    result = await agent.execute(context)

    assert result.success is False
    assert "reply_body" in (result.error or "")

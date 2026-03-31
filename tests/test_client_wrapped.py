"""Tests: guardrailed LLM client (sync structured path)."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from app.llm.client_wrapped import safe_llm_call, safe_llm_call_sync
from app.llm.context import LlmCallContext
from app.llm.exceptions import LLMContractViolation
from app.llm_models import LLMProvider, LLMResponse, LLMTaskType
from app.operational_monitoring_models import OamiExplanationOut


def _patch_router_returns(resp: LLMResponse) -> patch:
    instance = MagicMock()
    instance.route_and_call.return_value = resp
    return patch("app.llm.client_wrapped.LLMRouter", return_value=instance)


def test_safe_llm_call_sync_valid_json() -> None:
    ctx = LlmCallContext(
        tenant_id="t-wrap",
        user_role="tenant_admin",
        action_name="test_structured",
    )
    fake = LLMResponse(
        text='{"summary_de":"S","drivers_de":[],"monitoring_gap_de":null}',
        provider=LLMProvider.OPENAI,
        model_id="m",
    )

    with _patch_router_returns(fake):
        out = safe_llm_call_sync(
            "prompt",
            OamiExplanationOut,
            context=ctx,
            session=None,
            task_type=LLMTaskType.STRUCTURED_OUTPUT,
            response_format="json_object",
        )
    assert out.summary_de == "S"


def test_safe_llm_call_async_matches_sync() -> None:
    ctx = LlmCallContext(tenant_id="t-async", action_name="async_test")
    fake = LLMResponse(
        text='{"summary_de":"A","drivers_de":[],"monitoring_gap_de":null}',
        provider=LLMProvider.OPENAI,
        model_id="m",
    )

    async def _run() -> OamiExplanationOut:
        with _patch_router_returns(fake):
            return await safe_llm_call(
                "p",
                OamiExplanationOut,
                context=ctx,
                session=None,
                task_type=LLMTaskType.STRUCTURED_OUTPUT,
            )

    out = asyncio.run(_run())
    assert out.summary_de == "A"


def test_safe_llm_call_sync_invalid_json_raises() -> None:
    ctx = LlmCallContext(tenant_id="t-bad", action_name="test")
    fake = LLMResponse(text="not json", provider=LLMProvider.OPENAI, model_id="m")

    with _patch_router_returns(fake):
        with pytest.raises(LLMContractViolation):
            safe_llm_call_sync(
                "x",
                OamiExplanationOut,
                context=ctx,
                session=None,
                task_type=LLMTaskType.STRUCTURED_OUTPUT,
            )

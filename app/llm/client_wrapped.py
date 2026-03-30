"""Guardrailed LLM invocation (async + sync) over the existing LLMRouter."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, TypeVar

from pydantic import BaseModel

from app.llm.context import LlmCallContext
from app.llm.exceptions import LLMContractViolation
from app.llm.guardrails import (
    GuardrailScanResult,
    log_llm_guardrail_scan,
    redact_obvious_pii_patterns,
    scan_input_for_pii_and_injection,
    validate_llm_json_output,
)
from app.llm_models import LLMResponse, LLMTaskType
from app.services.llm_router import LLMRouter
from app.services.readiness_explain_structured import extract_json_object

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def _prepare_prompt_after_scan(prompt: str, scan: GuardrailScanResult) -> str:
    if scan.risk_level == "high":
        # TODO: HITL queue, hard block, or tenant policy toggle for production.
        return redact_obvious_pii_patterns(prompt)
    return prompt


def _structured_llm_sync(
    prompt: str,
    schema: type[T],
    session: Session | None,
    tenant_id: str,
    task_type: LLMTaskType,
    *,
    response_format: str | None = "json_object",
) -> T:
    router = LLMRouter(session=session)
    kwargs: dict[str, str] = {}
    if response_format is not None:
        kwargs["response_format"] = response_format
    resp = router.route_and_call(task_type, prompt, tenant_id, **kwargs)
    raw = resp.text or ""
    data = extract_json_object(raw)
    if data is None:
        raise LLMContractViolation("LLM output did not contain a parseable JSON object")
    return validate_llm_json_output(data, schema)


async def safe_llm_call(
    prompt: str,
    schema: type[T],
    *,
    context: LlmCallContext,
    session: Session | None,
    task_type: LLMTaskType,
    response_format: str | None = "json_object",
) -> T:
    """
    Scan prompt, log with context, optional PII redaction on high risk, LLM call, JSON validate.

    Underlying router is sync; runs in a thread pool.
    """
    scan = scan_input_for_pii_and_injection(prompt)
    log_llm_guardrail_scan(context, scan)
    effective = _prepare_prompt_after_scan(prompt, scan)
    return await asyncio.to_thread(
        _structured_llm_sync,
        effective,
        schema,
        session,
        context.tenant_id,
        task_type,
        response_format=response_format,
    )


def safe_llm_call_sync(
    prompt: str,
    schema: type[T],
    *,
    context: LlmCallContext,
    session: Session | None,
    task_type: LLMTaskType,
    response_format: str | None = "json_object",
) -> T:
    """Synchronous variant for LangGraph sync nodes and legacy call sites."""
    scan = scan_input_for_pii_and_injection(prompt)
    log_llm_guardrail_scan(context, scan)
    effective = _prepare_prompt_after_scan(prompt, scan)
    return _structured_llm_sync(
        effective,
        schema,
        session,
        context.tenant_id,
        task_type,
        response_format=response_format,
    )


def guardrailed_route_and_call_sync(
    session: Session | None,
    task_type: LLMTaskType,
    prompt: str,
    tenant_id: str,
    *,
    context: LlmCallContext,
    response_format: str | None = "json_object",
) -> LLMResponse:
    """
    For flows whose output is not a single Pydantic JSON contract (e.g. readiness explain).

    Applies the same input scan, logging, and high-risk redaction before calling the router.
    """
    scan = scan_input_for_pii_and_injection(prompt)
    log_llm_guardrail_scan(context, scan)
    effective = _prepare_prompt_after_scan(prompt, scan)
    router = LLMRouter(session=session)
    kwargs: dict[str, str] = {}
    if response_format is not None:
        kwargs["response_format"] = response_format
    return router.route_and_call(task_type, effective, tenant_id, **kwargs)


def safe_llm_json_call(
    session: Session | None,
    tenant_id: str,
    task_type: LLMTaskType,
    prompt: str,
    schema: type[T],
    *,
    context: str,
    response_format: str | None = "json_object",
) -> T:
    """
    Back-compat shim: ``context`` was a short string label; mapped to ``action_name``.
    Prefer ``safe_llm_call_sync(..., context=LlmCallContext(...))`` in new code.
    """
    ctx = LlmCallContext(tenant_id=tenant_id, action_name=context)
    return safe_llm_call_sync(
        prompt,
        schema,
        context=ctx,
        session=session,
        task_type=task_type,
        response_format=response_format,
    )

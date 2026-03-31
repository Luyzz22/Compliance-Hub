"""Guardrailed LLM invocation (async + sync) over the existing LLMRouter."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import TYPE_CHECKING, TypeVar

from pydantic import BaseModel

from app.evidence.llm_audit import (
    log_llm_contract_violation_audit,
    log_llm_guardrail_block_audit,
)
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
from app.services import llm_client
from app.services.llm_router import LLMRouter
from app.services.readiness_explain_structured import extract_json_object
from app.telemetry.tracing import start_span

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def _prompt_sha256_prefix(prompt: str, n: int = 16) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:n]


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
    with start_span(
        "llm.guardrailed_call",
        llm_tenant_id=context.tenant_id,
        llm_user_role=context.user_role,
        llm_action_name=context.action_name,
        llm_task_type=task_type.value,
        llm_contract_schema=schema.__name__,
        llm_prompt_length_chars=len(prompt),
        llm_prompt_sha256_prefix=_prompt_sha256_prefix(prompt),
    ) as span:
        try:
            scan = scan_input_for_pii_and_injection(prompt)
            log_llm_guardrail_scan(context, scan)
            effective = _prepare_prompt_after_scan(prompt, scan)
            out = await asyncio.to_thread(
                _structured_llm_sync,
                effective,
                schema,
                session,
                context.tenant_id,
                task_type,
                response_format=response_format,
            )
            if span.is_recording():
                span.set_attribute("llm_result", "ok")
                span.set_attribute("llm_response_json_length", len(out.model_dump_json()))
            return out
        except LLMContractViolation:
            if span.is_recording():
                span.set_attribute("llm_result", "contract_violation")
            log_llm_contract_violation_audit(
                session,
                tenant_id=context.tenant_id,
                action_name=context.action_name,
                task_type=task_type.value,
                contract_schema=schema.__name__,
            )
            raise
        except PermissionError:
            if span.is_recording():
                span.set_attribute("llm_result", "guardrail_blocked")
            log_llm_guardrail_block_audit(
                session,
                tenant_id=context.tenant_id,
                action_name=context.action_name,
                error_class="PermissionError",
                task_type=task_type.value,
            )
            raise
        except llm_client.LLMConfigurationError:
            if span.is_recording():
                span.set_attribute("llm_result", "configuration_error")
            log_llm_guardrail_block_audit(
                session,
                tenant_id=context.tenant_id,
                action_name=context.action_name,
                error_class="LLMConfigurationError",
                task_type=task_type.value,
            )
            raise
        except llm_client.LLMProviderHTTPError:
            if span.is_recording():
                span.set_attribute("llm_result", "provider_error")
            log_llm_guardrail_block_audit(
                session,
                tenant_id=context.tenant_id,
                action_name=context.action_name,
                error_class="LLMProviderHTTPError",
                task_type=task_type.value,
            )
            raise


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
    with start_span(
        "llm.guardrailed_call",
        llm_tenant_id=context.tenant_id,
        llm_user_role=context.user_role,
        llm_action_name=context.action_name,
        llm_task_type=task_type.value,
        llm_contract_schema=schema.__name__,
        llm_prompt_length_chars=len(prompt),
        llm_prompt_sha256_prefix=_prompt_sha256_prefix(prompt),
    ) as span:
        try:
            scan = scan_input_for_pii_and_injection(prompt)
            log_llm_guardrail_scan(context, scan)
            effective = _prepare_prompt_after_scan(prompt, scan)
            out = _structured_llm_sync(
                effective,
                schema,
                session,
                context.tenant_id,
                task_type,
                response_format=response_format,
            )
            if span.is_recording():
                span.set_attribute("llm_result", "ok")
                span.set_attribute("llm_response_json_length", len(out.model_dump_json()))
            return out
        except LLMContractViolation:
            if span.is_recording():
                span.set_attribute("llm_result", "contract_violation")
            log_llm_contract_violation_audit(
                session,
                tenant_id=context.tenant_id,
                action_name=context.action_name,
                task_type=task_type.value,
                contract_schema=schema.__name__,
            )
            raise
        except PermissionError:
            if span.is_recording():
                span.set_attribute("llm_result", "guardrail_blocked")
            log_llm_guardrail_block_audit(
                session,
                tenant_id=context.tenant_id,
                action_name=context.action_name,
                error_class="PermissionError",
                task_type=task_type.value,
            )
            raise
        except llm_client.LLMConfigurationError:
            if span.is_recording():
                span.set_attribute("llm_result", "configuration_error")
            log_llm_guardrail_block_audit(
                session,
                tenant_id=context.tenant_id,
                action_name=context.action_name,
                error_class="LLMConfigurationError",
                task_type=task_type.value,
            )
            raise
        except llm_client.LLMProviderHTTPError:
            if span.is_recording():
                span.set_attribute("llm_result", "provider_error")
            log_llm_guardrail_block_audit(
                session,
                tenant_id=context.tenant_id,
                action_name=context.action_name,
                error_class="LLMProviderHTTPError",
                task_type=task_type.value,
            )
            raise


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
    with start_span(
        "llm.guardrailed_call",
        llm_tenant_id=context.tenant_id,
        llm_user_role=context.user_role,
        llm_action_name=context.action_name,
        llm_task_type=task_type.value,
        llm_contract_schema="freeform_markdown",
        llm_prompt_length_chars=len(prompt),
        llm_prompt_sha256_prefix=_prompt_sha256_prefix(prompt),
    ) as span:
        try:
            scan = scan_input_for_pii_and_injection(prompt)
            log_llm_guardrail_scan(context, scan)
            effective = _prepare_prompt_after_scan(prompt, scan)
            router = LLMRouter(session=session)
            kwargs: dict[str, str] = {}
            if response_format is not None:
                kwargs["response_format"] = response_format
            resp = router.route_and_call(task_type, effective, tenant_id, **kwargs)
            if span.is_recording():
                span.set_attribute("llm_result", "ok")
            return resp
        except LLMContractViolation:
            if span.is_recording():
                span.set_attribute("llm_result", "contract_violation")
            log_llm_contract_violation_audit(
                session,
                tenant_id=tenant_id,
                action_name=context.action_name,
                task_type=task_type.value,
                contract_schema="freeform_markdown",
            )
            raise
        except PermissionError:
            if span.is_recording():
                span.set_attribute("llm_result", "guardrail_blocked")
            log_llm_guardrail_block_audit(
                session,
                tenant_id=tenant_id,
                action_name=context.action_name,
                error_class="PermissionError",
                task_type=task_type.value,
            )
            raise
        except llm_client.LLMConfigurationError:
            if span.is_recording():
                span.set_attribute("llm_result", "configuration_error")
            log_llm_guardrail_block_audit(
                session,
                tenant_id=tenant_id,
                action_name=context.action_name,
                error_class="LLMConfigurationError",
                task_type=task_type.value,
            )
            raise
        except llm_client.LLMProviderHTTPError:
            if span.is_recording():
                span.set_attribute("llm_result", "provider_error")
            log_llm_guardrail_block_audit(
                session,
                tenant_id=tenant_id,
                action_name=context.action_name,
                error_class="LLMProviderHTTPError",
                task_type=task_type.value,
            )
            raise


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

"""GA-ready advisor service layer.

Wraps the core AdvisorComplianceAgent with:
- SLA-aware timeout enforcement
- Standardised error handling
- Channel abstraction
- Idempotency via request_id
- Structured output (tags, next_steps, ref_ids)
- Metrics instrumentation (latency, errors, channels)

This module is the single entry point for all advisor invocations,
regardless of channel.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from typing import Any

from app.advisor.channels import DEFAULT_CHANNEL, AdvisorChannel, ChannelMetadata
from app.advisor.errors import (
    ADVISOR_SLA_TIMEOUT_SECONDS,
    AdvisorErrorCategory,
    build_advisor_error,
)
from app.advisor.formatting import (
    derive_next_steps,
    derive_tags,
    format_answer_for_channel,
)
from app.advisor.idempotency import get_cached_response, store_response
from app.advisor.response_models import (
    AdvisorResponseMeta,
    AdvisorStructuredResponse,
)
from app.services.agents.advisor_compliance_agent import (
    AdvisorComplianceAgent,
    AdvisorState,
)
from app.services.rag.logging import log_advisor_agent_event

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="advisor")


class AdvisorRequest:
    """Encapsulates all input for an advisor invocation."""

    __slots__ = (
        "query",
        "tenant_id",
        "channel",
        "channel_metadata",
        "request_id",
        "trace_id",
        "flow_type",
        "extra_tags",
        "client_id",
        "system_id",
    )

    def __init__(
        self,
        query: str,
        tenant_id: str = "",
        channel: AdvisorChannel = DEFAULT_CHANNEL,
        channel_metadata: ChannelMetadata | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
        flow_type: str | None = None,
        extra_tags: list[str] | None = None,
        client_id: str = "",
        system_id: str = "",
    ) -> None:
        self.query = query
        self.tenant_id = tenant_id
        self.channel = channel
        self.channel_metadata = channel_metadata
        self.request_id = request_id
        self.trace_id = trace_id
        self.flow_type = flow_type
        self.extra_tags = extra_tags
        self.client_id = client_id
        self.system_id = system_id


def run_advisor(
    request: AdvisorRequest,
    agent: AdvisorComplianceAgent,
    *,
    timeout_seconds: float = ADVISOR_SLA_TIMEOUT_SECONDS,
) -> AdvisorStructuredResponse:
    """Execute an advisor query with full GA wrapping.

    Returns a structured response in all cases (success, error, timeout).
    """
    start = time.monotonic()

    cached = get_cached_response(request.request_id)
    if cached is not None and isinstance(cached, AdvisorStructuredResponse):
        cached.meta.is_cached = True
        _log_invocation(request, cached, time.monotonic() - start, is_duplicate=True)
        return cached

    try:
        future = _executor.submit(_run_agent, agent, request)
        state: AdvisorState = future.result(timeout=timeout_seconds)
        elapsed = (time.monotonic() - start) * 1000

        response = _build_response(request, state, elapsed)

    except FuturesTimeout:
        elapsed = (time.monotonic() - start) * 1000
        response = _build_error_response(
            request,
            AdvisorErrorCategory.timeout,
            elapsed,
            retry_allowed=True,
        )

    except Exception:
        elapsed = (time.monotonic() - start) * 1000
        logger.exception(
            "advisor_agent_unhandled_error",
            extra={"tenant_id": request.tenant_id, "trace_id": request.trace_id},
        )
        response = _build_error_response(
            request,
            AdvisorErrorCategory.agent_failure,
            elapsed,
            retry_allowed=True,
        )

    store_response(request.request_id, response)
    _log_invocation(request, response, (time.monotonic() - start))
    return response


def _run_agent(agent: AdvisorComplianceAgent, request: AdvisorRequest) -> AdvisorState:
    return agent.run(
        query=request.query,
        tenant_id=request.tenant_id,
        trace_id=request.trace_id,
    )


def _build_response(
    request: AdvisorRequest,
    state: AdvisorState,
    elapsed_ms: float,
) -> AdvisorStructuredResponse:
    tags = derive_tags(request.query, state.answer)
    if request.extra_tags:
        tags = sorted(set(tags) | set(request.extra_tags))
    next_steps = derive_next_steps(state.is_escalated, state.confidence_level, tags)
    answer = format_answer_for_channel(
        state.answer,
        request.channel,
        tags=tags,
        next_steps=next_steps,
    )

    ref_ids: dict[str, str] = {}
    if request.flow_type:
        ref_ids["flow_type"] = request.flow_type
    if request.channel_metadata:
        if request.channel_metadata.sap_document_id:
            ref_ids["sap_document_id"] = request.channel_metadata.sap_document_id
        if request.channel_metadata.datev_client_number:
            ref_ids["datev_client_number"] = request.channel_metadata.datev_client_number
        if request.channel_metadata.partner_reference:
            ref_ids["partner_reference"] = request.channel_metadata.partner_reference

    return AdvisorStructuredResponse(
        answer=answer,
        is_escalated=state.is_escalated,
        escalation_reason=state.escalation_reason,
        confidence_level=state.confidence_level,
        intent=str(state.intent),
        tags=tags,
        suggested_next_steps=next_steps,
        ref_ids=ref_ids,
        needs_manual_followup=state.is_escalated,
        meta=AdvisorResponseMeta(
            channel=request.channel,
            channel_metadata=request.channel_metadata,
            request_id=request.request_id,
            trace_id=request.trace_id,
            latency_ms=round(elapsed_ms, 1),
            flow_type=request.flow_type,
        ),
        agent_trace=state.agent_trace,
    )


def _build_error_response(
    request: AdvisorRequest,
    category: AdvisorErrorCategory,
    elapsed_ms: float,
    *,
    retry_allowed: bool = False,
) -> AdvisorStructuredResponse:
    err = build_advisor_error(
        category,
        trace_id=request.trace_id,
        needs_manual_followup=True,
        retry_allowed=retry_allowed,
    )
    return AdvisorStructuredResponse(
        answer=err.message_de,
        needs_manual_followup=True,
        error=err,
        meta=AdvisorResponseMeta(
            channel=request.channel,
            channel_metadata=request.channel_metadata,
            request_id=request.request_id,
            trace_id=request.trace_id,
            latency_ms=round(elapsed_ms, 1),
        ),
    )


def _log_invocation(
    request: AdvisorRequest,
    response: AdvisorStructuredResponse,
    elapsed_seconds: float,
    *,
    is_duplicate: bool = False,
) -> None:
    """Log the advisor invocation for metrics aggregation."""
    extra: dict[str, Any] = {
        "channel": request.channel.value,
        "latency_ms": round(elapsed_seconds * 1000, 1),
        "is_duplicate": is_duplicate,
    }
    if request.flow_type:
        extra["flow_type"] = request.flow_type
    if request.client_id:
        extra["client_id"] = request.client_id
    if request.system_id:
        extra["system_id"] = request.system_id
    if response.error:
        extra["error_category"] = response.error.category.value

    decision = (
        "error"
        if response.error
        else ("escalate_to_human" if response.is_escalated else "answered")
    )
    if is_duplicate:
        decision = "duplicate"

    log_advisor_agent_event(
        tenant_id=request.tenant_id,
        decision=decision,
        intent=response.intent or None,
        trace_id=request.trace_id,
        extra=extra,
    )

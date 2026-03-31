"""Guardrailed LLM call wrappers for ComplianceHub.

All LLM interactions go through safe_llm_call / safe_llm_call_sync
to enforce:
- Tenant context tracking (LlmCallContext)
- Structured error handling / fallback
- Audit logging of every call
- Token budget limits

Actual LLM provider calls are abstracted behind a callable;
in production this delegates to the configured model (Claude/GPT-4o/Gemini).
In tests, a mock callable is injected.
"""

from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

logger = logging.getLogger("compliancehub.llm")


@dataclass
class LlmCallContext:
    """Metadata attached to every LLM invocation for audit/evidence."""

    tenant_id: str
    role: str
    action: str
    trace_id: str = ""
    model_id: str = ""
    max_tokens: int = 2048
    temperature: float = 0.1
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LlmResponse:
    text: str
    model_id: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    error: str | None = None


class LlmCallable(Protocol):
    def __call__(self, prompt: str, context: LlmCallContext) -> LlmResponse: ...


_FALLBACK_RESPONSE = (
    "Die Anfrage konnte nicht automatisch beantwortet werden. "
    "Bitte wenden Sie sich an Ihren Compliance-Berater."
)


def safe_llm_call_sync(
    prompt: str,
    context: LlmCallContext,
    llm_fn: LlmCallable | None = None,
) -> LlmResponse:
    """Synchronous guardrailed LLM call.

    If llm_fn is None or raises, returns a safe fallback response
    and logs the failure for evidence.
    """
    start = time.monotonic()
    try:
        if llm_fn is None:
            raise RuntimeError("No LLM callable configured")

        response = llm_fn(prompt, context)
        response.latency_ms = (time.monotonic() - start) * 1000

        logger.info(
            "llm_call_success",
            extra={
                "llm_context": asdict(context),
                "model_id": response.model_id,
                "latency_ms": response.latency_ms,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
            },
        )
        return response

    except Exception:
        latency = (time.monotonic() - start) * 1000
        logger.exception(
            "llm_call_failed",
            extra={
                "llm_context": asdict(context),
                "latency_ms": latency,
            },
        )
        return LlmResponse(
            text=_FALLBACK_RESPONSE,
            latency_ms=latency,
            error="LLM call failed – safe fallback returned",
        )

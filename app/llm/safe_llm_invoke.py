"""Guardrailed LLM invocation for structured JSON contracts."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, TypeVar

from pydantic import BaseModel

from app.llm.guardrails import (
    LLMContractViolation,
    log_input_guardrail_scan,
    scan_input_for_pii_and_injection,
    validate_llm_json_output,
)
from app.llm_models import LLMTaskType
from app.services.llm_router import LLMRouter
from app.services.readiness_explain_structured import extract_json_object

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


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
    Scan prompt, call router, parse JSON, validate against `schema`.

    On missing/invalid JSON after extraction, raises LLMContractViolation.
    """
    scan = scan_input_for_pii_and_injection(prompt)
    log_input_guardrail_scan(context=context, tenant_id=tenant_id, scan=scan)

    router = LLMRouter(session=session)
    resp = router.route_and_call(
        task_type,
        prompt,
        tenant_id,
        response_format=response_format,
    )
    raw = resp.text or ""
    data = extract_json_object(raw)
    if data is None:
        raise LLMContractViolation("LLM output did not contain a parseable JSON object")
    return validate_llm_json_output(data, schema)


# Backwards-friendly alias (spec / docs)
safe_llm_call = safe_llm_json_call

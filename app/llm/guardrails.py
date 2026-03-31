"""Input scanning and structured-output validation for LLM calls."""

from __future__ import annotations

import logging
import re
from typing import Any, Literal, TypeVar

from pydantic import BaseModel, ValidationError

from app.llm.context import LlmCallContext
from app.llm.exceptions import LLMContractViolation

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

GuardrailRiskLevel = Literal["low", "medium", "high"]


class GuardrailScanResult(BaseModel):
    """Heuristic scan of a prompt prior to LLM invocation (v1: log-only, no hard block)."""

    has_pii: bool = False
    has_injection_markers: bool = False
    risk_level: GuardrailRiskLevel = "low"
    flags: list[str] = []


_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
)
_PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}\b",
)
_IBAN_LIKE_RE = re.compile(
    r"\b[A-Z]{2}\d{2}[A-Z0-9]{1,30}\b",
    re.IGNORECASE,
)

_INJECTION_MARKERS = (
    "ignore previous instructions",
    "ignore all previous",
    "disregard the above",
    "system:",
    "assistant:",
    "you are now",
    "new instructions:",
    "override",
    "jailbreak",
)


def scan_input_for_pii_and_injection(text: str) -> GuardrailScanResult:
    """
    Regex heuristics for obvious PII and prompt-injection markers.

    risk_level:
    - high: PII and injection markers
    - medium: PII only, or injection markers only (stronger logging without PII)
    - low: neither
    """
    if not text or not str(text).strip():
        return GuardrailScanResult()

    t = str(text)
    lowered = t.lower()
    flags: list[str] = []

    has_pii = False
    if _EMAIL_RE.search(t):
        flags.append("possible_email")
        has_pii = True
    if _IBAN_LIKE_RE.search(t):
        flags.append("possible_iban")
        has_pii = True
    if _PHONE_RE.search(t) and len(re.sub(r"\D", "", t)) >= 10:
        flags.append("possible_phone")
        has_pii = True

    has_inj = False
    for marker in _INJECTION_MARKERS:
        if marker in lowered:
            flags.append("injection_marker")
            has_inj = True
            break

    if has_pii and has_inj:
        risk: GuardrailRiskLevel = "high"
    elif has_pii or has_inj:
        risk = "medium"
    else:
        risk = "low"

    return GuardrailScanResult(
        has_pii=has_pii,
        has_injection_markers=has_inj,
        risk_level=risk,
        flags=flags,
    )


def redact_obvious_pii_patterns(text: str) -> str:
    """Best-effort redaction for high-risk prompts; extend with DLP/HITL in production."""
    out = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    out = _IBAN_LIKE_RE.sub("[REDACTED_IBAN]", out)
    return out


def log_llm_guardrail_scan(ctx: LlmCallContext, scan: GuardrailScanResult) -> None:
    """Always log medium and high; low stays at debug to limit noise."""
    extra = {
        "tenant_id": ctx.tenant_id,
        "user_role": ctx.user_role or None,
        "action_name": ctx.action_name or None,
        "has_pii": scan.has_pii,
        "has_injection_markers": scan.has_injection_markers,
        "flags": scan.flags,
    }
    if scan.risk_level == "high":
        logger.warning("llm_guardrail_input_high_risk %s", extra)
    elif scan.risk_level == "medium":
        logger.info("llm_guardrail_input_medium_risk %s", extra)
    else:
        logger.debug("llm_guardrail_input_low_risk %s", extra)


def validate_llm_json_output(payload: Any, schema: type[T]) -> T:
    """
    Validate parsed JSON (dict) or JSON string against a Pydantic model.

    Raises LLMContractViolation on failure.
    """
    try:
        if isinstance(payload, schema):
            return payload
        if isinstance(payload, dict):
            return schema.model_validate(payload)
        if isinstance(payload, str):
            return schema.model_validate_json(payload)
        return schema.model_validate(payload)
    except ValidationError as exc:
        raise LLMContractViolation(str(exc)) from exc

"""Input scanning and structured-output validation for LLM calls."""

from __future__ import annotations

import logging
import re
from typing import Any, Literal, TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

GuardrailRiskLevel = Literal["low", "medium", "high"]


class GuardrailScanResult(BaseModel):
    risk_level: GuardrailRiskLevel
    """Heuristic aggregate risk for logging and future hard blocks."""

    flags: list[str] = []
    matched_patterns: list[str] = []


class LLMContractViolation(Exception):
    """Raised when LLM output does not validate against the expected Pydantic contract."""


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
    Lightweight regex heuristics for obvious PII and prompt-injection markers.

    v1: never blocks by itself; callers log and may tighten policy later.
    """
    if not text or not str(text).strip():
        return GuardrailScanResult(risk_level="low")

    t = str(text)
    lowered = t.lower()
    flags: list[str] = []
    matched: list[str] = []

    if _EMAIL_RE.search(t):
        flags.append("possible_email")
        matched.append("email")
    if _IBAN_LIKE_RE.search(t):
        flags.append("possible_iban")
        matched.append("iban_like")
    if _PHONE_RE.search(t) and len(re.sub(r"\D", "", t)) >= 10:
        flags.append("possible_phone")
        matched.append("phone_like")

    for marker in _INJECTION_MARKERS:
        if marker in lowered:
            flags.append("injection_marker")
            matched.append(marker)
            break

    risk: GuardrailRiskLevel = "low"
    if flags:
        risk = "medium"
    if "injection_marker" in flags and ("possible_email" in flags or "possible_iban" in flags):
        risk = "high"
    elif "injection_marker" in flags:
        risk = "high"

    return GuardrailScanResult(risk_level=risk, flags=flags, matched_patterns=matched)


def log_input_guardrail_scan(
    *,
    context: str,
    tenant_id: str,
    scan: GuardrailScanResult,
) -> None:
    if scan.risk_level == "high":
        logger.warning(
            "llm_guardrail_input_high_risk context=%s tenant=%s flags=%s",
            context,
            tenant_id,
            scan.flags,
        )
    elif scan.risk_level == "medium":
        logger.info(
            "llm_guardrail_input_medium_risk context=%s tenant=%s flags=%s",
            context,
            tenant_id,
            scan.flags,
        )


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

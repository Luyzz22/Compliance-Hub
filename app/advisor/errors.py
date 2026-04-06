"""Standardised advisor error model for GA-ready error handling.

All advisor errors share a common shape so that consumers (web, SAP, DATEV)
can handle them uniformly.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class AdvisorErrorCategory(StrEnum):
    rag_failure = "rag_failure"
    llm_failure = "llm_failure"
    agent_failure = "agent_failure"
    policy_refusal = "policy_refusal"
    timeout = "timeout"
    internal = "internal"


class AdvisorError(BaseModel):
    """Structured error returned to clients on advisor failures."""

    error: bool = True
    category: AdvisorErrorCategory
    message_de: str
    message_en: str
    needs_manual_followup: bool = True
    trace_id: str | None = None
    retry_allowed: bool = False


ADVISOR_SLA_TIMEOUT_SECONDS = 30.0

_ERROR_MESSAGES: dict[AdvisorErrorCategory, tuple[str, str]] = {
    AdvisorErrorCategory.rag_failure: (
        "Die Quellensuche konnte nicht abgeschlossen werden. "
        "Bitte versuchen Sie es erneut oder wenden Sie sich an den Support.",
        "Source retrieval failed. Please retry or contact support.",
    ),
    AdvisorErrorCategory.llm_failure: (
        "Die automatische Antwortgenerierung ist derzeit nicht verfügbar. "
        "Ihre Anfrage wurde zur manuellen Bearbeitung markiert.",
        "Answer generation is currently unavailable. "
        "Your request has been flagged for manual processing.",
    ),
    AdvisorErrorCategory.agent_failure: (
        "Ein interner Verarbeitungsfehler ist aufgetreten. Bitte versuchen Sie es erneut.",
        "An internal processing error occurred. Please retry.",
    ),
    AdvisorErrorCategory.timeout: (
        "Die Verarbeitung hat das Zeitlimit überschritten. "
        "Bitte versuchen Sie es erneut oder vereinfachen Sie Ihre Anfrage.",
        "Processing exceeded the time limit. Please retry or simplify your query.",
    ),
    AdvisorErrorCategory.internal: (
        "Ein unerwarteter Fehler ist aufgetreten. Bitte kontaktieren Sie den Support.",
        "An unexpected error occurred. Please contact support.",
    ),
    AdvisorErrorCategory.policy_refusal: (
        "Die Anfrage wurde aufgrund einer Richtlinie abgelehnt.",
        "The request was declined based on a policy rule.",
    ),
}


def build_advisor_error(
    category: AdvisorErrorCategory,
    *,
    trace_id: str | None = None,
    needs_manual_followup: bool = True,
    retry_allowed: bool = False,
) -> AdvisorError:
    msg_de, msg_en = _ERROR_MESSAGES.get(
        category,
        _ERROR_MESSAGES[AdvisorErrorCategory.internal],
    )
    return AdvisorError(
        category=category,
        message_de=msg_de,
        message_en=msg_en,
        trace_id=trace_id,
        needs_manual_followup=needs_manual_followup,
        retry_allowed=retry_allowed,
    )

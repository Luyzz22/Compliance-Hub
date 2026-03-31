"""Zentrale deutsche Antwort-Templates für den Advisor-Agenten.

Alle Vorlagen hier pflegen, damit Legal/Compliance sie leicht prüfen kann.
Keine PII, keine dynamischen User-Daten in den Templates selbst.
"""

from __future__ import annotations

DISCLAIMER_KEINE_RECHTSBERATUNG = (
    "Hinweis: Diese Antwort stellt keine Rechtsberatung dar. "
    "Für verbindliche Einschätzungen wenden Sie sich bitte an Ihre Rechtsabteilung."
)

ANSWER_NORMAL = f"{{answer}}\n\n---\n_{DISCLAIMER_KEINE_RECHTSBERATUNG}_"

ESCALATION_HUMAN_REVIEW = (
    "Menschliche Prüfung empfohlen.\n\n"
    "Grund: {reason}\n\n"
    "Ihre Anfrage wurde zur Überprüfung durch einen Compliance-Berater markiert. "
    "Bitte warten Sie auf eine qualifizierte Rückmeldung."
)

REFUSAL_PROHIBITED_TOPIC = (
    "Diese Anfrage betrifft ein Thema, das außerhalb des automatisierten "
    "Beratungsbereichs liegt (z.\u202fB. biometrische Kategorisierung, "
    "Emotionserkennung, Arbeitnehmerüberwachung).\n\n"
    "Bitte wenden Sie sich für Fragen zu diesem Bereich direkt an "
    "Ihren Compliance-Beauftragten oder Ihre Rechtsabteilung."
)

REFUSAL_OUT_OF_SCOPE = (
    "Ihre Anfrage liegt außerhalb des Compliance-Beratungsbereichs. "
    "Der Advisor unterstützt ausschließlich Fragen zu regulatorischer "
    "Compliance (EU AI Act, NIS2, ISO 42001, DSGVO).\n\n"
    "Für andere Themen nutzen Sie bitte die entsprechenden Fachbereiche."
)

REFUSAL_SENSITIVE_LOW_CONFIDENCE = (
    "Ihre Anfrage berührt ein sensibles regulatorisches Thema. "
    "Die automatische Quellenübereinstimmung ist für eine sichere Antwort "
    "nicht ausreichend.\n\n"
    "Grund: {reason}\n\n"
    "Bitte wenden Sie sich an Ihren Compliance-Beauftragten für eine "
    "qualifizierte Einschätzung."
)


DISCLAIMER_SHORT = "Keine Rechtsberatung. Rücksprache mit Fachberater empfohlen."

ANSWER_COMPACT = "{answer}\n\n_{disclaimer}_"


def format_normal_answer(answer: str, *, compact: bool = False) -> str:
    if compact:
        return ANSWER_COMPACT.format(answer=answer, disclaimer=DISCLAIMER_SHORT)
    return ANSWER_NORMAL.format(answer=answer)


def format_escalation(reason: str) -> str:
    return ESCALATION_HUMAN_REVIEW.format(reason=reason)


def format_sensitive_refusal(reason: str) -> str:
    return REFUSAL_SENSITIVE_LOW_CONFIDENCE.format(reason=reason)

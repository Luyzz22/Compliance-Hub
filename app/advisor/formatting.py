"""Channel-aware formatting layer for advisor responses.

Keeps channel-specific logic out of the core agent. Each channel can
adjust answer length, disclaimer inclusion, and structured field emphasis.
"""

from __future__ import annotations

import re

from app.advisor.channels import AdvisorChannel, include_disclaimer, max_answer_length
from app.advisor.templates import DISCLAIMER_KEINE_RECHTSBERATUNG


def format_answer_for_channel(
    answer: str,
    channel: AdvisorChannel,
) -> str:
    limit = max_answer_length(channel)
    if not include_disclaimer(channel):
        answer = _strip_disclaimer(answer)
    if limit and len(answer) > limit:
        answer = answer[: limit - 3] + "..."
    return answer


def _strip_disclaimer(text: str) -> str:
    text = text.replace(f"\n\n---\n_{DISCLAIMER_KEINE_RECHTSBERATUNG}_", "")
    text = text.replace(DISCLAIMER_KEINE_RECHTSBERATUNG, "")
    return text.rstrip()


_TAG_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"ai\s*act|ki.verordnung", re.IGNORECASE), "eu_ai_act"),
    (re.compile(r"nis\s*2", re.IGNORECASE), "nis2"),
    (re.compile(r"iso\s*42001", re.IGNORECASE), "iso_42001"),
    (re.compile(r"dsgvo|gdpr|datenschutz", re.IGNORECASE), "gdpr"),
    (re.compile(r"hochrisiko|high.risk", re.IGNORECASE), "high_risk"),
    (re.compile(r"art(ikel|\.)\s*\d+", re.IGNORECASE), "article_reference"),
    (re.compile(r"meldepflicht|meldung|incident", re.IGNORECASE), "incident_reporting"),
    (re.compile(r"risikomanagement|risk.management", re.IGNORECASE), "risk_management"),
    (re.compile(r"konformit|compliance|conformity", re.IGNORECASE), "conformity_assessment"),
]


def derive_tags(query: str, answer: str) -> list[str]:
    """Derive topic tags from query + answer text for structured output."""
    combined = f"{query} {answer}"
    tags: list[str] = []
    for pat, tag in _TAG_PATTERNS:
        if pat.search(combined):
            tags.append(tag)
    return sorted(set(tags))


def derive_next_steps(
    is_escalated: bool,
    confidence_level: str,
    tags: list[str],
) -> list[str]:
    """Suggest actionable next steps based on the advisor result."""
    steps: list[str] = []
    if is_escalated:
        steps.append("Compliance-Berater kontaktieren")
        steps.append("Anfrage mit zusätzlichem Kontext erneut stellen")
        return steps

    if confidence_level == "medium":
        steps.append("Ergebnis durch Fachexperten prüfen lassen")

    if "eu_ai_act" in tags:
        steps.append("EU AI Act Konformitätsbewertung prüfen")
    if "nis2" in tags:
        steps.append("NIS2-Meldepflichten überprüfen")
    if "high_risk" in tags:
        steps.append("Hochrisiko-Klassifizierung dokumentieren")
    if "risk_management" in tags:
        steps.append("Risikomanagementsystem aktualisieren")

    if not steps:
        steps.append("Ergebnis in Compliance-Dokumentation übernehmen")

    return steps

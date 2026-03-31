"""Regelbasierte Abstimmung: Governance-Maturity-Brief ↔ Incident-Drilldown (Laufzeit)."""

from __future__ import annotations

from app.advisor_governance_maturity_brief_models import AdvisorGovernanceMaturityBrief
from app.incident_drilldown_models import TenantIncidentDrilldownOut
from app.services.incident_drilldown_signal_utils import (
    drilldown_mandate_pattern,
    top_ai_system_names_for_brief,
)

# Hochlevel-Fokus (keine Systemnamen)
FOCUS_SAFETY_DRILLDOWN_DE = (
    "Sicherheitsrelevante Incidents und Post-Market-Monitoring (OAMI, Eskalation, Nachweise)."
)
FOCUS_AVAILABILITY_DRILLDOWN_DE = (
    "Betriebsstabilität und Verfügbarkeit der KI-Systeme (Recovery, SLAs, Betriebsführung)."
)
FOCUS_MONITORING_COVERAGE_DE = (
    "Monitoring-Abdeckung und Datenaktualität der Laufzeit-Signale verbessern."
)


def _focus_line_for_pattern(pattern: str) -> str:
    if pattern == "safety":
        return FOCUS_SAFETY_DRILLDOWN_DE
    if pattern == "availability":
        return FOCUS_AVAILABILITY_DRILLDOWN_DE
    return FOCUS_MONITORING_COVERAGE_DE


def _focus_effectively_present(areas: list[str], candidate: str) -> bool:
    c = candidate.casefold()
    needles: list[str]
    if "sicherheitsrelevant" in c or "post-market" in c:
        needles = ["sicherheitsrelevant", "post-market", "post market", "laufzeitvor"]
    elif "verfügbarkeit" in c or "betriebsstabilität" in c:
        needles = ["verfügbarkeit", "betriebsstabilität", "recovery"]
    else:
        needles = ["monitoring-abdeckung", "laufzeit-signale", "datenaktualität"]
    return any(any(n in a.casefold() for n in needles) for a in areas)


def _client_system_bridge(pattern: str, names: list[str]) -> str | None:
    if pattern == "benign_low" or not names:
        return None
    label = "Safety-Signalen" if pattern == "safety" else "Verfügbarkeits-Signalen"
    if len(names) >= 2:
        return (
            f"Im Fokus stehen aktuell vor allem die Systeme „{names[0]}“ und „{names[1]}“ "
            f"({label})."
        )
    return f"Im Fokus steht aktuell vor allem das System „{names[0]}“ ({label})."


def apply_drilldown_alignment_to_brief(
    brief: AdvisorGovernanceMaturityBrief,
    drilldown: TenantIncidentDrilldownOut | None,
) -> AdvisorGovernanceMaturityBrief:
    """Ergänzt Fokusliste und optional Mandantenabsatz aus Laufzeit-Drilldown.

    Systemnamen höchstens kurz im Absatz; Fokuszeilen bleiben strategisch.
    """
    if drilldown is None or not drilldown.items:
        return brief

    total_incidents = sum(x.incident_total_90d for x in drilldown.items)
    if total_incidents <= 0:
        return brief

    pattern = drilldown_mandate_pattern(drilldown.items)
    candidate = _focus_line_for_pattern(pattern)
    areas = list(brief.recommended_focus_areas)
    if pattern == "benign_low":
        areas = [a for a in areas if a != FOCUS_MONITORING_COVERAGE_DE]
        if not areas or areas[0] != FOCUS_MONITORING_COVERAGE_DE:
            areas = [FOCUS_MONITORING_COVERAGE_DE, *areas]
    elif not _focus_effectively_present(areas, candidate):
        areas = [candidate, *areas]

    names = top_ai_system_names_for_brief(drilldown.items, limit=2)
    bridge = _client_system_bridge(pattern, names)
    para = (brief.client_ready_paragraph_de or "").strip()
    if bridge:
        para = f"{para} {bridge}".strip() if para else bridge
        para = para[:600]

    return brief.model_copy(
        update={
            "recommended_focus_areas": areas,
            "client_ready_paragraph_de": para or None,
        },
    )

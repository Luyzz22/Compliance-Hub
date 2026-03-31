"""Dominanz, Ranking und Muster aus TenantIncidentDrilldown (Brief + Markdown)."""

from __future__ import annotations

from typing import Literal

from app.incident_drilldown_models import TenantIncidentDrilldownItem

OAMI_INCIDENT_DOMINANCE_THRESHOLD = 0.45
DRILLDOWN_LOW_TOTAL_THRESHOLD = 3

DrilldownMandatePattern = Literal["safety", "availability", "benign_low"]


def is_safety_driven_item(it: TenantIncidentDrilldownItem) -> bool:
    s = it.weighted_incident_share_safety
    a = it.weighted_incident_share_availability
    o = it.weighted_incident_share_other
    return s >= OAMI_INCIDENT_DOMINANCE_THRESHOLD and s > a and s > o


def is_availability_driven_item(it: TenantIncidentDrilldownItem) -> bool:
    s = it.weighted_incident_share_safety
    a = it.weighted_incident_share_availability
    o = it.weighted_incident_share_other
    return a >= OAMI_INCIDENT_DOMINANCE_THRESHOLD and a > s and a > o


def rank_drilldown_items_by_volume(
    items: list[TenantIncidentDrilldownItem],
) -> list[TenantIncidentDrilldownItem]:
    return sorted(
        items,
        key=lambda x: (-x.incident_total_90d, -x.weighted_incident_share_safety, x.ai_system_name),
    )


def drilldown_mandate_pattern(items: list[TenantIncidentDrilldownItem]) -> DrilldownMandatePattern:
    """Aggregiertes Lagebild für Brief-Fokus (nicht zeilenweise)."""
    total = sum(i.incident_total_90d for i in items)
    if total <= 0:
        return "benign_low"
    if total <= DRILLDOWN_LOW_TOTAL_THRESHOLD:
        return "benign_low"
    s_vol = sum(i.incident_total_90d for i in items if is_safety_driven_item(i))
    a_vol = sum(i.incident_total_90d for i in items if is_availability_driven_item(i))
    if s_vol == 0 and a_vol == 0:
        return "benign_low"
    if s_vol >= a_vol and s_vol > 0:
        return "safety"
    if a_vol > 0:
        return "availability"
    return "benign_low"


def top_ai_system_names_for_brief(
    items: list[TenantIncidentDrilldownItem],
    *,
    limit: int = 2,
) -> list[str]:
    """Bis zu ``limit`` Anzeigenamen, nach Incident-Volumen sortiert."""
    out: list[str] = []
    seen: set[str] = set()
    for it in rank_drilldown_items_by_volume(items):
        label = (it.ai_system_name or "").strip() or it.ai_system_id
        if label in seen:
            continue
        seen.add(label)
        out.append(label)
        if len(out) >= limit:
            break
    return out

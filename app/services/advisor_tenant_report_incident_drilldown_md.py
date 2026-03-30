"""Markdown-Abschnitt „System- und Lieferanten-Drilldown“ für den Advisor-Mandanten-Steckbrief."""

from __future__ import annotations

from typing import Literal

from app.incident_drilldown_models import TenantIncidentDrilldownItem, TenantIncidentDrilldownOut
from app.services.incident_drilldown_signal_utils import (
    DRILLDOWN_LOW_TOTAL_THRESHOLD,
    is_availability_driven_item,
    is_safety_driven_item,
    rank_drilldown_items_by_volume,
)

_MAX_BULLETS = 5

DominantKind = Literal["safety", "availability", "other"]


def _dominant_kind(it: TenantIncidentDrilldownItem) -> DominantKind:
    if is_safety_driven_item(it):
        return "safety"
    if is_availability_driven_item(it):
        return "availability"
    return "other"


def _select_for_report(
    items: list[TenantIncidentDrilldownItem],
) -> list[TenantIncidentDrilldownItem]:
    """Bis zu fünf Systeme; Safety- und Availability-Treiber, falls im Datenbestand vorhanden."""
    if not items:
        return []
    ranked = rank_drilldown_items_by_volume(items)
    seen: set[str] = set()
    out: list[TenantIncidentDrilldownItem] = []

    def add(it: TenantIncidentDrilldownItem) -> None:
        if it.ai_system_id in seen:
            return
        seen.add(it.ai_system_id)
        out.append(it)

    for it in ranked:
        if is_safety_driven_item(it):
            add(it)
            break
    for it in ranked:
        if is_availability_driven_item(it):
            add(it)
            break
    for it in ranked:
        if len(out) >= _MAX_BULLETS:
            break
        add(it)
    return sorted(
        out,
        key=lambda x: (-x.incident_total_90d, -x.weighted_incident_share_safety, x.ai_system_name),
    )


def _bullet_for_item(it: TenantIncidentDrilldownItem) -> str:
    name = it.ai_system_name.strip() or it.ai_system_id
    supplier = it.supplier_label_de.strip() or "unbekannt"
    kind = _dominant_kind(it)
    if kind == "safety":
        if it.incident_total_90d >= 6:
            core = (
                f"**{name}** (Lieferant: {supplier}) zeigt im Berichtszeitraum ein erhöhtes "
                "Volumen überwiegend sicherheitsrelevanter Laufzeit-Incidents; diese tragen "
                "überproportional zum OAMI bei."
            )
        else:
            core = (
                f"**{name}** (Lieferant: {supplier}) zeigt im Berichtszeitraum wenige, aber "
                "überwiegend sicherheitsrelevante Incidents; diese tragen überproportional "
                "zum OAMI bei."
            )
    elif kind == "availability":
        core = (
            f"**{name}** (Lieferant: {supplier}) verursacht vor allem "
            "Verfügbarkeits-/Performance-Incidents; Fokus auf Betriebsstabilität und "
            "Service-Recovery."
        )
    else:
        core = (
            f"**{name}** (Lieferant: {supplier}) weist nur vereinzelte, überwiegend unspezifische "
            "Laufzeit-Incidents auf; aktuell kein primärer OAMI-Treiber."
        )
    hint = (it.oami_local_hint_de or "").strip()
    if hint and hint not in core:
        core = f"{core} *Kurz:* {hint}"
    return f"- {core}"


def build_incident_system_supplier_drilldown_section(
    drilldown: TenantIncidentDrilldownOut | None,
    *,
    include_governance_brief_bridge: bool = False,
) -> str | None:
    """Markdown-Block mit Überschrift ###, oder None ohne sinnvollen Drilldown.

    Keine Roh-Gewichte im Fließtext; qualitative Einordnung und Volumina.
    """
    if drilldown is None or not drilldown.items:
        return None
    total_incidents = sum(x.incident_total_90d for x in drilldown.items)
    if total_incidents <= 0:
        return None

    selected = _select_for_report(drilldown.items)
    if not selected:
        return None

    subtitle = (
        "*Überblick zu den KI-Systemen und Lieferanten, die die Incident- und OAMI-Lage "
        "im Berichtszeitraum prägen.*"
    )
    bridge = ""
    if include_governance_brief_bridge:
        bridge = (
            "*Die nachfolgenden Systeme und Lieferanten spiegeln die oben genannten Schwerpunkte "
            "des Governance-Kurzbriefs wider.*\n\n"
        )
    intro_a = (
        "Die folgende Einordnung basiert auf aggregierten Laufzeit-Incidents "
        "(ohne Einzelfall-Inhalte) und der mandantenweiten OAMI-Gewichtung."
    )
    if total_incidents <= DRILLDOWN_LOW_TOTAL_THRESHOLD:
        intro_b = (
            "Im Berichtszeitraum wurden nur wenige Incidents beobachtet; kein System dominiert die "
            "OAMI-Lage. Die genannten Systeme sind dennoch die größten relativen Treiber "
            "im Fenster."
        )
    else:
        intro_b = (
            "Priorisiert sind die Systeme mit dem höchsten Incident-Volumen beziehungsweise dem "
            "stärksten Sicherheitsbezug gemäß OAMI-Logik."
        )

    bullets = "\n".join(_bullet_for_item(it) for it in selected)
    return (
        f"### System- und Lieferanten-Drilldown\n\n{subtitle}\n\n{bridge}"
        f"{intro_a} {intro_b}\n\n{bullets}\n"
    )

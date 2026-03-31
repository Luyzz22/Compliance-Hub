"""
NIS2/KRITIS- und Incident-Kontext für den Mandanten-Steckbrief (Markdown/JSON).

Nur Aggregationen und Stammdaten – keine Inhalte aus Einzelvorfällen.
"""

from __future__ import annotations

from typing import Literal

from sqlalchemy.orm import Session

from app.advisor_portfolio_models import IncidentBurdenLevel, Nis2EntityCategory
from app.repositories.incidents import IncidentRepository
from app.repositories.tenant_registry import TenantRegistryRepository
from app.services.advisor_portfolio_priority import (
    compute_incident_burden_level,
    effective_readiness_level,
    normalize_nis2_entity_category,
    regulatory_bump_suffix_de,
    regulatory_priority_bump_applies,
)

IncidentBurdenDe = Literal["niedrig", "mittel", "hoch"]


def nis2_entity_category_report_label_de(cat: Nis2EntityCategory) -> str:
    """Sachliche Einordnung für Berater-Texte."""
    if cat == "none":
        return (
            "Es liegt keine Einordnung als wichtige oder wesentliche Einrichtung nach NIS2 vor "
            "(bzw. außerhalb des relevanten NIS2-Scope in den Stammdaten geführt)."
        )
    if cat == "important_entity":
        return "Der Mandant ist als wichtige Einrichtung im Sinne von NIS2 eingestuft (Stammdaten)."
    return "Der Mandant ist als wesentliche Einrichtung im Sinne von NIS2 eingestuft (Stammdaten)."


def kritis_sector_label_de(sector_key: str | None) -> str | None:
    """Anzeigename für bekannte Sektorschlüssel; sonst Rohschlüssel."""
    if sector_key is None or not str(sector_key).strip():
        return None
    raw = str(sector_key).strip().lower()
    m = {
        "energy": "Energie",
        "health": "Gesundheit",
        "transport": "Transport",
        "water": "Wasser",
        "digital": "Digitale Infrastruktur",
        "financial": "Finanzmarkt",
        "other": "Sonstiger Sektor",
    }
    return m.get(raw, sector_key.strip())


def incident_burden_label_de(burden: IncidentBurdenLevel) -> IncidentBurdenDe:
    return {"low": "niedrig", "medium": "mittel", "high": "hoch"}[burden]


def oami_proxy_from_nis2_incident_readiness_pct(pct: float) -> str:
    """
    Grober Surrogat-Level für die regulatorische Prioritätslogik, aus NIS2-Incident-Readiness-%.

    Entspricht nicht dem Board-OAMI; dient nur der konsistenten Aufstock-Heuristik im Steckbrief.
    """
    if pct < 45.0:
        return "low"
    if pct < 80.0:
        return "medium"
    return "high"


def build_tenant_report_risiko_fields(
    session: Session,
    tenant_id: str,
    incident_repo: IncidentRepository,
    *,
    eu_ai_act_readiness_score: float,
    nis2_incident_readiness_percent: float,
) -> dict[str, object]:
    """Felder für AdvisorTenantReport (Risiko-/Incident-Abschnitt)."""
    treg = TenantRegistryRepository(session)
    trow = treg.get_by_id(tenant_id)
    nis2_cat = normalize_nis2_entity_category(trow.nis2_scope if trow else None)
    kritis_key = (
        trow.kritis_sector.strip()
        if trow and trow.kritis_sector and str(trow.kritis_sector).strip()
        else None
    )
    c90 = incident_repo.count_created_since_days(tenant_id, days=90)
    h90 = incident_repo.count_high_severity_since_days(tenant_id, days=90)
    burden: IncidentBurdenLevel = compute_incident_burden_level(c90, h90)
    open_cnt = incident_repo.count_open_for_tenant(tenant_id)
    rd_level = effective_readiness_level(None, eu_ai_act_readiness_score)
    oami_proxy = oami_proxy_from_nis2_incident_readiness_pct(nis2_incident_readiness_percent)
    recent = c90 > 0
    bump = regulatory_priority_bump_applies(
        nis2_category=nis2_cat,
        kritis_sector_key=kritis_key,
        recent_incidents_90d=recent,
        incident_burden=burden,
        readiness_level=rd_level,
        oami_level=oami_proxy,
    )
    note: str | None = None
    if bump:
        note = regulatory_bump_suffix_de(
            nis2_category=nis2_cat,
            kritis_sector_key=kritis_key,
            recent_incidents_90d=recent,
            incident_burden=burden,
        ).strip()

    return {
        "risiko_nis2_scope_label_de": nis2_entity_category_report_label_de(nis2_cat),
        "risiko_kritis_sector_label_de": kritis_sector_label_de(kritis_key),
        "risiko_incidents_90d_count": c90,
        "risiko_incidents_90d_high_severity": h90,
        "risiko_incident_burden_level": burden,
        "risiko_open_incidents_count": open_cnt,
        "risiko_regulatory_priority_note_de": note,
        "risiko_nis2_entity_category": nis2_cat,
    }

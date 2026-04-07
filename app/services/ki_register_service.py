"""KI-Register-Service: Aufbau, Export und Board-Aggregation."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime

from app.ai_governance_action_models import GovernanceActionStatus
from app.ki_register_models import (
    BoardAggregation,
    KIRegisterAuthorityExport,
    KIRegisterEntry,
    KIRegisterListResponse,
    PostMarketSurveillanceStatus,
)
from app.repositories.ai_governance_actions import AIGovernanceActionRepository
from app.repositories.ai_systems import AISystemRepository
from app.repositories.classifications import ClassificationRepository


def build_ki_register_entry(
    system,  # noqa: ANN001 – AISystem domain object
    classification=None,  # noqa: ANN001
    incidents: list[str] | None = None,
    risks: list[str] | None = None,
) -> KIRegisterEntry:
    """Map an AISystem + optional classification to a KIRegisterEntry."""
    return KIRegisterEntry(
        ai_system_id=system.id,
        tenant_id=system.tenant_id,
        name=system.name,
        description=system.description,
        provider_name=getattr(system, "provider_name", None),
        deployer_name=getattr(system, "deployer_name", None),
        intended_purpose=getattr(system, "intended_purpose", None),
        training_data_provenance=getattr(system, "training_data_provenance", None),
        fria_reference=getattr(system, "fria_reference", None),
        provider_responsibilities=getattr(system, "provider_responsibilities", None),
        deployer_responsibilities=getattr(system, "deployer_responsibilities", None),
        risk_category=(classification.risk_level if classification else None),
        ai_act_category=system.ai_act_category,
        annex_iii_category=(classification.annex_iii_category if classification else None),
        related_incident_ids=incidents or [],
        related_risk_ids=risks or [],
        pms_status=PostMarketSurveillanceStatus(getattr(system, "pms_status", None) or "pending"),
        pms_next_review_date=getattr(system, "pms_next_review_date", None),
        pms_last_review_date=getattr(system, "pms_last_review_date", None),
        business_unit=system.business_unit,
        owner_email=system.owner_email,
        created_at_utc=system.created_at_utc,
        updated_at_utc=system.updated_at_utc,
    )


def list_ki_register(
    tenant_id: str,
    ai_repo: AISystemRepository,
    cls_repo: ClassificationRepository,
) -> KIRegisterListResponse:
    """Alle KI-Systeme eines Mandanten als KI-Register-Einträge."""
    systems = ai_repo.list_for_tenant(tenant_id)
    items = []
    for sys in systems:
        cl = cls_repo.get_for_system(tenant_id, sys.id)
        items.append(build_ki_register_entry(sys, classification=cl))
    return KIRegisterListResponse(tenant_id=tenant_id, total=len(items), items=items)


def build_authority_export(
    tenant_id: str,
    ai_repo: AISystemRepository,
    cls_repo: ClassificationRepository,
    fmt: str = "json",
) -> KIRegisterAuthorityExport:
    """Strukturierter Export für nationale Aufsichtsbehörden."""
    register = list_ki_register(tenant_id, ai_repo, cls_repo)
    return KIRegisterAuthorityExport(
        tenant_id=tenant_id,
        export_timestamp=datetime.utcnow(),
        format=fmt,
        systems=register.items,
    )


def authority_export_xml(export: KIRegisterAuthorityExport) -> str:
    """Render KI-Register als XML für Behörden-Schnittstelle."""
    root = ET.Element("KIRegisterExport")
    ET.SubElement(root, "tenantId").text = export.tenant_id
    ET.SubElement(root, "exportTimestamp").text = export.export_timestamp.isoformat()
    systems_el = ET.SubElement(root, "systems")
    for sys in export.systems:
        s_el = ET.SubElement(systems_el, "system")
        ET.SubElement(s_el, "id").text = sys.ai_system_id
        ET.SubElement(s_el, "name").text = sys.name
        ET.SubElement(s_el, "description").text = sys.description or ""
        ET.SubElement(s_el, "intendedPurpose").text = sys.intended_purpose or ""
        ET.SubElement(s_el, "trainingDataProvenance").text = sys.training_data_provenance or ""
        ET.SubElement(s_el, "friaReference").text = sys.fria_reference or ""
        ET.SubElement(s_el, "providerName").text = sys.provider_name or ""
        ET.SubElement(s_el, "deployerName").text = sys.deployer_name or ""
        ET.SubElement(s_el, "riskCategory").text = sys.risk_category or ""
        ET.SubElement(s_el, "aiActCategory").text = sys.ai_act_category or ""
        ET.SubElement(s_el, "pmsStatus").text = sys.pms_status.value
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def build_board_aggregation(
    tenant_id: str,
    ai_repo: AISystemRepository,
    cls_repo: ClassificationRepository,
    action_repo: AIGovernanceActionRepository,
) -> BoardAggregation:
    """Aggregation für Board-Reporting."""
    systems = ai_repo.list_for_tenant(tenant_id)
    total = len(systems)
    high_risk_by_use_case: dict[str, int] = {}
    by_role: dict[str, int] = {}
    pms_overdue = 0
    now = datetime.utcnow()

    for sys in systems:
        cl = cls_repo.get_for_system(tenant_id, sys.id)

        # High-risk by use case
        if cl and cl.risk_level == "high_risk" and cl.annex_iii_category is not None:
            domain = _category_to_domain(cl.annex_iii_category)
            high_risk_by_use_case[domain] = high_risk_by_use_case.get(domain, 0) + 1

        # Role distribution
        provider = getattr(sys, "provider_name", None)
        deployer = getattr(sys, "deployer_name", None)
        if provider:
            by_role["provider"] = by_role.get("provider", 0) + 1
        if deployer:
            by_role["deployer"] = by_role.get("deployer", 0) + 1
        if not provider and not deployer:
            by_role["unassigned"] = by_role.get("unassigned", 0) + 1

        # PMS overdue
        pms_status = getattr(sys, "pms_status", "pending")
        pms_next = getattr(sys, "pms_next_review_date", None)
        if pms_status == "overdue" or (pms_next and pms_next < now):
            pms_overdue += 1

    # Open actions
    all_actions = action_repo.list_for_tenant(tenant_id, limit=500)
    open_count = sum(
        1
        for a in all_actions
        if a.status in (GovernanceActionStatus.open, GovernanceActionStatus.in_progress)
    )

    return BoardAggregation(
        tenant_id=tenant_id,
        total_systems=total,
        high_risk_by_use_case=high_risk_by_use_case,
        by_role=by_role,
        open_actions_count=open_count,
        pms_overdue_count=pms_overdue,
    )


# Reverse map of ANNEX_III_DOMAIN_TO_CATEGORY
_CATEGORY_TO_DOMAIN: dict[int, str] = {
    1: "biometrics",
    2: "critical_infra",
    3: "education",
    4: "employment",
    5: "essential_services",
    6: "law_enforcement",
    7: "migration",
    8: "justice",
}


def _category_to_domain(cat: int) -> str:
    return _CATEGORY_TO_DOMAIN.get(cat, f"category_{cat}")

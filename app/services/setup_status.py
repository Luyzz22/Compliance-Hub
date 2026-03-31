from __future__ import annotations

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.compliance_gap_models import ComplianceStatus
from app.models_db import (
    AIGovernanceActionDB,
    AISystemTable,
    ComplianceStatusTable,
    EvidenceFileTable,
    Nis2KritisKpiDB,
    PolicyTable,
    RiskClassificationDB,
)
from app.setup_models import TenantSetupStatus


def compute_tenant_setup_status(session: Session, tenant_id: str) -> TenantSetupStatus:
    """
    Leitet den Guided-Setup-Status ausschließlich aus vorhandenen Tabellen ab.

    Hinweise:
    - Klassifikation: Join RiskClassificationDB → ai_systems (tenant_id).
    - NIS2: nur Stammdaten-risk_level == \"high\" zählt als High-Risk für KPI-Pflicht.
    - Readiness-Baseline: kein UI-Tracking; Proxy über fortgeschrittene Compliance-Status-Einträge.
    """
    n_systems = session.scalar(
        select(func.count()).select_from(AISystemTable).where(AISystemTable.tenant_id == tenant_id),
    )
    n_systems = int(n_systems or 0)

    ai_inventory_completed = n_systems > 0

    n_classified = session.scalar(
        select(func.count(func.distinct(RiskClassificationDB.ai_system_id)))
        .select_from(RiskClassificationDB)
        .join(AISystemTable, AISystemTable.id == RiskClassificationDB.ai_system_id)
        .where(AISystemTable.tenant_id == tenant_id),
    )
    n_classified = int(n_classified or 0)

    classification_coverage_ratio = (n_classified / n_systems) if n_systems else 0.0
    classification_completed = n_systems > 0 and n_classified >= n_systems

    hr_without_kpi: list[str] = []
    if n_systems > 0:
        hr_without_kpi = list(
            session.scalars(
                select(AISystemTable.id)
                .where(
                    AISystemTable.tenant_id == tenant_id,
                    AISystemTable.risk_level == "high",
                )
                .outerjoin(
                    Nis2KritisKpiDB,
                    and_(
                        Nis2KritisKpiDB.ai_system_id == AISystemTable.id,
                        Nis2KritisKpiDB.tenant_id == tenant_id,
                    ),
                )
                .group_by(AISystemTable.id)
                .having(func.count(Nis2KritisKpiDB.id) == 0),
            ).all(),
        )
    # Ohne Register: KPI-Schritt nicht „vacuous true“ (Neumandant bleibt 0/7).
    nis2_kpis_seeded = n_systems > 0 and len(hr_without_kpi) == 0

    n_policies = session.scalar(
        select(func.count()).select_from(PolicyTable).where(PolicyTable.tenant_id == tenant_id),
    )
    policies_published = int(n_policies or 0) > 0

    n_actions = session.scalar(
        select(func.count())
        .select_from(AIGovernanceActionDB)
        .where(AIGovernanceActionDB.tenant_id == tenant_id),
    )
    actions_defined = int(n_actions or 0) > 0

    n_evidence_linked = session.scalar(
        select(func.count())
        .select_from(EvidenceFileTable)
        .where(
            EvidenceFileTable.tenant_id == tenant_id,
            or_(
                EvidenceFileTable.ai_system_id.is_not(None),
                EvidenceFileTable.action_id.is_not(None),
                EvidenceFileTable.audit_record_id.is_not(None),
            ),
        ),
    )
    evidence_attached = int(n_evidence_linked or 0) > 0

    n_compliance_progress = session.scalar(
        select(func.count())
        .select_from(ComplianceStatusTable)
        .where(
            ComplianceStatusTable.tenant_id == tenant_id,
            ComplianceStatusTable.status != ComplianceStatus.not_started.value,
        ),
    )
    eu_ai_act_readiness_baseline_created = int(n_compliance_progress or 0) > 0

    flags = [
        ai_inventory_completed,
        classification_completed,
        nis2_kpis_seeded,
        policies_published,
        actions_defined,
        evidence_attached,
        eu_ai_act_readiness_baseline_created,
    ]
    completed_steps = sum(1 for f in flags if f)

    return TenantSetupStatus(
        tenant_id=tenant_id,
        ai_inventory_completed=ai_inventory_completed,
        classification_completed=classification_completed,
        classification_coverage_ratio=round(classification_coverage_ratio, 4),
        nis2_kpis_seeded=nis2_kpis_seeded,
        policies_published=policies_published,
        actions_defined=actions_defined,
        evidence_attached=evidence_attached,
        eu_ai_act_readiness_baseline_created=eu_ai_act_readiness_baseline_created,
        completed_steps=completed_steps,
        total_steps=7,
    )

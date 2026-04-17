"""
Deterministic control suggestions (MVP) — no LLM.

Inputs wired to existing repo artefacts:
- TenantDB (NIS2/KRITIS sector, nis2_scope)
- AISystemTable risk_level (EU AI Act register)
- ServiceHealthIncidentTable (operational resilience)

Later: rule engine / RAG over norm text; optional POST to materialize suggestions as controls.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.governance_control_models import (
    FrameworkMappingCreate,
    GovernanceControlSuggestion,
)
from app.models_db import AISystemTable, TenantDB
from app.repositories.service_health import ServiceHealthRepository


def suggest_governance_controls(
    session: Session,
    tenant_id: str,
) -> list[GovernanceControlSuggestion]:
    """
    Return reusable control templates when signals indicate elevated exposure.

    Rules (explicit, auditable):
    1) Open service_health_incidents → monitoring / incident / BCM style controls
       (feeds Operational Resilience + NIS2 Art.21 narrative overlap).
    2) Any AI system with risk_level in (high, unacceptable) → AI Act + ISO 42001
       logging / PMS / technical documentation posture.
    3) Tenant marked KRITIS sector OR nis2_scope indicates in_scope with sector hint
       → NIS2 + ISO 27001 supply-chain / governance controls (MVP heuristic).
    """
    suggestions: list[GovernanceControlSuggestion] = []

    sh = ServiceHealthRepository(session)
    if sh.count_open_incidents(tenant_id) > 0:
        suggestions.append(
            GovernanceControlSuggestion(
                suggestion_key="ops_open_health_incidents",
                title="Incident-Triage und Eskalationspfad (Monitoring)",
                description=(
                    "Offene service_health_incidents: formalisiertes Triage, "
                    "Eskalation, Nachweise für NIS2-Betriebslage und BCM."
                ),
                framework_tags=["NIS2", "ISO_27001"],
                framework_mappings=[
                    FrameworkMappingCreate(
                        framework="NIS2",
                        clause_ref="Art. 21 (incident handling)",
                        mapping_note="Anknüpfung an operational_health_incidents",
                    ),
                    FrameworkMappingCreate(
                        framework="ISO_27001",
                        clause_ref="Annex A.16 (Information security aspects of BCM)",
                        mapping_note="BCM / Verfügbarkeit",
                    ),
                ],
                triggered_by={"signal": "open_service_health_incidents"},
            )
        )

    high_ai = session.scalar(
        select(func.count())
        .select_from(AISystemTable)
        .where(
            AISystemTable.tenant_id == tenant_id,
            AISystemTable.risk_level.in_(("high", "unacceptable")),
        )
    )
    if int(high_ai or 0) > 0:
        suggestions.append(
            GovernanceControlSuggestion(
                suggestion_key="ai_act_high_risk_register",
                title="Post-Market Surveillance & Logging (High-Risk KI)",
                description=(
                    "Mindestens ein KI-System mit hohem Risiko im Register — "
                    "PMS, Logging und technische Dokumentation evidenzieren "
                    "(EU AI Act / ISO 42001)."
                ),
                framework_tags=["EU_AI_ACT", "ISO_42001"],
                framework_mappings=[
                    FrameworkMappingCreate(
                        framework="EU_AI_ACT",
                        clause_ref="Art. 12 (record-keeping) / Art. 72 (post-market monitoring)",
                        mapping_note="Anknüpfung an ai_systems.risk_level",
                    ),
                    FrameworkMappingCreate(
                        framework="ISO_42001",
                        clause_ref="Annex A — operational lifecycle controls",
                        mapping_note="AI-Managementsystem",
                    ),
                ],
                triggered_by={
                    "signal": "ai_system_high_or_unacceptable",
                    "count": int(high_ai or 0),
                },
            )
        )

    tenant = session.get(TenantDB, tenant_id)
    if tenant is not None and (
        (tenant.kritis_sector and tenant.kritis_sector.strip())
        or tenant.nis2_scope == "in_scope"
    ):
        suggestions.append(
            GovernanceControlSuggestion(
                suggestion_key="nis2_governance_supply_chain",
                title="Lieferketten- und Geschäftsleitungspflichten (NIS2)",
                description=(
                    "Mandant mit KRITIS-Sektor oder NIS2-In-Scope-Flag — "
                    "Dokumentation zu Lieferanten, Risikoüberwachung und Management-Reviews."
                ),
                framework_tags=["NIS2", "ISO_27001", "ISO_27701"],
                framework_mappings=[
                    FrameworkMappingCreate(
                        framework="NIS2",
                        clause_ref="Art. 21 / supply chain",
                        mapping_note="Heuristik: tenants.kritis_sector / nis2_scope",
                    ),
                    FrameworkMappingCreate(
                        framework="ISO_27001",
                        clause_ref="Annex A.5 / A.15",
                        mapping_note="Lieferanten- und Zugangskontrollen",
                    ),
                    FrameworkMappingCreate(
                        framework="ISO_27701",
                        clause_ref="PIMS operational controls",
                        mapping_note="Privacy Information Management",
                    ),
                ],
                triggered_by={
                    "signal": "tenant_nis2_kritis_heuristic",
                    "kritis_sector": tenant.kritis_sector,
                    "nis2_scope": tenant.nis2_scope,
                },
            )
        )

    return suggestions

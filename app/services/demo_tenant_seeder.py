"""Befüllt einen leeren Mandanten mit realistischen Demo-Daten (nur für Demo-/Pilot-Tenants)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai_governance_action_models import AIGovernanceActionCreate, GovernanceActionStatus
from app.ai_system_models import (
    AIActCategory,
    AISystemCreate,
    AISystemCriticality,
    AISystemRiskLevel,
    DataSensitivity,
)
from app.classification_models import ClassificationPath, RiskClassification, RiskLevel
from app.demo_models import DemoSeedResponse
from app.demo_templates import get_demo_template
from app.models_db import (
    AIGovernanceActionDB,
    AISystemTable,
    EvidenceFileTable,
    PolicyTable,
    RiskClassificationDB,
)
from app.nis2_kritis_models import Nis2KritisKpiType
from app.repositories.advisor_tenants import AdvisorTenantRepository
from app.repositories.ai_governance_actions import AIGovernanceActionRepository
from app.repositories.ai_systems import AISystemRepository
from app.repositories.classifications import ClassificationRepository
from app.repositories.evidence_files import EvidenceFileRepository
from app.repositories.nis2_kritis_kpis import Nis2KritisKpiRepository
from app.repositories.policies import PolicyRepository
from app.services.demo_tenant_seed_extras import apply_demo_seed_extensions
from app.services.evidence_storage import EvidenceStorageBackend, get_evidence_storage


def _annex_iii_high(ai_id: str, category: int, rationale: str) -> RiskClassification:
    return RiskClassification(
        ai_system_id=ai_id,
        risk_level=RiskLevel.high_risk,
        classification_path=ClassificationPath.annex_iii,
        annex_iii_category=category,
        profiles_natural_persons=False,
        classification_rationale=rationale,
        classified_by="demo-seed",
    )


def _limited(ai_id: str, rationale: str) -> RiskClassification:
    return RiskClassification(
        ai_system_id=ai_id,
        risk_level=RiskLevel.limited_risk,
        classification_path=ClassificationPath.transparency,
        profiles_natural_persons=False,
        classification_rationale=rationale,
        classified_by="demo-seed",
    )


def _minimal(ai_id: str, rationale: str) -> RiskClassification:
    return RiskClassification(
        ai_system_id=ai_id,
        risk_level=RiskLevel.minimal_risk,
        classification_path=ClassificationPath.none,
        profiles_natural_persons=False,
        classification_rationale=rationale,
        classified_by="demo-seed",
    )


def _bid(tenant_id: str, slug: str) -> str:
    return f"{tenant_id}-demo-{slug}"


def _build_plan(
    template_key: str,
    tenant_id: str,
) -> list[tuple[AISystemCreate, RiskClassification, tuple[int, int, int] | None]]:
    """
    Liefert (AISystemCreate, Classification, kpi_triple | None).
    kpi_triple = (incident %, supplier %, ot_it %) für High-Risk-Systeme, sonst None.
    """
    if template_key == "kritis_energy":
        return [
            (
                AISystemCreate(
                    id=_bid(tenant_id, "netzlast"),
                    name="Netzlast-Prognose (KRITIS)",
                    description=(
                        "Hochrisiko-KI für Lastprognose im Verteilnetz; Lieferanten-Register "
                        "noch unvollständig (Demo-Lücke)."
                    ),
                    business_unit="Netzbetrieb",
                    risk_level=AISystemRiskLevel.high,
                    ai_act_category=AIActCategory.high_risk,
                    gdpr_dpia_required=True,
                    owner_email="ciso@demo-kritis.example",
                    criticality=AISystemCriticality.very_high,
                    data_sensitivity=DataSensitivity.restricted,
                    has_incident_runbook=True,
                    has_supplier_risk_register=False,
                    has_backup_runbook=True,
                ),
                _annex_iii_high(
                    _bid(tenant_id, "netzlast"),
                    2,
                    "Demo: Anhang III, kritische Infrastruktur / Energie.",
                ),
                (72, 48, 38),
            ),
            (
                AISystemCreate(
                    id=_bid(tenant_id, "outage"),
                    name="Ausfall-Warnmodell (SCADA-Anbindung)",
                    description="Prognose von Schalthandlungen; begrenzte Transparenzpflichten.",
                    business_unit="Leittechnik",
                    risk_level=AISystemRiskLevel.limited,
                    ai_act_category=AIActCategory.limited_risk,
                    gdpr_dpia_required=False,
                    owner_email="ot@demo-kritis.example",
                    criticality=AISystemCriticality.high,
                    data_sensitivity=DataSensitivity.confidential,
                    has_incident_runbook=True,
                    has_supplier_risk_register=True,
                    has_backup_runbook=False,
                ),
                _limited(
                    _bid(tenant_id, "outage"),
                    "Demo: Transparenz / dokumentierte Einschränkungen.",
                ),
                None,
            ),
            (
                AISystemCreate(
                    id=_bid(tenant_id, "supplier_bot"),
                    name="Supplier-Risk Scoring (Drittparteien)",
                    description="Bewertung von IT-/OT-Lieferanten; Minimalrisiko im Register.",
                    business_unit="Beschaffung",
                    risk_level=AISystemRiskLevel.low,
                    ai_act_category=AIActCategory.minimal_risk,
                    gdpr_dpia_required=False,
                    owner_email="procurement@demo-kritis.example",
                    criticality=AISystemCriticality.medium,
                    data_sensitivity=DataSensitivity.internal,
                    has_incident_runbook=True,
                    has_supplier_risk_register=True,
                    has_backup_runbook=True,
                ),
                _minimal(_bid(tenant_id, "supplier_bot"), "Demo: unterhalb Hochrisiko."),
                None,
            ),
            (
                AISystemCreate(
                    id=_bid(tenant_id, "smart_meter"),
                    name="Smart-Meter Anomalieerkennung",
                    description="Batch-Auswertung ohne Echtzeit-Biometrie; KPI-Lücken OT/IT.",
                    business_unit="Messstellenbetrieb",
                    risk_level=AISystemRiskLevel.high,
                    ai_act_category=AIActCategory.high_risk,
                    gdpr_dpia_required=True,
                    owner_email="metering@demo-kritis.example",
                    criticality=AISystemCriticality.high,
                    data_sensitivity=DataSensitivity.confidential,
                    has_incident_runbook=True,
                    has_supplier_risk_register=True,
                    has_backup_runbook=True,
                ),
                _annex_iii_high(
                    _bid(tenant_id, "smart_meter"),
                    2,
                    "Demo: Hochrisiko Use-Case mit vollständigeren Kontrollen.",
                ),
                (68, 62, 41),
            ),
        ]

    if template_key == "industrial_sme":
        return [
            (
                AISystemCreate(
                    id=_bid(tenant_id, "qc-vision"),
                    name="Qualitätskontrolle Vision",
                    description="Inline-Inspektion; DPIA relevant; Supplier-Register Lücke.",
                    business_unit="Produktion",
                    risk_level=AISystemRiskLevel.high,
                    ai_act_category=AIActCategory.high_risk,
                    gdpr_dpia_required=True,
                    owner_email="qm@demo-mfg.example",
                    criticality=AISystemCriticality.high,
                    data_sensitivity=DataSensitivity.confidential,
                    has_incident_runbook=True,
                    has_supplier_risk_register=False,
                    has_backup_runbook=True,
                ),
                _annex_iii_high(
                    _bid(tenant_id, "qc-vision"),
                    5,
                    "Demo: Anhang III / wesentliche private Dienste (Produktsicherheit).",
                ),
                (55, 52, 58),
            ),
            (
                AISystemCreate(
                    id=_bid(tenant_id, "pm"),
                    name="Predictive Maintenance",
                    description="Sensorfusion für Anlagen; begrenztes Risiko.",
                    business_unit="Instandhaltung",
                    risk_level=AISystemRiskLevel.limited,
                    ai_act_category=AIActCategory.limited_risk,
                    gdpr_dpia_required=False,
                    owner_email="maint@demo-mfg.example",
                    criticality=AISystemCriticality.medium,
                    data_sensitivity=DataSensitivity.internal,
                    has_incident_runbook=True,
                    has_supplier_risk_register=True,
                    has_backup_runbook=True,
                ),
                _limited(_bid(tenant_id, "pm"), "Demo: Transparenzpflichten erfüllt."),
                None,
            ),
            (
                AISystemCreate(
                    id=_bid(tenant_id, "doc-rag"),
                    name="Internes Wissens-RAG",
                    description="Suche in Handbüchern; Minimalrisiko.",
                    business_unit="IT",
                    risk_level=AISystemRiskLevel.low,
                    ai_act_category=AIActCategory.minimal_risk,
                    gdpr_dpia_required=False,
                    owner_email="it@demo-mfg.example",
                    criticality=AISystemCriticality.low,
                    data_sensitivity=DataSensitivity.internal,
                    has_incident_runbook=False,
                    has_supplier_risk_register=True,
                    has_backup_runbook=True,
                ),
                _minimal(_bid(tenant_id, "doc-rag"), "Demo: Minimalrisiko-Chatbot."),
                None,
            ),
            (
                AISystemCreate(
                    id=_bid(tenant_id, "safety"),
                    name="Arbeitssicherheit-Assistenz",
                    description="Hochrisiko-Empfehlungen an Maschinen; vollständige Runbooks.",
                    business_unit="EHS",
                    risk_level=AISystemRiskLevel.high,
                    ai_act_category=AIActCategory.high_risk,
                    gdpr_dpia_required=True,
                    owner_email="ehs@demo-mfg.example",
                    criticality=AISystemCriticality.very_high,
                    data_sensitivity=DataSensitivity.restricted,
                    has_incident_runbook=True,
                    has_supplier_risk_register=True,
                    has_backup_runbook=True,
                ),
                _annex_iii_high(
                    _bid(tenant_id, "safety"),
                    5,
                    "Demo: Sicherheitskomponente / Arbeitsumgebung.",
                ),
                (61, 70, 44),
            ),
        ]

    if template_key == "tax_advisor":
        return [
            (
                AISystemCreate(
                    id=_bid(tenant_id, "doc-review"),
                    name="Dokumentenprüfung Belege",
                    description=(
                        "High-Risk Klassifikation für automatisierte Steuerberatung (Demo)."
                    ),
                    business_unit="Mandantenbetreuung",
                    risk_level=AISystemRiskLevel.high,
                    ai_act_category=AIActCategory.high_risk,
                    gdpr_dpia_required=True,
                    owner_email="partner@demo-wp.example",
                    criticality=AISystemCriticality.high,
                    data_sensitivity=DataSensitivity.restricted,
                    has_incident_runbook=True,
                    has_supplier_risk_register=True,
                    has_backup_runbook=False,
                ),
                _annex_iii_high(
                    _bid(tenant_id, "doc-review"),
                    8,
                    "Demo: Justiz / Rechtsauslegung (Assistenz).",
                ),
                (58, 66, 72),
            ),
            (
                AISystemCreate(
                    id=_bid(tenant_id, "vat"),
                    name="Umsatzsteuer-Plausibilisierung",
                    description="Regelbasiert mit ML; Transparenz.",
                    business_unit="Steuern",
                    risk_level=AISystemRiskLevel.limited,
                    ai_act_category=AIActCategory.limited_risk,
                    gdpr_dpia_required=False,
                    owner_email="vat@demo-wp.example",
                    criticality=AISystemCriticality.medium,
                    data_sensitivity=DataSensitivity.confidential,
                    has_incident_runbook=True,
                    has_supplier_risk_register=True,
                    has_backup_runbook=True,
                ),
                _limited(_bid(tenant_id, "vat"), "Demo: Transparenz / Kennzeichnung."),
                None,
            ),
            (
                AISystemCreate(
                    id=_bid(tenant_id, "client-chat"),
                    name="Mandanten-Chatbot (FAQ)",
                    description="Öffentliche FAQs; Minimalrisiko.",
                    business_unit="Kanzlei-Marketing",
                    risk_level=AISystemRiskLevel.low,
                    ai_act_category=AIActCategory.minimal_risk,
                    gdpr_dpia_required=False,
                    owner_email="marketing@demo-wp.example",
                    criticality=AISystemCriticality.low,
                    data_sensitivity=DataSensitivity.public,
                    has_incident_runbook=True,
                    has_supplier_risk_register=True,
                    has_backup_runbook=True,
                ),
                _minimal(_bid(tenant_id, "client-chat"), "Demo: Minimalrisiko."),
                None,
            ),
            (
                AISystemCreate(
                    id=_bid(tenant_id, "anomaly"),
                    name="Anomalie-Erkennung Buchungen",
                    description="Auffällige Buchungsmuster; High-Risk für GoBD-Nachweis.",
                    business_unit="Revision",
                    risk_level=AISystemRiskLevel.high,
                    ai_act_category=AIActCategory.high_risk,
                    gdpr_dpia_required=True,
                    owner_email="revision@demo-wp.example",
                    criticality=AISystemCriticality.high,
                    data_sensitivity=DataSensitivity.confidential,
                    has_incident_runbook=True,
                    has_supplier_risk_register=True,
                    has_backup_runbook=True,
                ),
                _annex_iii_high(
                    _bid(tenant_id, "anomaly"),
                    8,
                    "Demo: Hochrisiko-Assistenz im steuerlichen Kontext.",
                ),
                (64, 59, 68),
            ),
        ]

    raise ValueError(f"Unknown template_key: {template_key}")


def _action_specs(primary_system: str, secondary: str) -> list[AIGovernanceActionCreate]:
    return [
        AIGovernanceActionCreate(
            related_ai_system_id=primary_system,
            related_requirement="EU AI Act Art. 9 Risikomanagementsystem",
            title="Risikomanagement-Dokumentation für Hochrisiko-KI finalisieren",
            status=GovernanceActionStatus.in_progress,
        ),
        AIGovernanceActionCreate(
            related_ai_system_id=primary_system,
            related_requirement="EU AI Act Art. 12 Protokollierung",
            title="Logging-Konzept und Aufbewahrung prüfen",
            status=GovernanceActionStatus.open,
        ),
        AIGovernanceActionCreate(
            related_ai_system_id=secondary,
            related_requirement="NIS2 Art. 21 Incident Response",
            title="Incident-Playbook mit KI-Betrieb abstimmen",
            status=GovernanceActionStatus.open,
        ),
        AIGovernanceActionCreate(
            related_ai_system_id=secondary,
            related_requirement="NIS2 Art. 21 Lieferketten",
            title="Supplier-Risk-Register für kritische KI-Lieferanten vervollständigen",
            status=GovernanceActionStatus.open,
        ),
        AIGovernanceActionCreate(
            related_ai_system_id=None,
            related_requirement="ISO 42001 AI IMS",
            title="AI-Governance-Rollen (CISO, DSB, Fachbereich) schriftlich festlegen",
            status=GovernanceActionStatus.open,
        ),
    ]


def seed_demo_tenant(
    session: Session,
    template_key: str,
    tenant_id: str,
    *,
    advisor_id: str | None = None,
    ai_repo: AISystemRepository,
    cls_repo: ClassificationRepository,
    nis2_repo: Nis2KritisKpiRepository,
    policy_repo: PolicyRepository,
    action_repo: AIGovernanceActionRepository,
    evidence_repo: EvidenceFileRepository,
    storage: EvidenceStorageBackend | None = None,
) -> DemoSeedResponse:
    if get_demo_template(template_key) is None:
        raise ValueError(f"Unknown template_key: {template_key}")

    if ai_repo.list_for_tenant(tenant_id):
        raise ValueError(
            "Tenant already has AI systems; demo seeding only supports empty tenants.",
        )

    plan = _build_plan(template_key, tenant_id)
    now = datetime.now(UTC)
    kpi_count = 0

    for create_body, classification, kpi_triple in plan:
        ai_repo.create(tenant_id, create_body)
        cls_repo.save(tenant_id, classification)
        if kpi_triple is not None:
            inc, sup, ot = kpi_triple
            nis2_repo.upsert(
                tenant_id,
                create_body.id,
                Nis2KritisKpiType.INCIDENT_RESPONSE_MATURITY,
                inc,
                "demo-seed",
                now,
            )
            nis2_repo.upsert(
                tenant_id,
                create_body.id,
                Nis2KritisKpiType.SUPPLIER_RISK_COVERAGE,
                sup,
                "demo-seed",
                now,
            )
            nis2_repo.upsert(
                tenant_id,
                create_body.id,
                Nis2KritisKpiType.OT_IT_SEGREGATION,
                ot,
                "demo-seed",
                now,
            )
            kpi_count += 3

    policy_repo.ensure_default_policy_rules(tenant_id)

    primary = plan[0][0].id
    secondary = plan[1][0].id
    for body in _action_specs(primary, secondary):
        action_repo.create(tenant_id, body)

    store = storage or get_evidence_storage()
    demo_bytes = b"# Demo-Evidenz\nNur fuer Demos/Piloten. Keine produktiven Inhalte.\n"
    for label, sys_id in (
        ("readme", primary),
        ("kpi-nachweis", primary),
        ("prozessbeschreibung", secondary),
    ):
        key = store.store_file(tenant_id, demo_bytes, "text/markdown")
        evidence_repo.create(
            tenant_id=tenant_id,
            storage_key=key,
            filename_original=f"demo-{label}.md",
            content_type="text/markdown",
            size_bytes=len(demo_bytes),
            uploaded_by="demo-seed",
            ai_system_id=sys_id,
            audit_record_id=None,
            action_id=None,
            norm_framework="DEMO",
            norm_reference="internal-demo",
        )

    advisor_linked = False
    if advisor_id and str(advisor_id).strip():
        adv = AdvisorTenantRepository(session)
        tmpl = get_demo_template(template_key)
        adv.upsert_link(
            advisor_id=str(advisor_id).strip(),
            tenant_id=tenant_id,
            tenant_display_name=tmpl.name if tmpl else None,
            industry=tmpl.industry if tmpl else None,
            country=tmpl.country if tmpl else None,
        )
        advisor_linked = True

    n_policies = int(
        session.scalar(
            select(func.count()).select_from(PolicyTable).where(PolicyTable.tenant_id == tenant_id),
        )
        or 0,
    )
    n_actions_db = int(
        session.scalar(
            select(func.count())
            .select_from(AIGovernanceActionDB)
            .where(AIGovernanceActionDB.tenant_id == tenant_id),
        )
        or 0,
    )
    n_class = int(
        session.scalar(
            select(func.count(func.distinct(RiskClassificationDB.ai_system_id)))
            .select_from(RiskClassificationDB)
            .join(AISystemTable, AISystemTable.id == RiskClassificationDB.ai_system_id)
            .where(AISystemTable.tenant_id == tenant_id),
        )
        or 0,
    )
    n_evidence_db = int(
        session.scalar(
            select(func.count())
            .select_from(EvidenceFileTable)
            .where(EvidenceFileTable.tenant_id == tenant_id),
        )
        or 0,
    )

    extra = apply_demo_seed_extensions(
        session,
        tenant_id,
        primary_ai_system_id=primary,
        secondary_ai_system_id=secondary,
    )

    return DemoSeedResponse(
        template_key=template_key,
        tenant_id=tenant_id,
        ai_systems_count=len(plan),
        governance_actions_count=n_actions_db,
        evidence_files_count=n_evidence_db,
        nis2_kpi_rows_count=kpi_count,
        policy_rows_count=n_policies,
        classifications_count=n_class,
        advisor_linked=advisor_linked,
        board_reports_count=int(extra.get("board_reports_count", 0)),
        ai_kpi_value_rows_count=int(extra.get("ai_kpi_value_rows_count", 0)),
        cross_reg_control_rows_count=int(extra.get("cross_reg_control_rows_count", 0)),
    )

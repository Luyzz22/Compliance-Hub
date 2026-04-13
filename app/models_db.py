from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

Base = declarative_base()


class TenantDB(Base):
    """Registrierter Mandant (Pilot-/Enterprise-Provisioning)."""

    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[str] = mapped_column(String(128), nullable=False)
    country: Mapped[str] = mapped_column(String(64), nullable=False, default="DE")
    nis2_scope: Mapped[str] = mapped_column(String(64), nullable=False, default="in_scope")
    kritis_sector: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ai_act_scope: Mapped[str] = mapped_column(String(64), nullable=False, default="in_scope")
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    demo_playground: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )


class TenantAIGovernanceSetupDB(Base):
    """Persistenter Stand des AI-Governance-Setup-Wizards (Mandant)."""

    __tablename__ = "tenant_ai_governance_setup"

    tenant_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    setup_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )


class EnterpriseOnboardingReadinessDB(Base):
    """Enterprise onboarding readiness profile per tenant."""

    __tablename__ = "enterprise_onboarding_readiness"

    tenant_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_by: Mapped[str] = mapped_column(String(320), nullable=False, default="api_client")


class EnterpriseIntegrationBlueprintDB(Base):
    """Metadata-first integration blueprint rows per tenant and source system."""

    __tablename__ = "enterprise_integration_blueprints"
    __table_args__ = (
        UniqueConstraint("tenant_id", "blueprint_id", name="uq_enterprise_integration_blueprint"),
        Index(
            "ix_enterprise_integration_blueprints_tenant_source",
            "tenant_id",
            "source_system_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    blueprint_id: Mapped[str] = mapped_column(String(120), nullable=False)
    source_system_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_by: Mapped[str] = mapped_column(String(320), nullable=False, default="api_client")


class EnterpriseConnectorInstanceDB(Base):
    """First live connector skeleton runtime state per tenant."""

    __tablename__ = "enterprise_connector_instances"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_enterprise_connector_instance_tenant"),
        Index(
            "ix_enterprise_connector_instances_tenant_source",
            "tenant_id",
            "source_system_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    connector_instance_id: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_system_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="generic_api"
    )
    connection_status: Mapped[str] = mapped_column(
        String(64), nullable=False, default="not_configured"
    )
    sync_status: Mapped[str] = mapped_column(String(64), nullable=False, default="idle")
    enabled_evidence_domains: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_by: Mapped[str] = mapped_column(String(320), nullable=False, default="api_client")


class EnterpriseConnectorSyncRunDB(Base):
    """Audit-friendly sync run results for connector skeleton."""

    __tablename__ = "enterprise_connector_sync_runs"
    __table_args__ = (
        Index("ix_enterprise_connector_sync_runs_tenant_started", "tenant_id", "started_at_utc"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sync_run_id: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    connector_instance_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    sync_status: Mapped[str] = mapped_column(String(64), nullable=False, default="running")
    started_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    finished_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    records_ingested: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_normalized: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    failure_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retry_of_sync_run_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_de: Mapped[str] = mapped_column(Text, nullable=False, default="")
    details_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class EnterpriseConnectorEvidenceRecordDB(Base):
    """Normalized external evidence records ingested by connector skeleton."""

    __tablename__ = "enterprise_connector_evidence_records"
    __table_args__ = (
        Index(
            "ix_enterprise_connector_evidence_records_tenant_domain",
            "tenant_id",
            "evidence_domain",
        ),
        UniqueConstraint(
            "tenant_id",
            "connector_instance_id",
            "evidence_domain",
            "external_record_id",
            name="uq_enterprise_connector_evidence_external",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    connector_instance_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    sync_run_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    evidence_domain: Mapped[str] = mapped_column(String(64), nullable=False)
    external_record_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    normalized_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    ingested_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )


class TenantApiKeyDB(Base):
    """API-Schlüssel pro Mandant (Hash-only, Klartext nur bei Erstellung)."""

    __tablename__ = "tenant_api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    key_last4: Mapped[str] = mapped_column(String(4), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )


class TenantFeatureFlagOverrideDB(Base):
    """Mandanten-spezifische Feature-Flag-Overrides (Pilot-Defaults vs. ENV-Fallback)."""

    __tablename__ = "tenant_feature_flag_overrides"
    __table_args__ = (UniqueConstraint("tenant_id", "flag_key", name="uq_tenant_feature_flag"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    flag_key: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)


class AdvisorTenantDB(Base):
    """Zuordnung Berater → Mandanten (Portfolio-Sicht, ohne Tenant-Daten zu mischen)."""

    __tablename__ = "advisor_tenants"
    __table_args__ = (
        UniqueConstraint(
            "advisor_id",
            "tenant_id",
            name="uq_advisor_tenants_advisor_tenant",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    advisor_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    tenant_display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(128), nullable=True)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)


class RiskClassificationDB(Base):
    __tablename__ = "risk_classifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ai_system_id: Mapped[str] = mapped_column(String(255), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(50), nullable=False)
    classification_path: Mapped[str] = mapped_column(String(50), nullable=False)
    annex_i_legislation: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_safety_component: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    requires_third_party_assessment: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    annex_iii_category: Mapped[int | None] = mapped_column(nullable=True)
    profiles_natural_persons: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    exception_applies: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    exception_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    classification_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float] = mapped_column(nullable=False, default=1.0)
    classified_by: Mapped[str] = mapped_column(String(50), default="auto")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
    )


class AISystemTable(Base):
    __tablename__ = "ai_systems"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    business_unit: Mapped[str] = mapped_column(String(255), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(50), nullable=False)
    ai_act_category: Mapped[str] = mapped_column(String(50), nullable=False)
    gdpr_dpia_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    owner_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    criticality: Mapped[str] = mapped_column(String(50), nullable=False, default="medium")
    data_sensitivity: Mapped[str] = mapped_column(String(50), nullable=False, default="internal")
    has_incident_runbook: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_supplier_risk_register: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_backup_runbook: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    # ── KI-Register Pflichtfelder (EU AI Act) ─────────────────
    intended_purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    training_data_provenance: Mapped[str | None] = mapped_column(Text, nullable=True)
    fria_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    deployer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_responsibilities: Mapped[str | None] = mapped_column(Text, nullable=True)
    deployer_responsibilities: Mapped[str | None] = mapped_column(Text, nullable=True)
    pms_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    pms_next_review_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pms_last_review_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )


class AISystemInventoryProfileDB(Base):
    __tablename__ = "ai_system_inventory_profiles"

    tenant_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    ai_system_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("ai_systems.id", ondelete="CASCADE"),
        primary_key=True,
    )
    provider_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_type: Mapped[str] = mapped_column(String(32), nullable=False, default="external")
    use_case: Mapped[str] = mapped_column(String(500), nullable=False)
    business_process: Mapped[str | None] = mapped_column(String(255), nullable=True)
    eu_ai_act_scope: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="review_needed",
    )
    iso_42001_scope: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="review_needed",
    )
    nis2_scope: Mapped[str] = mapped_column(String(32), nullable=False, default="review_needed")
    dsgvo_special_risk: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="review_needed",
    )
    register_status: Mapped[str] = mapped_column(String(32), nullable=False, default="planned")
    register_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    authority_reporting_flags: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    created_by: Mapped[str] = mapped_column(String(320), nullable=False, default="api_client")
    updated_by: Mapped[str] = mapped_column(String(320), nullable=False, default="api_client")


class AIRegisterEntryDB(Base):
    __tablename__ = "ai_register_entries"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "ai_system_id",
            "version",
            name="uq_ai_register_entries_tenant_system_version",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ai_system_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("ai_systems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="planned")
    authority_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    national_register_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reportable_incident: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reportable_change: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fields_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    created_by: Mapped[str] = mapped_column(String(320), nullable=False, default="api_client")


class Nis2KritisKpiDB(Base):
    """NIS2 / KRITIS-orientierte KPIs pro KI-System (mandantenfähig)."""

    __tablename__ = "nis2_kritis_kpis"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "ai_system_id",
            "kpi_type",
            name="uq_nis2_kritis_kpi_tenant_system_type",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ai_system_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("ai_systems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kpi_type: Mapped[str] = mapped_column(String(64), nullable=False)
    value_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class AiKpiDefinitionDB(Base):
    """Globale KPI-/KRI-Definitionen (EU AI Act Post-Market / ISO 42001 Performance Evaluation)."""

    __tablename__ = "ai_kpi_definitions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    recommended_direction: Mapped[str] = mapped_column(String(16), nullable=False)
    framework_tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    alert_threshold_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    alert_threshold_low: Mapped[float | None] = mapped_column(Float, nullable=True)


class AiSystemKpiValueDB(Base):
    """Zeitreihenwerte je KI-System und KPI-Definition (mandantenisoliert)."""

    __tablename__ = "ai_system_kpi_values"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "ai_system_id",
            "kpi_definition_id",
            "period_start",
            name="uq_ai_system_kpi_value_period",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ai_system_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("ai_systems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kpi_definition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ai_kpi_definitions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )


class PolicyTable(Base):
    __tablename__ = "policies"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class RuleTable(Base):
    __tablename__ = "rules"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    policy_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    condition_type: Mapped[str] = mapped_column(String(255), nullable=False)


class ViolationTable(Base):
    __tablename__ = "violations"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ai_system_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    rule_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )


class ComplianceStatusTable(Base):
    __tablename__ = "compliance_status"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ai_system_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    requirement_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )


class IncidentTable(Base):
    """NIS2 Art. 21/23, ISO 42001 Incident Management – mandantenfähig, RLS-konform."""

    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ai_system_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    acknowledged_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class AIGovernanceActionDB(Base):
    """Leichtgewichtige Maßnahmen/Gaps (EU AI Act, NIS2) – mandantenfähig."""

    __tablename__ = "ai_governance_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    related_ai_system_id: Mapped[str | None] = mapped_column(
        String(255),
        ForeignKey("ai_systems.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    related_requirement: Mapped[str] = mapped_column(String(500), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    owner: Mapped[str | None] = mapped_column(String(320), nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )


class EvidenceFileTable(Base):
    """Persistente Evidenz-Dateien (mandantenisoliert, Storage-Key ohne PII im Pfad)."""

    __tablename__ = "evidence_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ai_system_id: Mapped[str | None] = mapped_column(
        String(255),
        ForeignKey("ai_systems.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    audit_record_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    action_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ai_governance_actions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    filename_original: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_by: Mapped[str] = mapped_column(String(320), nullable=False)
    norm_framework: Mapped[str | None] = mapped_column(String(64), nullable=True)
    norm_reference: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )


class AuditLogTable(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    before: Mapped[str | None] = mapped_column(Text, nullable=True)
    after: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entry_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    actor_role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(32), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class UsageEventTable(Base):
    """Aggregierbare Nutzungsereignisse (kein technisches Audit-Log)."""

    __tablename__ = "usage_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )


class TenantLLMPolicyOverrideDB(Base):
    """JSON-Override für Mandanten-LLM-Richtlinien (merged mit Standard-Policy)."""

    __tablename__ = "tenant_llm_policy_overrides"

    tenant_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    policy_json: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class AIActDocDB(Base):
    """EU-AI-Act-Technische-Dokumentation pro High-Risk-KI-System (mandantenisoliert)."""

    __tablename__ = "ai_act_docs"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "ai_system_id",
            "section_key",
            name="uq_ai_act_docs_tenant_system_section",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ai_system_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("ai_systems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_key: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False, default="")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    content_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    created_by: Mapped[str] = mapped_column(String(320), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    updated_by: Mapped[str] = mapped_column(String(320), nullable=False)


class ComplianceFrameworkDB(Base):
    """Regelwerks-Stammdaten (mandantenübergreifend)."""

    __tablename__ = "compliance_frameworks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class ComplianceRequirementDB(Base):
    """Norm-/Gesetzes-Pflichten je Framework (globaler Katalog)."""

    __tablename__ = "compliance_requirements"
    __table_args__ = (
        UniqueConstraint("framework_id", "code", name="uq_compliance_requirement_framework_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    framework_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("compliance_frameworks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirement_type: Mapped[str] = mapped_column(String(32), nullable=False)
    criticality: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")


class ComplianceRequirementRelationDB(Base):
    """Crosswalk: inhaltliche Zuordnung zwischen Pflichten verschiedener Frameworks."""

    __tablename__ = "compliance_requirement_relations"
    __table_args__ = (
        UniqueConstraint(
            "source_requirement_id",
            "target_requirement_id",
            name="uq_compliance_req_relation_pair",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_requirement_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("compliance_requirements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_requirement_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("compliance_requirements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    note: Mapped[str | None] = mapped_column(String(512), nullable=True)


class ComplianceControlDB(Base):
    """Mandantenspezifische Controls (Map once, comply many)."""

    __tablename__ = "compliance_controls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    control_type: Mapped[str] = mapped_column(String(32), nullable=False)
    owner_role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="planned")
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )


class ComplianceRequirementControlLinkDB(Base):
    """Verknüpfung Pflicht ↔ Control inkl. Deckungsgrad."""

    __tablename__ = "compliance_requirement_control_links"
    __table_args__ = (
        UniqueConstraint(
            "requirement_id",
            "control_id",
            name="uq_compliance_req_control_link",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    requirement_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("compliance_requirements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    control_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("compliance_controls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    coverage_level: Mapped[str] = mapped_column(String(16), nullable=False)


class ComplianceControlAISystemDB(Base):
    """Optional: Control wirkt auf konkrete KI-Systeme."""

    __tablename__ = "compliance_control_ai_systems"
    __table_args__ = (
        UniqueConstraint("control_id", "ai_system_id", name="uq_compliance_control_ai_system"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    control_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("compliance_controls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ai_system_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("ai_systems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


class ComplianceControlPolicyDB(Base):
    __tablename__ = "compliance_control_policies"
    __table_args__ = (
        UniqueConstraint("control_id", "policy_id", name="uq_compliance_control_policy"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    control_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("compliance_controls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    policy_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


class ComplianceControlActionDB(Base):
    __tablename__ = "compliance_control_actions"
    __table_args__ = (
        UniqueConstraint("control_id", "action_id", name="uq_compliance_control_action"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    control_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("compliance_controls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ai_governance_actions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


class LLMCallMetadataDB(Base):
    """Metadaten je LLM-Aufruf (ohne Prompt/Response-Inhalt, DSGVO-minimierend)."""

    __tablename__ = "llm_call_metadata"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_length: Mapped[int] = mapped_column(Integer, nullable=False)
    response_length: Mapped[int] = mapped_column(Integer, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )


class AiComplianceBoardReportDB(Base):
    """KI-generierter AI-Compliance-Board-Report (Coverage, Gaps, komprimierte Empfehlungen)."""

    __tablename__ = "ai_compliance_board_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    audience_type: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    rendered_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    rendered_html: Mapped[str | None] = mapped_column(Text, nullable=True)


class AiRuntimeEventTable(Base):
    """Laufzeit-/Monitoring-Events (SAP AI Core u. a.), mandanten- und systemisoliert."""

    __tablename__ = "ai_runtime_events"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "source",
            "source_event_id",
            name="uq_ai_runtime_events_tenant_source_event",
        ),
        Index(
            "ix_ai_runtime_events_tenant_system_occurred",
            "tenant_id",
            "ai_system_id",
            "occurred_at",
        ),
        Index(
            "ix_ai_runtime_events_tenant_system_type_occurred",
            "tenant_id",
            "ai_system_id",
            "event_type",
            "occurred_at",
        ),
        Index(
            "ix_ai_runtime_events_tenant_system_time",
            "tenant_id",
            "ai_system_id",
            "occurred_at",
            postgresql_ops={"occurred_at": "DESC"},
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ai_system_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("ai_systems.id", ondelete="CASCADE"),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_subtype: Mapped[str | None] = mapped_column(String(64), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    metric_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    incident_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold_breached: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    environment: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    extra: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class AiRuntimeIncidentSummaryTable(Base):
    """Aggregate Incidents pro System und Zeitfenster (Board / OAMI, optional materialisiert)."""

    __tablename__ = "ai_runtime_incident_summaries"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "ai_system_id",
            "window_start",
            "window_end",
            name="uq_ai_runtime_incident_summary_window",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ai_system_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("ai_systems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    incident_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    high_severity_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_incident_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    computed_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )


class TenantOperationalMonitoringSnapshotTable(Base):
    """Cache Tenant-OAMI für schnelle APIs (optional, durch Job oder on-read aktualisierbar)."""

    __tablename__ = "tenant_operational_monitoring_snapshots"
    __table_args__ = (UniqueConstraint("tenant_id", "window_days", name="uq_tenant_oami_window"),)

    tenant_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    window_days: Mapped[int] = mapped_column(Integer, primary_key=True)
    index_value: Mapped[int] = mapped_column(Integer, nullable=False)
    level: Mapped[str] = mapped_column(String(16), nullable=False)
    breakdown_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    computed_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )


class NIS2IncidentTable(Base):
    """NIS2 Art. 21 compliant incident response records — multi-tenant."""

    __tablename__ = "nis2_incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    incident_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    workflow_status: Mapped[str] = mapped_column(String(20), nullable=False, default="detected")
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    affected_systems_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    kritis_relevant: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    personal_data_affected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    estimated_impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    bsi_notification_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    bsi_report_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    final_report_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    contained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    eradicated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recovered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )


class ComplianceDeadlineTable(Base):
    """Regulatory compliance deadlines per tenant."""

    __tablename__ = "compliance_deadlines"
    __table_args__ = (
        Index("idx_compliance_deadlines_tenant_due_date", "tenant_id", "due_date"),
        Index(
            "uq_compliance_deadlines_tenant_source",
            "tenant_id",
            "source_type",
            "source_id",
            unique=True,
            sqlite_where=text("source_type IS NOT NULL AND source_id IS NOT NULL"),
            postgresql_where=text("source_type IS NOT NULL AND source_id IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    due_date: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    owner: Mapped[str | None] = mapped_column(String(320), nullable=True)
    regulation_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recurrence_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )


class UserDB(Base):
    """Registered user for identity & auth (DSGVO data-sparse)."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="de")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/Berlin")
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    email_verification_token: Mapped[str | None] = mapped_column(String(128), nullable=True)
    password_reset_token: Mapped[str | None] = mapped_column(String(128), nullable=True)
    password_reset_expires: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sso_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sso_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class UserTenantRoleDB(Base):
    """Tenant-specific role assignment for a user (M:N with composite key)."""

    __tablename__ = "user_tenant_roles"
    __table_args__ = (UniqueConstraint("user_id", "tenant_id", name="uq_user_tenant_role"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(64), nullable=False, default="viewer")
    assigned_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


# ── Enterprise IAM: Identity Providers, SCIM, Access Reviews ────────────────


class IdentityProviderDB(Base):
    """External Identity Provider configuration (SAML 2.0 / OIDC) per tenant."""

    __tablename__ = "identity_providers"
    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_idp_tenant_slug"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    protocol: Mapped[str] = mapped_column(String(16), nullable=False)  # "saml" | "oidc"
    issuer_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    metadata_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    client_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # attribute mapping stored as JSON: {"email": "...", "role": "...", "department": "..."}
    attribute_mapping: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_role: Mapped[str] = mapped_column(String(64), nullable=False, default="viewer")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class ExternalIdentityDB(Base):
    """Link between external IdP subject and local user."""

    __tablename__ = "external_identities"
    __table_args__ = (
        UniqueConstraint("provider_id", "external_subject", name="uq_ext_id_provider_subject"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    provider_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("identity_providers.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    external_subject: Mapped[str] = mapped_column(String(512), nullable=False)
    external_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    external_attributes: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class SCIMSyncStateDB(Base):
    """SCIM provisioning state per user+tenant (tracks sync lifecycle)."""

    __tablename__ = "scim_sync_state"
    __table_args__ = (UniqueConstraint("tenant_id", "user_id", name="uq_scim_sync_tenant_user"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    scim_external_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    provision_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active"
    )  # active | disabled | deprovisioned
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_source: Mapped[str | None] = mapped_column(String(128), nullable=True)  # e.g. "azure_ad"
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class AccessReviewDB(Base):
    """Access review / recertification for privileged roles."""

    __tablename__ = "access_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    target_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    target_role: Mapped[str] = mapped_column(String(64), nullable=False)
    reviewer_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )  # pending | approved | revoked | escalated
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    deadline_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


# ── Enterprise Governance: MFA, SoD, Approval Workflows, Privileged Actions ─


class MFAFactorDB(Base):
    """MFA factor enrollment (TOTP) per user."""

    __tablename__ = "mfa_factors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    factor_type: Mapped[str] = mapped_column(String(32), nullable=False, default="totp")  # totp
    secret_encrypted: Mapped[str] = mapped_column(String(512), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class MFABackupCodeDB(Base):
    """Single-use MFA backup code per user."""

    __tablename__ = "mfa_backup_codes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )


class SoDPolicyDB(Base):
    """Segregation of Duties policy rule — defines conflicting role pairs."""

    __tablename__ = "sod_policies"
    __table_args__ = (UniqueConstraint("tenant_id", "role_a", "role_b", name="uq_sod_policy_pair"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role_a: Mapped[str] = mapped_column(String(64), nullable=False)
    role_b: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(
        String(32), nullable=False, default="block"
    )  # block | warn
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class ApprovalRequestDB(Base):
    """Approval workflow request for sensitive operations (4-eye principle)."""

    __tablename__ = "approval_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    request_type: Mapped[str] = mapped_column(String(64), nullable=False)
    requester_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    target_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="requested"
    )  # requested | pending | approved | rejected | expired
    approver_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class PrivilegedActionEventDB(Base):
    """Audit log for privileged actions (governance-grade traceability)."""

    __tablename__ = "privileged_action_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    actor_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    step_up_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approval_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )


class ComplianceScoreDB(Base):
    """Aggregated compliance score snapshot per tenant (board-level KPI)."""

    __tablename__ = "compliance_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    score_type: Mapped[str] = mapped_column(String(64), nullable=False)  # overall | norm-specific
    norm: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )  # e.g. eu_ai_act, iso_42001
    score_value: Mapped[float] = mapped_column(Float, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    period: Mapped[str] = mapped_column(String(32), nullable=False)  # e.g. 2026-Q1
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )


class GapReportDB(Base):
    """Persisted gap analysis report per tenant (RAG-powered)."""

    __tablename__ = "gap_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )  # pending | running | completed | failed
    norm_scope: Mapped[str] = mapped_column(String(255), nullable=False)  # comma-separated norms
    gaps_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # structured JSON
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    llm_trace_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requested_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    completed_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class DatevExportLogDB(Base):
    """Audit trail for DATEV EXTF exports."""

    __tablename__ = "datev_export_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    export_type: Mapped[str] = mapped_column(String(64), nullable=False)  # extf_buchungen
    period_from: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    period_to: Mapped[str] = mapped_column(String(10), nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)  # SHA-256
    exported_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    step_up_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )


class NormEmbeddingDB(Base):
    """Chunked regulatory text with embedding vector (pgvector-ready, stores dim in JSON)."""

    __tablename__ = "norm_embeddings"
    __table_args__ = (
        UniqueConstraint("norm", "article_ref", "chunk_index", name="uq_norm_embedding_chunk"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    norm: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    article_ref: Mapped[str] = mapped_column(String(128), nullable=False)  # e.g. Art. 9 Abs. 2
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON float array
    embedding_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    valid_from: Mapped[str | None] = mapped_column(String(10), nullable=True)  # YYYY-MM-DD
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )


# ── Phase 4: PDF Reports & XRechnung Exports ─────────────────────────────────


class ReportExportDB(Base):
    """Audit log for generated PDF/A-3 board reports."""

    __tablename__ = "report_exports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    report_type: Mapped[str] = mapped_column(String(64), nullable=False)  # pdf_board_report
    format: Mapped[str] = mapped_column(String(32), nullable=False)  # html_pdfa3
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)  # SHA-256
    requested_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )


class XRechnungExportDB(Base):
    """Audit log for generated XRechnung 3.0 invoices."""

    __tablename__ = "xrechnung_exports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    invoice_id: Mapped[str] = mapped_column(String(128), nullable=False)
    buyer_reference: Mapped[str] = mapped_column(String(255), nullable=False)  # Leitweg-ID
    total_gross: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    validation_errors: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    exported_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )


# ── Phase 5: Tenant Onboarding & Subscription Billing ────────────────────────


class OnboardingStatusDB(Base):
    """Tracks onboarding wizard progress per tenant."""

    __tablename__ = "onboarding_status"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    total_steps: Mapped[int] = mapped_column(Integer, nullable=False, default=6)
    step_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class SubscriptionPlanDB(Base):
    """Available subscription plans."""

    __tablename__ = "subscription_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    max_users: Mapped[int | None] = mapped_column(Integer, nullable=True)
    features: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    price_monthly_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stripe_price_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )


class SubscriptionDB(Base):
    """Tenant subscription tracking."""

    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    plan_id: Mapped[str] = mapped_column(String(36), nullable=False)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="trialing")
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class BillingEventDB(Base):
    """Audit log for billing-related events."""

    __tablename__ = "billing_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    stripe_event_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )


class AuditAlertDB(Base):
    """NIS2 security alert generated from audit trail analysis."""

    __tablename__ = "audit_alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    audit_log_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )


# ---------------------------------------------------------------------------
# Trust Center & Assurance Portal
# ---------------------------------------------------------------------------


class TrustCenterAssetDB(Base):
    """Published document / artefact in the Trust Center / Assurance Portal."""

    __tablename__ = "trust_center_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    asset_type: Mapped[str] = mapped_column(String(64), nullable=False)
    sensitivity: Mapped[str] = mapped_column(String(32), nullable=False, default="customer")
    framework_refs: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    file_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )


class EvidenceBundleDB(Base):
    """Pre-assembled evidence bundle for due-diligence / audit."""

    __tablename__ = "evidence_bundles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    bundle_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    artefact_ids: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    metadata_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    sensitivity: Mapped[str] = mapped_column(String(32), nullable=False, default="auditor")
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    # E-Signing fields (Phase 11 – eIDAS / GoBD)
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    cert_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signed_by_role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Phase 12 – Key-Rotation-Safe Verification & Payload-Binding
    signing_key_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    signed_payload: Mapped[str | None] = mapped_column(Text, nullable=True)


class TrustCenterAccessLogDB(Base):
    """Immutable access log for trust center downloads and views."""

    __tablename__ = "trust_center_access_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

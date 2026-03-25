from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
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
    ai_act_scope: Mapped[str] = mapped_column(String(64), nullable=False, default="in_scope")
    created_at_utc: Mapped[datetime] = mapped_column(
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
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )


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

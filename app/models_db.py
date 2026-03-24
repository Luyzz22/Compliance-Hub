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

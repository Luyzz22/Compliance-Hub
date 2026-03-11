from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.ai_system_models import (
    AIActCategory,
    AISystemCriticality,
    AISystemRiskLevel,
    AISystemStatus,
    DataSensitivity,
)
from app.classification_models import ClassificationPath, RiskLevel
from app.compliance_gap_models import ComplianceStatus


class Base(DeclarativeBase):
    pass


class AISystemTable(Base):
    __tablename__ = "aisystems"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    business_unit: Mapped[str] = mapped_column(String(255))
    risk_level: Mapped[AISystemRiskLevel] = mapped_column(
        Enum(AISystemRiskLevel, name="aisystem_risk_level", native_enum=False)
    )
    ai_act_category: Mapped[AIActCategory] = mapped_column(
        Enum(AIActCategory, name="ai_act_category", native_enum=False)
    )
    gdpr_dpia_required: Mapped[bool] = mapped_column(Boolean)
    owner_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    criticality: Mapped[AISystemCriticality] = mapped_column(
        Enum(AISystemCriticality, name="aisystem_criticality", native_enum=False),
        nullable=False,
        default=AISystemCriticality.medium,
    )
    data_sensitivity: Mapped[DataSensitivity] = mapped_column(
        Enum(DataSensitivity, name="data_sensitivity", native_enum=False),
        nullable=False,
        default=DataSensitivity.internal,
    )
    status: Mapped[AISystemStatus] = mapped_column(
        Enum(AISystemStatus, name="aisystem_status", native_enum=False),
        default=AISystemStatus.draft,
    )
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AuditLogTable(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    before: Mapped[str | None] = mapped_column(Text, nullable=True)
    after: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PolicyTable(Base):
    __tablename__ = "policies"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class RuleTable(Base):
    __tablename__ = "rules"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    policy_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    condition_type: Mapped[str] = mapped_column(String(255), nullable=False)


class ViolationTable(Base):
    __tablename__ = "violations"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    ai_system_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    rule_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RiskClassificationTable(Base):
    __tablename__ = "risk_classifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    ai_system_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="risk_level_enum", native_enum=False), nullable=False
    )
    classification_path: Mapped[ClassificationPath] = mapped_column(
        Enum(ClassificationPath, name="classification_path_enum", native_enum=False), nullable=False
    )
    annex_iii_category: Mapped[int | None] = mapped_column(Integer, nullable=True)
    annex_i_legislation: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_safety_component: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_third_party_assessment: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    exception_applies: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    exception_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    profiles_natural_persons: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    classification_rationale: Mapped[str] = mapped_column(Text, nullable=False)
    classified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    classified_by: Mapped[str] = mapped_column(String(255), default="auto", nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)


class ComplianceStatusTable(Base):
    __tablename__ = "compliance_statuses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    ai_system_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    requirement_id: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[ComplianceStatus] = mapped_column(
        Enum(ComplianceStatus, name="compliance_status_enum", native_enum=False),
        default=ComplianceStatus.not_started,
        nullable=False,
    )
    evidence_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_by: Mapped[str] = mapped_column(String(255), default="system", nullable=False)


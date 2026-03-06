from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.ai_system_models import (
    AIActCategory,
    AISystemCriticality,
    AISystemRiskLevel,
    AISystemStatus,
    DataSensitivity,
)


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
    owner_email: Mapped[str] = mapped_column(String(320))
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



"""Add normalized DPIA/FRIA impact-assessment records."""

from __future__ import annotations

import logging

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    false,
)
from sqlalchemy.engine import Engine

from app.db_migrations.util import table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260503_ai_impact_assessments"
DISPLAY_NAME = "ai_impact_assessments"


def satisfied(engine: Engine) -> bool:
    return table_exists(engine, "ai_impact_assessments") and table_exists(
        engine, "ai_impact_assessment_sections"
    )


def apply(engine: Engine) -> bool:
    if satisfied(engine):
        return False
    metadata = MetaData()
    Table("ai_systems", metadata, Column("id", String(255), primary_key=True))
    assessments = Table(
        "ai_impact_assessments",
        metadata,
        Column("id", String(36), primary_key=True),
        Column("tenant_id", String(255), nullable=False),
        Column(
            "ai_system_id",
            String(255),
            ForeignKey("ai_systems.id", ondelete="CASCADE"),
            nullable=False,
        ),
        Column("dpia_scope", String(32), nullable=False, server_default="undetermined"),
        Column("fria_scope", String(32), nullable=False, server_default="undetermined"),
        Column("deployer_context", String(64), nullable=False, server_default="unknown"),
        Column("scope_rationale", Text),
        Column("lifecycle_status", String(32), nullable=False, server_default="draft"),
        Column("residual_risk", String(32), nullable=False, server_default="unknown"),
        Column("assessment_owner", String(255)),
        Column("independent_reviewer", String(255)),
        Column("dpo_involved", Boolean, nullable=False, server_default=false()),
        Column(
            "stakeholder_views_status",
            String(32),
            nullable=False,
            server_default="not_assessed",
        ),
        Column(
            "prior_consultation_status",
            String(32),
            nullable=False,
            server_default="not_assessed",
        ),
        Column("prior_consultation_reference", String(1024)),
        Column("reviewed_at_utc", DateTime(timezone=True)),
        Column("approved_at_utc", DateTime(timezone=True)),
        Column("review_due_at_utc", DateTime(timezone=True)),
        Column("version", Integer, nullable=False, server_default="1"),
        Column("created_at_utc", DateTime(timezone=True), nullable=False),
        Column("updated_at_utc", DateTime(timezone=True), nullable=False),
        Column("updated_by", String(255), nullable=False),
        UniqueConstraint(
            "tenant_id",
            "ai_system_id",
            name="uq_ai_impact_assessment_tenant_system",
        ),
    )
    Index(
        "ix_ai_impact_assessments_tenant_review_due",
        assessments.c.tenant_id,
        assessments.c.review_due_at_utc,
    )
    Index(
        "ix_ai_impact_assessments_tenant_lifecycle",
        assessments.c.tenant_id,
        assessments.c.lifecycle_status,
    )
    sections = Table(
        "ai_impact_assessment_sections",
        metadata,
        Column("id", String(36), primary_key=True),
        Column(
            "assessment_id",
            String(36),
            ForeignKey("ai_impact_assessments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        Column("tenant_id", String(255), nullable=False),
        Column("section_key", String(80), nullable=False),
        Column("status", String(32), nullable=False, server_default="not_started"),
        Column("summary", Text),
        Column("evidence_reference", String(1024)),
        Column("rationale", Text),
        Column("updated_at_utc", DateTime(timezone=True), nullable=False),
        UniqueConstraint(
            "assessment_id",
            "section_key",
            name="uq_ai_impact_assessment_section_key",
        ),
    )
    Index(
        "ix_ai_impact_assessment_sections_tenant_status",
        sections.c.tenant_id,
        sections.c.status,
    )
    with engine.begin() as connection:
        assessments.create(connection, checkfirst=True)
        sections.create(connection, checkfirst=True)
    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True

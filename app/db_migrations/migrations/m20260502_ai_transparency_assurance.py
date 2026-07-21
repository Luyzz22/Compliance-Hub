"""Add normalized Article 50 and GDPR transparency assurance records."""

from __future__ import annotations

import logging

from sqlalchemy import (
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
)
from sqlalchemy.engine import Engine

from app.db_migrations.util import table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260502_ai_transparency_assurance"
DISPLAY_NAME = "ai_transparency_assurance"


def satisfied(engine: Engine) -> bool:
    return table_exists(engine, "ai_transparency_assessments") and table_exists(
        engine, "ai_transparency_controls"
    )


def apply(engine: Engine) -> bool:
    if satisfied(engine):
        return False
    metadata = MetaData()
    Table("ai_systems", metadata, Column("id", String(255), primary_key=True))
    assessments = Table(
        "ai_transparency_assessments",
        metadata,
        Column("id", String(36), primary_key=True),
        Column("tenant_id", String(255), nullable=False),
        Column(
            "ai_system_id",
            String(255),
            ForeignKey("ai_systems.id", ondelete="CASCADE"),
            nullable=False,
        ),
        Column("role_scope", String(32), nullable=False, server_default="unknown"),
        Column("control_owner", String(255)),
        Column("reviewer", String(255)),
        Column("reviewed_at_utc", DateTime(timezone=True)),
        Column("review_due_at_utc", DateTime(timezone=True)),
        Column("version", Integer, nullable=False, server_default="1"),
        Column("created_at_utc", DateTime(timezone=True), nullable=False),
        Column("updated_at_utc", DateTime(timezone=True), nullable=False),
        Column("updated_by", String(255), nullable=False),
        UniqueConstraint(
            "tenant_id",
            "ai_system_id",
            name="uq_ai_transparency_assessment_tenant_system",
        ),
    )
    Index(
        "ix_ai_transparency_assessments_tenant_review_due",
        assessments.c.tenant_id,
        assessments.c.review_due_at_utc,
    )
    controls = Table(
        "ai_transparency_controls",
        metadata,
        Column("id", String(36), primary_key=True),
        Column(
            "assessment_id",
            String(36),
            ForeignKey("ai_transparency_assessments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        Column("tenant_id", String(255), nullable=False),
        Column("control_key", String(64), nullable=False),
        Column("status", String(32), nullable=False, server_default="not_assessed"),
        Column("evidence_reference", String(1024)),
        Column("rationale", Text),
        Column("updated_at_utc", DateTime(timezone=True), nullable=False),
        UniqueConstraint(
            "assessment_id",
            "control_key",
            name="uq_ai_transparency_control_assessment_key",
        ),
    )
    Index(
        "ix_ai_transparency_controls_tenant_status",
        controls.c.tenant_id,
        controls.c.status,
    )
    with engine.begin() as conn:
        assessments.create(conn, checkfirst=True)
        controls.create(conn, checkfirst=True)
    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True

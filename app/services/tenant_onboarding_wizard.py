"""Tenant onboarding wizard service – tracks multi-step onboarding progress."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models_db import OnboardingStatusDB

logger = logging.getLogger(__name__)

INDUSTRY_TEMPLATES: dict[str, dict] = {
    "automotive_manufacturing": {"norms": ["EU AI Act", "ISO 42001", "DSGVO", "GoBD"]},
    "financial_services": {"norms": ["NIS2", "DSGVO", "GoBD", "ISO 27001"]},
    "legal_tax_advisory": {"norms": ["DSGVO", "GoBD"]},
    "public_administration_kritis": {
        "norms": ["NIS2", "EU AI Act", "ISO 27001", "DSGVO", "KRITIS"]
    },
    "general": {"norms": ["DSGVO", "GoBD"]},
}


def _row_to_dict(row: OnboardingStatusDB) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "current_step": row.current_step,
        "total_steps": row.total_steps,
        "step_data": row.step_data,
        "completed": row.completed,
        "created_at_utc": row.created_at_utc.isoformat() if row.created_at_utc else None,
        "updated_at_utc": row.updated_at_utc.isoformat() if row.updated_at_utc else None,
    }


def get_onboarding_status(session: Session, tenant_id: str) -> dict | None:
    """Return current onboarding status for a tenant, or None if not started."""
    row = (
        session.query(OnboardingStatusDB)
        .filter(OnboardingStatusDB.tenant_id == tenant_id)
        .first()
    )
    if row is None:
        return None
    return _row_to_dict(row)


def update_onboarding_step(
    session: Session, tenant_id: str, step: int, step_data: dict
) -> dict:
    """Update onboarding progress; creates record if first call."""
    row = (
        session.query(OnboardingStatusDB)
        .filter(OnboardingStatusDB.tenant_id == tenant_id)
        .first()
    )
    if row is None:
        row = OnboardingStatusDB(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            current_step=step,
            total_steps=6,
            step_data=step_data,
            completed=False,
            created_at_utc=datetime.utcnow(),
            updated_at_utc=datetime.utcnow(),
        )
        session.add(row)
    else:
        row.current_step = step
        row.step_data = {**(row.step_data or {}), **step_data}
        row.updated_at_utc = datetime.utcnow()
    session.commit()
    session.refresh(row)
    logger.info("onboarding_step_updated tenant=%s step=%d", tenant_id, step)
    return _row_to_dict(row)


def complete_onboarding(session: Session, tenant_id: str) -> dict:
    """Mark onboarding as completed for a tenant."""
    row = (
        session.query(OnboardingStatusDB)
        .filter(OnboardingStatusDB.tenant_id == tenant_id)
        .first()
    )
    if row is None:
        row = OnboardingStatusDB(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            current_step=6,
            total_steps=6,
            step_data={},
            completed=True,
            created_at_utc=datetime.utcnow(),
            updated_at_utc=datetime.utcnow(),
        )
        session.add(row)
    else:
        row.completed = True
        row.current_step = row.total_steps
        row.updated_at_utc = datetime.utcnow()
    session.commit()
    session.refresh(row)
    logger.info("onboarding_completed tenant=%s", tenant_id)
    return _row_to_dict(row)

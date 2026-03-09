from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.ai_system_models import AIActCategory, AISystemCreate, AISystemRiskLevel, AISystemStatus
from app.models_db import AISystemTable, Base
from app.repositories.ai_systems import AISystemRepository


def _create_payload(system_id: str, *, name: str = "Fraud Model") -> AISystemCreate:
    return AISystemCreate(
        id=system_id,
        name=name,
        description="Detects fraudulent payment patterns",
        business_unit="Risk",
        risk_level=AISystemRiskLevel.high,
        ai_act_category=AIActCategory.high_risk,
        gdpr_dpia_required=True,
        owner_email="owner@example.com",
    )


def _build_repository() -> tuple[AISystemRepository, Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = factory()
    return AISystemRepository(session), session


def test_create_and_get_by_id_success() -> None:
    repository, session = _build_repository()

    created = repository.create("tenant-a", _create_payload("ai-1"))
    loaded = repository.get_by_id("tenant-a", "ai-1")

    assert loaded is not None
    assert created.id == "ai-1"
    assert loaded.id == "ai-1"
    assert loaded.tenant_id == "tenant-a"

    session.close()


def test_list_for_tenant_filters_by_tenant() -> None:
    repository, session = _build_repository()

    repository.create("tenant-a", _create_payload("ai-1", name="A"))
    repository.create("tenant-b", _create_payload("ai-2", name="B"))

    tenant_a_items = repository.list_for_tenant("tenant-a")

    assert len(tenant_a_items) == 1
    assert tenant_a_items[0].id == "ai-1"

    session.close()


def test_update_status_changes_only_status_and_updated_at() -> None:
    repository, session = _build_repository()

    repository.create("tenant-a", _create_payload("ai-1"))
    before_row = session.get(AISystemTable, "ai-1")
    assert before_row is not None
    old_updated_at = before_row.updated_at_utc
    old_created_at = before_row.created_at_utc
    old_name = before_row.name

    before_row.updated_at_utc = datetime.now(UTC) - timedelta(days=1)
    session.commit()

    updated = repository.update_status("tenant-a", "ai-1", AISystemStatus.active)
    after_row = session.get(AISystemTable, "ai-1")
    assert after_row is not None

    assert updated.status == AISystemStatus.active
    assert after_row.status == AISystemStatus.active
    assert after_row.updated_at_utc > old_updated_at
    assert after_row.created_at_utc == old_created_at
    assert after_row.name == old_name

    session.close()


def test_get_by_id_returns_none_for_wrong_tenant() -> None:
    repository, session = _build_repository()

    repository.create("tenant-a", _create_payload("ai-1"))

    loaded = repository.get_by_id("tenant-b", "ai-1")

    assert loaded is None

    session.close()

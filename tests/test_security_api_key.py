from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.ai_system_models import AIActCategory, AISystemCreate, AISystemRiskLevel
from app.main import app, get_ai_system_repository
from app.models_db import Base
from app.repositories.ai_systems import AISystemRepository
from app.security import get_settings


@pytest.fixture(autouse=True)
def _security_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("COMPLIANCEHUB_API_KEYS", "test-key-1,test-key-2")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client_and_repository() -> Iterator[tuple[TestClient, AISystemRepository]]:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    session = factory()
    repository = AISystemRepository(session)

    def _override_repository() -> AISystemRepository:
        return repository

    app.dependency_overrides[get_ai_system_repository] = _override_repository
    with TestClient(app) as client:
        yield client, repository

    app.dependency_overrides.clear()
    session.close()


def test_missing_api_key_returns_401(
    client_and_repository: tuple[TestClient, AISystemRepository],
) -> None:
    client, _ = client_and_repository

    response = client.get("/api/v1/ai-systems", headers={"x-tenant-id": "tenant-a"})

    assert response.status_code == 401


def test_missing_tenant_id_returns_400(
    client_and_repository: tuple[TestClient, AISystemRepository],
) -> None:
    client, _ = client_and_repository

    response = client.get("/api/v1/ai-systems", headers={"x-api-key": "test-key-1"})

    assert response.status_code == 400


def test_invalid_api_key_returns_401(
    client_and_repository: tuple[TestClient, AISystemRepository],
) -> None:
    client, _ = client_and_repository

    response = client.get(
        "/api/v1/ai-systems",
        headers={"x-api-key": "not-valid", "x-tenant-id": "tenant-a"},
    )

    assert response.status_code == 401


def test_valid_api_key_and_tenant_allows_access(
    client_and_repository: tuple[TestClient, AISystemRepository],
) -> None:
    client, repository = client_and_repository

    repository.create(
        "tenant-a",
        AISystemCreate(
            id="ai-1",
            name="Fraud Detection",
            description="Flags suspicious transactions",
            business_unit="Risk",
            risk_level=AISystemRiskLevel.high,
            ai_act_category=AIActCategory.high_risk,
            gdpr_dpia_required=True,
            owner_email="owner@example.com",
        ),
    )

    response = client.get(
        "/api/v1/ai-systems",
        headers={"x-api-key": "test-key-1", "x-tenant-id": "tenant-a"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == "ai-1"
    assert payload[0]["tenant_id"] == "tenant-a"

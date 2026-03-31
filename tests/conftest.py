from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import engine, get_session
from app.db_migrations import run_all_db_migrations
from app.main import app
from app.models_db import Base
from app.security import get_settings
from app.services.cross_regulation_seed import ensure_cross_regulation_catalog_seeded

# Alle API-Keys, die Tests in _headers() verwenden – get_settings().api_keys wird
# einmal pro Session gecacht; damit alle Tests grün bleiben, hier Superset setzen.
_TEST_API_KEYS = (
    "board-kpi-key,test-key,test-api-key,tenant-overview-key,test-key-1,test-key-2,demo-seed-key"
)
_DEMO_SEED_TENANTS = (
    "demo-seed-tenant-1,demo-seed-tenant-2,demo-isolation-a,demo-isolation-b,demo-direct-only,"
    "demo-domain-kpi-tenant,demo-domain-br-tenant,demo-smoke-e2e"
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db() -> None:
    os.environ["COMPLIANCEHUB_API_KEYS"] = _TEST_API_KEYS
    os.environ["COMPLIANCEHUB_EVIDENCE_DELETE_API_KEYS"] = _TEST_API_KEYS
    os.environ["COMPLIANCEHUB_DEMO_SEED_API_KEYS"] = "demo-seed-key"
    os.environ["COMPLIANCEHUB_DEMO_SEED_TENANT_IDS"] = _DEMO_SEED_TENANTS
    os.environ["COMPLIANCEHUB_ADMIN_API_KEYS"] = "provision-admin-test-key"
    get_settings.cache_clear()
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS schema_migrations"))
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    run_all_db_migrations(engine)
    with Session(engine) as s:
        ensure_cross_regulation_catalog_seeded(s)


@pytest.fixture(autouse=True)
def _restore_api_keys_superset() -> None:
    """Nach Tests, die COMPLIANCEHUB_API_KEYS verkleinern, wieder vollständige Key-Liste."""
    os.environ["COMPLIANCEHUB_API_KEYS"] = _TEST_API_KEYS
    os.environ["COMPLIANCEHUB_EVIDENCE_DELETE_API_KEYS"] = _TEST_API_KEYS
    os.environ["COMPLIANCEHUB_DEMO_SEED_API_KEYS"] = "demo-seed-key"
    os.environ["COMPLIANCEHUB_DEMO_SEED_TENANT_IDS"] = _DEMO_SEED_TENANTS
    os.environ["COMPLIANCEHUB_ADMIN_API_KEYS"] = "provision-admin-test-key"
    get_settings.cache_clear()


def _headers() -> dict[str, str]:
    """Standard-Test-Header (x-api-key, x-tenant-id) für geschützte Endpoints.
    Key muss in get_settings().api_keys liegen (kompatibel mit COMPLIANCEHUB_API_KEYS)."""
    return {
        "x-api-key": "board-kpi-key",
        "x-tenant-id": "board-kpi-tenant",
    }


@pytest.fixture(autouse=True)
def _override_session() -> Iterator[None]:
    app.dependency_overrides[get_session] = get_session
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _clear_ai_act_evidence_store() -> Iterator[None]:
    from app.services.rag.evidence_store import clear_for_tests

    clear_for_tests()
    yield
    clear_for_tests()

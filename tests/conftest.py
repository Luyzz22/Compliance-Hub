from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

from app.db import engine, get_session
from app.main import app
from app.models_db import Base
from app.security import get_settings

# Alle API-Keys, die Tests in _headers() verwenden – get_settings().api_keys wird
# einmal pro Session gecacht; damit alle Tests grün bleiben, hier Superset setzen.
_TEST_API_KEYS = "board-kpi-key,test-key,test-api-key,tenant-overview-key,test-key-1,test-key-2"


@pytest.fixture(scope="session", autouse=True)
def setup_test_db() -> None:
    os.environ["COMPLIANCEHUB_API_KEYS"] = _TEST_API_KEYS
    get_settings.cache_clear()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


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

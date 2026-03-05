from __future__ import annotations

from collections.abc import Iterator

import pytest

from app.db import engine, get_session
from app.main import app
from app.models_db import Base


@pytest.fixture(scope="session", autouse=True)
def setup_test_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def _override_session() -> Iterator[None]:
    app.dependency_overrides[get_session] = get_session
    yield
    app.dependency_overrides.clear()

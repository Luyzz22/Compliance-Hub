import pytest
from fastapi.testclient import TestClient  # type: ignore

from app.main import app


def test_fastapi_testclient_runtime_available() -> None:
    pytest.importorskip("httpx")

    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["region"] == "DACH"

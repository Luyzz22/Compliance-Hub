import pytest

try:
    import httpx  # noqa: F401
    from fastapi.testclient import TestClient
    from app.main import app
except ModuleNotFoundError:
    pytest.skip("fastapi/httpx not installed", allow_module_level=True)

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["product"] == "ComplianceHub"
    assert data["region"] == "DACH"

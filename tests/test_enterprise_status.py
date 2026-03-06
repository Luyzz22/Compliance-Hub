from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_enterprise_status_ok():
    response = client.get("/api/v1/enterprise/status")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert body["product"] == "ComplianceHub"
    assert body["region"] == "DACH"
    assert body["version"] == "0.1.0"
    assert body["environment"] == "dev"
    assert "document_intake" in body["features_enabled"]
    assert "ai_system_registry" in body["features_enabled"]
    assert "audit_logging" in body["features_enabled"]


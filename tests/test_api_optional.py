import pytest

try:
    import httpx  # noqa: F401
    from fastapi.testclient import TestClient

    from app.main import app
except ModuleNotFoundError:
    pytest.skip("fastapi/httpx not installed", allow_module_level=True)


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_intake_endpoint():
    payload = {
        "tenant_id": "tenant-1",
        "document_id": "doc-1",
        "document_type": "invoice",
        "supplier_name": "Supplier GmbH",
        "supplier_country": "DE",
        "contains_personal_data": True,
        "e_invoice_format": "xrechnung",
        "xml_valid_en16931": True,
        "amount_eur": 199.0,
    }

    response = client.post("/api/v1/documents/intake", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == payload["document_id"]
    assert body["accepted"] is True
    assert isinstance(body["actions"], list)
    assert body["audit_hash"]

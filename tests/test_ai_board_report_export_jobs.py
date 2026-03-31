"""Tests für Board-Report-Export-Jobs (POST/GET, Webhook optional, Tenant-Isolation)."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.board_report_export_jobs import _jobs
from tests.conftest import _headers

client = TestClient(app)


def _tenant_headers(tenant_id: str = "board-kpi-tenant") -> dict[str, str]:
    return {
        "x-api-key": "board-kpi-key",
        "x-tenant-id": tenant_id,
    }


def setup_ai_system(
    tenant_id: str = "board-kpi-tenant",
    system_id: str | None = None,
) -> None:
    """Legt ein AI-System an (eindeutige system_id pro Test wegen gemeinsamer DB)."""
    sid = system_id or "export-test-sys"
    client.post(
        "/api/v1/ai-systems",
        json={
            "id": sid,
            "name": "Export Test",
            "description": "Test",
            "business_unit": "Ops",
            "risk_level": "high",
            "ai_act_category": "high_risk",
            "gdpr_dpia_required": False,
            "owner_email": "",
            "criticality": "medium",
            "data_sensitivity": "internal",
            "has_incident_runbook": False,
            "has_supplier_risk_register": False,
            "has_backup_runbook": False,
        },
        headers=_tenant_headers(tenant_id),
    )


def test_create_export_job_no_webhook():
    """Happy Path: Job ohne externen Call (z.B. target_system=sap_btp)."""
    _jobs.clear()
    setup_ai_system(system_id="export-job-no-webhook")

    response = client.post(
        "/api/v1/ai-governance/report/board/export-jobs",
        json={"target_system": "sap_btp"},
        headers=_headers(),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["tenant_id"] == "board-kpi-tenant"
    assert data["status"] == "sent"
    assert data["target_system"] == "sap_btp"
    assert "id" in data
    assert "created_at" in data
    assert data.get("callback_url") is None


def test_create_export_job_generic_webhook_missing_callback():
    """generic_webhook ohne callback_url → 400."""
    response = client.post(
        "/api/v1/ai-governance/report/board/export-jobs",
        json={"target_system": "generic_webhook"},
        headers=_headers(),
    )
    assert response.status_code == 400
    assert "callback_url" in response.json().get("detail", "").lower()


def test_create_export_job_generic_webhook_success():
    """Happy Path mit generic_webhook: Mock HTTP POST, Job status sent."""
    _jobs.clear()
    setup_ai_system(system_id="export-job-webhook-ok")

    with patch(
        "app.services.board_report_export_jobs._post_webhook",
        return_value=(True, ""),
    ):
        response = client.post(
            "/api/v1/ai-governance/report/board/export-jobs",
            json={
                "target_system": "generic_webhook",
                "callback_url": "https://example.com/webhook",
            },
            headers=_headers(),
        )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "sent"
    assert data["target_system"] == "generic_webhook"
    assert data.get("callback_url") == "https://example.com/webhook"


def test_create_export_job_sap_btp_http_missing_callback():
    """sap_btp_http ohne callback_url → 400."""
    response = client.post(
        "/api/v1/ai-governance/report/board/export-jobs",
        json={"target_system": "sap_btp_http"},
        headers=_headers(),
    )
    assert response.status_code == 400
    assert "callback_url" in response.json().get("detail", "").lower()


def test_create_export_job_sap_btp_http_success():
    """Happy Path sap_btp_http: Header X-ComplianceHub-Integration + stabiles Payload-Schema."""
    _jobs.clear()
    setup_ai_system(system_id="export-job-sap-btp")

    captured_headers: dict[str, str] = {}
    captured_payload: dict = {}

    def fake_post_with_headers(
        url: str, payload: dict, headers: dict[str, str]
    ) -> tuple[bool, str]:
        captured_payload.update(payload)
        captured_headers.update(headers)
        return (True, "")

    with patch(
        "app.services.board_report_export_jobs._post_with_headers",
        side_effect=fake_post_with_headers,
    ):
        resp = client.post(
            "/api/v1/ai-governance/report/board/export-jobs",
            json={
                "target_system": "sap_btp_http",
                "callback_url": "https://btp.example.com/inbound",
            },
            headers=_headers(),
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "sent"
    assert data["target_system"] == "sap_btp_http"
    assert captured_headers.get("X-ComplianceHub-Integration") == "sap_btp_http"
    assert captured_payload.get("tenant_id") == "board-kpi-tenant"
    assert "report_period" in captured_payload
    assert "markdown" in captured_payload
    assert "report_metadata" in captured_payload
    assert "job_id" in (captured_payload.get("report_metadata") or {})


def test_create_export_job_dms_generic_not_implemented():
    """dms_generic führt nicht zu Fehlern, Job-Status not_implemented."""
    _jobs.clear()
    setup_ai_system(system_id="export-job-dms")

    response = client.post(
        "/api/v1/ai-governance/report/board/export-jobs",
        json={"target_system": "dms_generic"},
        headers=_headers(),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "not_implemented"
    assert data["target_system"] == "dms_generic"
    assert "not yet implemented" in (data.get("error_message") or "")


def test_create_export_job_datev_dms_prepared_missing_callback():
    """datev_dms_prepared ohne callback_url → 400."""
    response = client.post(
        "/api/v1/ai-governance/report/board/export-jobs",
        json={"target_system": "datev_dms_prepared"},
        headers=_headers(),
    )
    assert response.status_code == 400
    assert "callback_url" in response.json().get("detail", "").lower()


def test_create_export_job_datev_dms_prepared_payload_structure():
    """datev_dms_prepared: Payload hat mandant, bericht, content, technisch mit stabilen Keys."""
    _jobs.clear()
    setup_ai_system(system_id="export-job-datev")

    captured_payload: dict = {}
    captured_headers: dict = {}

    def fake_post(url: str, payload: dict, headers: dict) -> tuple[bool, str]:
        captured_payload.update(payload)
        captured_headers.update(headers)
        return (True, "")

    with patch(
        "app.services.board_report_export_jobs._post_with_headers",
        side_effect=fake_post,
    ):
        response = client.post(
            "/api/v1/ai-governance/report/board/export-jobs",
            json={
                "target_system": "datev_dms_prepared",
                "callback_url": "https://datev-dms.example.com/inbound",
                "metadata": {
                    "mandant_nr": "M-001",
                    "mandant_name": "Beispiel Kanzlei",
                    "aktenzeichen": "AI-GOV-2026-001",
                    "berichtszeitraum_von": "2025-01-01",
                    "berichtszeitraum_bis": "2026-01-01",
                    "normbezug": "EU AI Act,NIS2,ISO 42001",
                    "dokument_typ": "AI Governance Board Report",
                },
            },
            headers=_headers(),
        )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "sent"
    assert data["target_system"] == "datev_dms_prepared"
    assert captured_headers.get("X-ComplianceHub-Integration") == "datev_dms_prepared"

    assert "mandant" in captured_payload
    assert captured_payload["mandant"]["mandant_nr"] == "M-001"
    assert captured_payload["mandant"]["mandant_name"] == "Beispiel Kanzlei"
    assert captured_payload["mandant"]["aktenzeichen"] == "AI-GOV-2026-001"

    assert "bericht" in captured_payload
    assert captured_payload["bericht"]["typ"] == "AI Governance Board Report"
    assert "zeitraum" in captured_payload["bericht"]
    assert captured_payload["bericht"]["zeitraum"]["von"] == "2025-01-01"
    assert captured_payload["bericht"]["zeitraum"]["bis"] == "2026-01-01"
    assert "normbezug" in captured_payload["bericht"]
    assert "EU AI Act" in captured_payload["bericht"]["normbezug"]

    assert "content" in captured_payload
    assert "markdown" in captured_payload["content"]
    assert "summary" in captured_payload["content"]
    assert "ai_systems_total" in captured_payload["content"]["summary"]
    assert "risiko_level" in captured_payload["content"]["summary"]

    assert "technisch" in captured_payload
    assert captured_payload["technisch"]["tenant_id"] == "board-kpi-tenant"
    assert "export_job_id" in captured_payload["technisch"]


def test_create_export_job_webhook_failure():
    """Webhook schlägt fehl → Job status failed, error_message gesetzt."""
    _jobs.clear()
    setup_ai_system(system_id="export-job-webhook-fail")

    with patch(
        "app.services.board_report_export_jobs._post_webhook",
        return_value=(False, "Connection refused"),
    ):
        response = client.post(
            "/api/v1/ai-governance/report/board/export-jobs",
            json={
                "target_system": "generic_webhook",
                "callback_url": "https://example.com/webhook",
            },
            headers=_headers(),
        )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "failed"
    assert "Connection refused" in (data.get("error_message") or "")


def test_get_export_job_status():
    """GET liefert Job-Status nach Erstellung."""
    _jobs.clear()
    setup_ai_system(system_id="export-job-get-status")
    create = client.post(
        "/api/v1/ai-governance/report/board/export-jobs",
        json={"target_system": "sharepoint"},
        headers=_headers(),
    )
    assert create.status_code == 201
    job_id = create.json()["id"]

    get_resp = client.get(
        f"/api/v1/ai-governance/report/board/export-jobs/{job_id}",
        headers=_headers(),
    )
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["id"] == job_id
    assert data["tenant_id"] == "board-kpi-tenant"
    assert data["status"] == "sent"


def test_get_export_job_404_unknown():
    """GET mit unbekannter job_id → 404."""
    response = client.get(
        "/api/v1/ai-governance/report/board/export-jobs/00000000-0000-0000-0000-000000000000",
        headers=_headers(),
    )
    assert response.status_code == 404


def test_export_job_tenant_isolation():
    """Job mit Tenant A erstellt, GET mit Tenant B → 404."""
    _jobs.clear()
    setup_ai_system("tenant-export-a", system_id="export-job-tenant-a")
    create = client.post(
        "/api/v1/ai-governance/report/board/export-jobs",
        json={"target_system": "sap_btp"},
        headers=_tenant_headers("tenant-export-a"),
    )
    assert create.status_code == 201
    job_id = create.json()["id"]

    get_b = client.get(
        f"/api/v1/ai-governance/report/board/export-jobs/{job_id}",
        headers=_tenant_headers("tenant-export-b"),
    )
    assert get_b.status_code == 404


def test_export_job_401_no_api_key():
    """POST ohne gültigen API-Key → 401."""
    response = client.post(
        "/api/v1/ai-governance/report/board/export-jobs",
        json={"target_system": "sap_btp"},
        headers={"x-tenant-id": "board-kpi-tenant"},
    )
    assert response.status_code == 401


def test_export_job_401_invalid_api_key():
    """POST mit ungültigem API-Key → 401."""
    response = client.post(
        "/api/v1/ai-governance/report/board/export-jobs",
        json={"target_system": "sap_btp"},
        headers={"x-api-key": "invalid-key", "x-tenant-id": "board-kpi-tenant"},
    )
    assert response.status_code == 401


def test_export_payload_example_sap_btp_http():
    """[DEV/Docs] GET export-payload-example liefert Beispiel-Payload für sap_btp_http."""
    response = client.get(
        "/api/v1/ai-governance/report/board/export-payload-example?target_system=sap_btp_http",
        headers=_headers(),
    )
    # In Tests ist ENV typisch nicht production → 200
    if response.status_code == 404:
        return  # Production-ähnliche Umgebung
    assert response.status_code == 200
    data = response.json()
    assert data.get("tenant_id") == "example-tenant-001"
    assert data.get("report_period") == "last_12_months"
    assert "markdown" in data
    assert "report_metadata" in data
    assert "job_id" in data["report_metadata"]

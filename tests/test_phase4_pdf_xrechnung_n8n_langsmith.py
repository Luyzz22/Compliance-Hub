"""Phase 4 tests: PDF/A-3 Report, XRechnung 3.0, n8n Webhooks, LangSmith Tracing.

Covers:
- Unit: PDF rendering, XRechnung validation, HMAC signature, LangSmith metrics
- Integration: Report download, XRechnung export, n8n webhook, LangSmith tracing
- Negative: Access without role blocked, invalid XRechnung rejected
"""

from __future__ import annotations

import json
import os
from datetime import date
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.rbac.permissions import Permission, has_permission
from app.rbac.roles import EnterpriseRole
from tests.conftest import _headers

client = TestClient(app)

_TENANT = "board-kpi-tenant"


def _admin_headers() -> dict[str, str]:
    return {**_headers(), "x-opa-user-role": "tenant_admin"}


def _ciso_headers() -> dict[str, str]:
    return {**_headers(), "x-opa-user-role": "ciso"}


def _board_headers() -> dict[str, str]:
    return {**_headers(), "x-opa-user-role": "board_member"}


def _compliance_admin_headers() -> dict[str, str]:
    return {**_headers(), "x-opa-user-role": "compliance_admin"}


def _viewer_headers() -> dict[str, str]:
    return {**_headers(), "x-opa-user-role": "viewer"}


# ── RBAC Permission Tests ───────────────────────────────────────────────────


class TestPhase4Permissions:
    def test_board_member_can_generate_pdf_report(self):
        assert has_permission(EnterpriseRole.BOARD_MEMBER, Permission.GENERATE_PDF_REPORT)

    def test_ciso_can_generate_pdf_report(self):
        assert has_permission(EnterpriseRole.CISO, Permission.GENERATE_PDF_REPORT)

    def test_tenant_admin_can_generate_pdf_report(self):
        assert has_permission(EnterpriseRole.TENANT_ADMIN, Permission.GENERATE_PDF_REPORT)

    def test_compliance_admin_can_export_xrechnung(self):
        assert has_permission(EnterpriseRole.COMPLIANCE_ADMIN, Permission.EXPORT_XRECHNUNG)

    def test_tenant_admin_can_export_xrechnung(self):
        assert has_permission(EnterpriseRole.TENANT_ADMIN, Permission.EXPORT_XRECHNUNG)

    def test_tenant_admin_can_manage_n8n(self):
        assert has_permission(EnterpriseRole.TENANT_ADMIN, Permission.MANAGE_N8N_WEBHOOKS)

    def test_compliance_admin_can_manage_n8n(self):
        assert has_permission(EnterpriseRole.COMPLIANCE_ADMIN, Permission.MANAGE_N8N_WEBHOOKS)

    def test_viewer_cannot_generate_pdf(self):
        assert not has_permission(EnterpriseRole.VIEWER, Permission.GENERATE_PDF_REPORT)

    def test_viewer_cannot_export_xrechnung(self):
        assert not has_permission(EnterpriseRole.VIEWER, Permission.EXPORT_XRECHNUNG)

    def test_viewer_cannot_manage_n8n(self):
        assert not has_permission(EnterpriseRole.VIEWER, Permission.MANAGE_N8N_WEBHOOKS)

    def test_board_member_cannot_export_xrechnung(self):
        assert not has_permission(EnterpriseRole.BOARD_MEMBER, Permission.EXPORT_XRECHNUNG)


# ── PDF/A-3 Report Unit Tests ───────────────────────────────────────────────


class TestPdfReportGenerator:
    def test_render_traffic_light_green(self):
        from app.services.pdf_report_generator import _render_traffic_light

        assert _render_traffic_light(80.0) == "🟢"

    def test_render_traffic_light_amber(self):
        from app.services.pdf_report_generator import _render_traffic_light

        assert _render_traffic_light(60.0) == "🟡"

    def test_render_traffic_light_red(self):
        from app.services.pdf_report_generator import _render_traffic_light

        assert _render_traffic_light(30.0) == "🔴"

    def test_render_traffic_light_boundary_75(self):
        from app.services.pdf_report_generator import _render_traffic_light

        assert _render_traffic_light(75.0) == "🟢"

    def test_render_traffic_light_boundary_50(self):
        from app.services.pdf_report_generator import _render_traffic_light

        assert _render_traffic_light(50.0) == "🟡"

    def test_build_heatmap_html(self):
        from app.services.pdf_report_generator import _build_heatmap_html

        data = [
            {"norm": "NIS2", "severity": "critical", "count": 3},
            {"norm": "NIS2", "severity": "high", "count": 5},
            {"norm": "DSGVO", "severity": "medium", "count": 2},
        ]
        html = _build_heatmap_html(data)
        assert "NIS2" in html
        assert "DSGVO" in html
        assert "heatmap-table" in html

    def test_generate_board_pdf_report_returns_bytes(self):
        from app.services.pdf_report_generator import generate_board_pdf_report

        kpi_data = {
            "tenant_name": "Test Tenant",
            "reporting_period": "2026-04",
            "overall_score": 72.5,
            "norm_scores": [],
            "critical_findings": [],
            "incidents": {"nis2": {"total": 5, "open": 2, "resolved": 3}},
            "deadlines": [
                {
                    "regulation": "EU AI Act",
                    "deadline": "2026-08-01",
                    "description": "High-risk classification deadline",
                }
            ],
        }
        result = generate_board_pdf_report(kpi_data, "test-tenant")
        assert isinstance(result, bytes)
        text = result.decode("utf-8")
        assert "Compliance Board Report" in text
        assert "Test Tenant" in text
        assert "72.5%" in text
        assert "🟡" in text  # amber for 72.5
        assert "pdfa:part" in text
        assert "EU AI Act" in text
        assert "CISO" in text
        assert "Geschäftsführer" in text

    def test_generate_board_pdf_report_empty_data(self):
        from app.services.pdf_report_generator import generate_board_pdf_report

        result = generate_board_pdf_report({}, "empty-tenant")
        assert isinstance(result, bytes)
        text = result.decode("utf-8")
        assert "Compliance Board Report" in text
        assert "🔴" in text  # red for 0.0


# ── XRechnung Unit Tests ───────────────────────────────────────────────────


class TestXRechnungExport:
    def _sample_invoice(self):
        from app.services.xrechnung_export import XRechnungInvoice

        return XRechnungInvoice(
            invoice_id="INV-2026-001",
            issue_date=date(2026, 4, 1),
            due_date=date(2026, 5, 1),
            seller_name="ComplianceHub GmbH",
            seller_tax_id="DE123456789",
            seller_address="Musterstraße 1, 10115 Berlin",
            buyer_name="Bundesministerium für Digitales",
            buyer_reference="04011000-12345-67",
            buyer_address="Kapelle-Ufer 1, 10117 Berlin",
            line_items=[
                {
                    "description": "GRC-Beratung Q1 2026",
                    "quantity": 40,
                    "unit_price": 250.00,
                    "tax_percent": 19,
                },
                {
                    "description": "ISO 42001 Zertifizierung",
                    "quantity": 1,
                    "unit_price": 5000.00,
                    "tax_percent": 19,
                },
            ],
        )

    def test_generate_xrechnung_xml_valid(self):
        from app.services.xrechnung_export import generate_xrechnung_xml, validate_xrechnung

        invoice = self._sample_invoice()
        xml = generate_xrechnung_xml(invoice)
        errors = validate_xrechnung(xml)
        assert errors == [], f"Validation errors: {errors}"

    def test_xrechnung_contains_required_elements(self):
        from app.services.xrechnung_export import (
            XRECHNUNG_CUSTOMIZATION_ID,
            XRECHNUNG_PROFILE_ID,
            generate_xrechnung_xml,
        )

        invoice = self._sample_invoice()
        xml = generate_xrechnung_xml(invoice)
        assert XRECHNUNG_CUSTOMIZATION_ID in xml
        assert XRECHNUNG_PROFILE_ID in xml
        assert "INV-2026-001" in xml
        assert "ComplianceHub GmbH" in xml
        assert "04011000-12345-67" in xml
        assert "380" in xml  # InvoiceTypeCode

    def test_xrechnung_tax_calculation(self):
        from app.services.xrechnung_export import generate_xrechnung_xml

        invoice = self._sample_invoice()
        xml = generate_xrechnung_xml(invoice)
        # 40*250=10000 + 1*5000=5000 = 15000 net, 15000*0.19=2850 tax
        assert "15000.00" in xml  # net
        assert "2850.00" in xml  # tax
        assert "17850.00" in xml  # gross

    def test_validate_xrechnung_invalid_xml(self):
        from app.services.xrechnung_export import validate_xrechnung

        errors = validate_xrechnung("<invalid>xml</not-closed>")
        assert len(errors) > 0
        assert any("parse error" in e.lower() for e in errors)

    def test_validate_xrechnung_missing_elements(self):
        from app.services.xrechnung_export import validate_xrechnung

        xml = (
            '<?xml version="1.0"?>'
            '<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">'
            "</Invoice>"
        )
        errors = validate_xrechnung(xml)
        assert len(errors) > 0
        assert any("Missing" in e for e in errors)


# ── n8n Webhook Unit Tests ──────────────────────────────────────────────────


class TestN8nWebhookService:
    def test_compute_hmac_signature(self):
        from app.services.n8n_webhook_service import compute_hmac_signature

        sig = compute_hmac_signature(b'{"test": true}', "secret-key")
        assert isinstance(sig, str)
        assert len(sig) == 64  # SHA-256 hex digest

    def test_verify_hmac_signature_valid(self):
        from app.services.n8n_webhook_service import (
            compute_hmac_signature,
            verify_hmac_signature,
        )

        payload = b'{"event": "test"}'
        secret = "my-secret"
        sig = compute_hmac_signature(payload, secret)
        assert verify_hmac_signature(payload, secret, sig)

    def test_verify_hmac_signature_invalid(self):
        from app.services.n8n_webhook_service import verify_hmac_signature

        assert not verify_hmac_signature(b"payload", "secret", "invalid-sig")

    def test_build_webhook_payload_structure(self):
        from app.services.n8n_webhook_service import build_webhook_payload

        payload = build_webhook_payload("test_event", "tenant-1", {"key": "value"})
        assert payload["event_type"] == "test_event"
        assert payload["tenant_id"] == "tenant-1"
        assert "timestamp" in payload
        assert "correlation_id" in payload
        assert payload["data"] == {"key": "value"}

    def test_n8n_workflow_type_enum(self):
        from app.services.n8n_webhook_service import N8nWorkflowType

        assert N8nWorkflowType.monthly_board_report == "monthly_board_report"
        assert N8nWorkflowType.datev_monthly_export == "datev_monthly_export"
        assert N8nWorkflowType.deadline_reminder == "deadline_reminder"
        assert N8nWorkflowType.gap_analysis_trigger == "gap_analysis_trigger"
        assert N8nWorkflowType.access_review_reminder == "access_review_reminder"


# ── LangSmith Tracing Unit Tests ───────────────────────────────────────────


class TestLangSmithTracing:
    def test_configure_langsmith_not_configured(self):
        from app.services.langsmith_tracing import configure_langsmith

        os.environ.pop("LANGSMITH_API_KEY", None)
        os.environ.pop("LANGSMITH_PROJECT", None)
        assert configure_langsmith() is False

    def test_configure_langsmith_configured(self):
        from app.services.langsmith_tracing import configure_langsmith

        with patch.dict(os.environ, {
            "LANGSMITH_API_KEY": "test-key",
            "LANGSMITH_PROJECT": "test-project",
        }):
            assert configure_langsmith() is True

    def test_create_run_returns_none_when_not_configured(self):
        from app.services.langsmith_tracing import create_langsmith_run

        os.environ.pop("LANGSMITH_API_KEY", None)
        result = create_langsmith_run("test-run")
        assert result is None

    def test_create_and_end_run_when_configured(self):
        from app.services.langsmith_tracing import (
            _trace_store,
            create_langsmith_run,
            end_langsmith_run,
        )

        with patch.dict(os.environ, {"LANGSMITH_API_KEY": "test-key"}):
            run_id = create_langsmith_run(
                "test-analysis",
                inputs={"norms": ["eu_ai_act"]},
                metadata={"model": "test-model"},
            )
            assert run_id is not None
            assert run_id in _trace_store

            end_langsmith_run(run_id, outputs={"success": True})
            assert _trace_store[run_id]["outputs"] == {"success": True}
            assert _trace_store[run_id]["end_time"] is not None

    def test_trace_gap_analysis_returns_metrics(self):
        from app.services.langsmith_tracing import trace_gap_analysis

        metrics = trace_gap_analysis(
            tenant_id="test-tenant",
            norms=["eu_ai_act", "nis2"],
            latency_ms=1500.0,
            token_estimate=2000,
            model="claude-sonnet-4-20250514",
            success=True,
        )
        assert metrics["event"] == "gap_analysis"
        assert metrics["tenant_id"] == "test-tenant"
        assert metrics["latency_ms"] == 1500.0
        assert metrics["success"] is True

    def test_langsmith_metrics_dataclass(self):
        from app.services.langsmith_tracing import LangSmithMetrics

        m = LangSmithMetrics(
            latency_ms=500.0,
            token_estimate=1000,
            model="gpt-4",
            prompt_version="v2",
            success=True,
        )
        assert m.latency_ms == 500.0
        assert m.model == "gpt-4"
        assert m.error_message == ""


# ── Integration Tests: API Endpoints ────────────────────────────────────────


class TestPdfReportEndpoint:
    def test_pdf_report_download_as_admin(self):
        resp = client.get(
            "/api/v1/enterprise/board/pdf-report",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert resp.headers.get("X-PDFA-Version") == "3"
        assert resp.headers.get("X-PDFA-Conformance") == "B"
        assert "X-Checksum-SHA256" in resp.headers
        assert "Compliance Board Report" in resp.text

    def test_pdf_report_download_as_board_member(self):
        resp = client.get(
            "/api/v1/enterprise/board/pdf-report",
            headers=_board_headers(),
        )
        assert resp.status_code == 200

    def test_pdf_report_download_as_ciso(self):
        resp = client.get(
            "/api/v1/enterprise/board/pdf-report",
            headers=_ciso_headers(),
        )
        assert resp.status_code == 200

    def test_pdf_report_blocked_for_viewer(self):
        resp = client.get(
            "/api/v1/enterprise/board/pdf-report",
            headers=_viewer_headers(),
        )
        assert resp.status_code == 403


class TestXRechnungEndpoint:
    def _valid_body(self):
        return {
            "invoice_id": "INV-2026-001",
            "issue_date": "2026-04-01",
            "due_date": "2026-05-01",
            "seller_name": "ComplianceHub GmbH",
            "seller_tax_id": "DE123456789",
            "seller_address": "Musterstraße 1, Berlin",
            "buyer_name": "Bundesministerium",
            "buyer_reference": "04011000-12345-67",
            "line_items": [
                {
                    "description": "GRC Beratung",
                    "quantity": 10,
                    "unit_price": 200.0,
                    "tax_percent": 19.0,
                }
            ],
        }

    def test_xrechnung_export_as_admin(self):
        resp = client.post(
            "/api/v1/enterprise/xrechnung/export",
            json=self._valid_body(),
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        assert "application/xml" in resp.headers["content-type"]
        assert "XRechnung" in resp.headers.get("content-disposition", "")

    def test_xrechnung_export_as_compliance_admin(self):
        resp = client.post(
            "/api/v1/enterprise/xrechnung/export",
            json=self._valid_body(),
            headers=_compliance_admin_headers(),
        )
        assert resp.status_code == 200

    def test_xrechnung_blocked_for_viewer(self):
        resp = client.post(
            "/api/v1/enterprise/xrechnung/export",
            json=self._valid_body(),
            headers=_viewer_headers(),
        )
        assert resp.status_code == 403

    def test_xrechnung_blocked_for_board_member(self):
        resp = client.post(
            "/api/v1/enterprise/xrechnung/export",
            json=self._valid_body(),
            headers=_board_headers(),
        )
        assert resp.status_code == 403

    def test_xrechnung_xml_validates(self):
        resp = client.post(
            "/api/v1/enterprise/xrechnung/export",
            json=self._valid_body(),
            headers=_admin_headers(),
        )
        assert resp.status_code == 200

        from app.services.xrechnung_export import validate_xrechnung

        errors = validate_xrechnung(resp.text)
        assert errors == []


class TestN8nWebhookEndpoint:
    def test_webhook_receive_as_admin(self):
        resp = client.post(
            "/api/v1/enterprise/n8n/webhook",
            json={"event_type": "test_event", "data": {"key": "value"}},
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "accepted"
        assert "correlation_id" in body

    def test_webhook_blocked_for_viewer(self):
        resp = client.post(
            "/api/v1/enterprise/n8n/webhook",
            json={"event_type": "test"},
            headers=_viewer_headers(),
        )
        assert resp.status_code == 403


# ── Migration Tests ─────────────────────────────────────────────────────────


class TestPhase4Migration:
    def test_migration_file_exists(self):
        from app.db_migrations.migrations import m20260414_phase4_pdf_xrechnung as m

        assert m.MIGRATION_ID == "20260414_phase4_pdf_xrechnung"

    def test_migration_satisfied_after_setup(self):
        from app.db import engine
        from app.db_migrations.migrations import m20260414_phase4_pdf_xrechnung as m

        assert m.satisfied(engine)


# ── n8n Workflow JSON Tests ─────────────────────────────────────────────────


class TestN8nWorkflowJsons:
    def test_workflow_files_exist_and_valid_json(self):
        import pathlib

        workflow_dir = pathlib.Path(
            "/home/runner/work/Compliance-Hub/Compliance-Hub/infra/n8n/workflows"
        )
        expected = [
            "monthly_board_pdf_report.json",
            "datev_monthly_export.json",
            "deadline_reminder.json",
            "gap_analysis_trigger.json",
            "access_review_reminder.json",
        ]
        for name in expected:
            path = workflow_dir / name
            assert path.exists(), f"Workflow file missing: {name}"
            data = json.loads(path.read_text())
            assert "name" in data
            assert "nodes" in data
            assert "connections" in data


# ── LangSmith Ground Truth Dataset ─────────────────────────────────────────


class TestLangSmithGroundTruth:
    def test_ground_truth_dataset_valid(self):
        import pathlib

        path = pathlib.Path(
            "/home/runner/work/Compliance-Hub/Compliance-Hub/data/langsmith/"
            "gap_analysis_ground_truth.json"
        )
        assert path.exists()
        data = json.loads(path.read_text())
        assert len(data["entries"]) >= 10
        for entry in data["entries"]:
            assert "norm" in entry
            assert "article_ref" in entry
            assert "expected_gaps" in entry
            assert "expected_severity" in entry

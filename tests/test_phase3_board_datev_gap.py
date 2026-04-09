"""Phase 3 tests: Board KPI, DATEV EXTF export, RAG ingestion, Gap Analysis.

Covers:
- Unit: KPI calculation, DATEV validation/format, gap prioritization, chunking
- Integration: Report endpoints, export flow, RAG pipeline
- Negative: Access without role blocked, RBAC enforcement
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import engine
from app.main import app
from app.models_db import ComplianceScoreDB, DatevExportLogDB
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


def _viewer_headers() -> dict[str, str]:
    return {**_headers(), "x-opa-user-role": "viewer"}


# ── RBAC permission tests ────────────────────────────────────────────────────


class TestPhase3Permissions:
    def test_board_member_has_executive_dashboard(self):
        assert has_permission(EnterpriseRole.BOARD_MEMBER, Permission.VIEW_EXECUTIVE_DASHBOARD)

    def test_board_member_has_view_gap_reports(self):
        assert has_permission(EnterpriseRole.BOARD_MEMBER, Permission.VIEW_GAP_REPORTS)

    def test_board_member_cannot_export_datev(self):
        assert not has_permission(EnterpriseRole.BOARD_MEMBER, Permission.EXPORT_DATEV)

    def test_board_member_cannot_run_gap_analysis(self):
        assert not has_permission(EnterpriseRole.BOARD_MEMBER, Permission.RUN_GAP_ANALYSIS)

    def test_ciso_has_executive_dashboard(self):
        assert has_permission(EnterpriseRole.CISO, Permission.VIEW_EXECUTIVE_DASHBOARD)

    def test_ciso_has_gap_analysis(self):
        assert has_permission(EnterpriseRole.CISO, Permission.RUN_GAP_ANALYSIS)

    def test_ciso_cannot_export_datev(self):
        assert not has_permission(EnterpriseRole.CISO, Permission.EXPORT_DATEV)

    def test_tenant_admin_has_all_phase3_perms(self):
        for p in [
            Permission.VIEW_EXECUTIVE_DASHBOARD,
            Permission.VIEW_GAP_REPORTS,
            Permission.RUN_GAP_ANALYSIS,
            Permission.EXPORT_DATEV,
        ]:
            assert has_permission(EnterpriseRole.TENANT_ADMIN, p), f"TENANT_ADMIN missing {p}"

    def test_compliance_admin_has_all_phase3_perms(self):
        for p in [
            Permission.VIEW_EXECUTIVE_DASHBOARD,
            Permission.VIEW_GAP_REPORTS,
            Permission.RUN_GAP_ANALYSIS,
            Permission.EXPORT_DATEV,
        ]:
            assert has_permission(EnterpriseRole.COMPLIANCE_ADMIN, p), (
                f"COMPLIANCE_ADMIN missing {p}"
            )

    def test_viewer_cannot_access_phase3(self):
        for p in [
            Permission.VIEW_EXECUTIVE_DASHBOARD,
            Permission.VIEW_GAP_REPORTS,
            Permission.RUN_GAP_ANALYSIS,
            Permission.EXPORT_DATEV,
        ]:
            assert not has_permission(EnterpriseRole.VIEWER, p), f"VIEWER should not have {p}"


# ── KPI Calculation unit tests ───────────────────────────────────────────────


class TestBoardKpiCalculation:
    def test_compute_overall_compliance_score_empty(self):
        from app.services.board_kpi_aggregation import compute_overall_compliance_score

        with Session(engine) as s:
            result = compute_overall_compliance_score(s, "nonexistent-tenant")
        assert result["overall_score"] == 0.0
        assert len(result["norm_scores"]) == 4

    def test_compute_overall_compliance_score_with_data(self):
        from datetime import UTC, datetime

        from app.services.board_kpi_aggregation import compute_overall_compliance_score

        tid = f"kpi-test-{uuid.uuid4().hex[:8]}"
        with Session(engine) as s:
            norm_vals = [
                ("eu_ai_act", 80.0),
                ("iso_42001", 60.0),
                ("nis2", 70.0),
                ("dsgvo", 90.0),
            ]
            for norm, val in norm_vals:
                s.add(
                    ComplianceScoreDB(
                        id=str(uuid.uuid4()),
                        tenant_id=tid,
                        score_type="norm",
                        norm=norm,
                        score_value=val,
                        weight=1.0,
                        period="2026-Q1",
                        created_at_utc=datetime.now(UTC),
                    )
                )
            s.commit()
            result = compute_overall_compliance_score(s, tid)

        # Weighted: 80*0.3 + 60*0.2 + 70*0.25 + 90*0.25 = 24+12+17.5+22.5 = 76.0
        assert result["overall_score"] == 76.0

    def test_count_high_risk_ai_systems(self):
        from app.services.board_kpi_aggregation import count_high_risk_ai_systems

        with Session(engine) as s:
            count = count_high_risk_ai_systems(s, "nonexistent-tenant")
        assert count == 0

    def test_incident_statistics_empty(self):
        from app.services.board_kpi_aggregation import get_incident_statistics

        with Session(engine) as s:
            stats = get_incident_statistics(s, "nonexistent-tenant")
        assert stats["total"] == 0
        assert stats["open"] == 0

    def test_build_board_kpi_report_structure(self):
        from app.services.board_kpi_aggregation import build_board_kpi_report

        with Session(engine) as s:
            report = build_board_kpi_report(s, _TENANT)
        assert "compliance_score" in report
        assert "high_risk_ai_systems" in report
        assert "incident_statistics" in report
        assert "trend_data" in report
        assert "upcoming_deadlines" in report
        assert report["tenant_id"] == _TENANT
        assert len(report["upcoming_deadlines"]) >= 1


# ── DATEV EXTF Validation unit tests ────────────────────────────────────────


class TestDatevExtfValidation:
    def test_validate_records_empty(self):
        from app.services.datev_extf_export import validate_records

        assert validate_records([]) == []

    def test_validate_records_valid(self):
        from app.services.datev_extf_export import DatevBookingRecord, validate_records

        records = [
            DatevBookingRecord(
                umsatz=1500.00,
                soll_haben="S",
                konto=6880,
                gegenkonto=1200,
                belegdatum="1503",
                buchungstext="BSI Bussgeld 2026-Q1",
                beleg1="FINE-001",
                booking_type="bussgeld",
            )
        ]
        assert validate_records(records) == []

    def test_validate_records_negative_umsatz(self):
        from app.services.datev_extf_export import DatevBookingRecord, validate_records

        records = [
            DatevBookingRecord(
                umsatz=-100.0,
                soll_haben="S",
                konto=6880,
                gegenkonto=1200,
                belegdatum="1503",
                buchungstext="Negative amount",
            )
        ]
        errors = validate_records(records)
        assert len(errors) == 1
        assert "umsatz" in errors[0]

    def test_validate_records_empty_buchungstext(self):
        from app.services.datev_extf_export import DatevBookingRecord, validate_records

        records = [
            DatevBookingRecord(
                umsatz=100.0,
                soll_haben="S",
                konto=6880,
                gegenkonto=1200,
                belegdatum="1503",
                buchungstext="   ",
            )
        ]
        errors = validate_records(records)
        assert len(errors) == 1
        assert "buchungstext" in errors[0]

    def test_render_extf_header(self):
        from app.services.datev_extf_export import render_extf_header

        header = render_extf_header(berater_nr="12345", mandanten_nr="67890")
        assert '"EXTF"' in header
        assert "510" in header
        assert '"12345"' in header
        assert '"67890"' in header

    def test_render_extf_booking_line(self):
        from app.services.datev_extf_export import DatevBookingRecord, render_extf_booking_line

        rec = DatevBookingRecord(
            umsatz=2500.50,
            soll_haben="S",
            konto=6880,
            gegenkonto=1200,
            belegdatum="0103",
            buchungstext="ISO 27001 Zertifizierung",
            beleg1="CERT-001",
            kostenstelle="GRC",
        )
        line = render_extf_booking_line(rec)
        assert "2500,50" in line
        assert '"S"' in line
        assert "6880" in line
        assert "1200" in line
        assert '"ISO 27001 Zertifizierung"' in line

    def test_render_extf_export_complete(self):
        from app.services.datev_extf_export import DatevBookingRecord, render_extf_export

        records = [
            DatevBookingRecord(
                umsatz=1000.00,
                soll_haben="S",
                konto=6880,
                gegenkonto=1200,
                belegdatum="1503",
                buchungstext="Test Buchung",
            )
        ]
        content = render_extf_export(records)
        lines = content.strip().split("\r\n")
        assert len(lines) == 3  # header + column header + 1 record
        assert lines[0].startswith('"EXTF"')
        assert "Buchungstext" in lines[1]
        assert "1000,00" in lines[2]

    def test_compute_checksum(self):
        from app.services.datev_extf_export import compute_checksum

        cs = compute_checksum("test content")
        assert len(cs) == 64  # SHA-256 hex length

    def test_skr03_accounts(self):
        from app.services.datev_extf_export import get_default_accounts

        accts = get_default_accounts("bussgeld", "SKR03")
        assert accts["konto"] == 6880
        assert accts["gegenkonto"] == 1200

    def test_skr04_accounts(self):
        from app.services.datev_extf_export import get_default_accounts

        accts = get_default_accounts("bussgeld", "SKR04")
        assert accts["konto"] == 7680
        assert accts["gegenkonto"] == 1800

    def test_buchungstext_max_60_chars(self):
        from app.services.datev_extf_export import DatevBookingRecord

        rec = DatevBookingRecord(
            umsatz=100.0,
            soll_haben="S",
            konto=6880,
            gegenkonto=1200,
            belegdatum="0103",
            buchungstext="A" * 100,
        )
        assert len(rec.buchungstext) == 60


# ── RAG Chunking unit tests ─────────────────────────────────────────────────


class TestRagChunking:
    def test_chunk_article_text_single(self):
        from app.services.rag_norm_ingestion import chunk_article_text

        chunks = chunk_article_text("eu_ai_act", "Art. 9 Abs. 2", "Short text.")
        assert len(chunks) == 1
        assert chunks[0]["norm"] == "eu_ai_act"
        assert chunks[0]["article_ref"] == "Art. 9 Abs. 2"
        assert chunks[0]["chunk_index"] == 0

    def test_chunk_article_text_splits_long(self):
        from app.services.rag_norm_ingestion import chunk_article_text

        long_text = "\n\n".join([f"Paragraph {i} " * 50 for i in range(10)])
        chunks = chunk_article_text("nis2", "§ 30", long_text, max_chunk_size=500)
        assert len(chunks) > 1
        for i, c in enumerate(chunks):
            assert c["chunk_index"] == i

    def test_ingest_norm_chunks_persists(self):
        from app.services.rag_norm_ingestion import ingest_norm_chunks

        with Session(engine) as s:
            rows = ingest_norm_chunks(
                s,
                norm="eu_ai_act",
                article_ref="Art. 6",
                text_content="Hochrisiko-KI-Systeme gemäß Anhang III.",
                valid_from="2026-08-02",
            )
            count = len(rows)
            first_norm = rows[0].norm
            first_model = rows[0].embedding_model
            s.commit()
        assert count >= 1
        assert first_norm == "eu_ai_act"
        assert first_model is not None

    def test_search_norm_chunks(self):
        from app.services.rag_norm_ingestion import ingest_norm_chunks, search_norm_chunks

        with Session(engine) as s:
            ingest_norm_chunks(
                s,
                norm="dsgvo",
                article_ref="Art. 25",
                text_content=(
                    "Datenschutz durch Technikgestaltung und"
                    " datenschutzfreundliche Voreinstellungen."
                ),
            )
            s.commit()
            results = search_norm_chunks(s, norm="dsgvo", query_text="Datenschutz")
        assert len(results) >= 1
        assert results[0]["norm"] == "dsgvo"


# ── Gap Analysis unit tests ──────────────────────────────────────────────────


class TestGapAnalysis:
    def test_run_gap_analysis_creates_report(self):
        from app.services.gap_analysis_agent import run_gap_analysis

        tid = f"gap-test-{uuid.uuid4().hex[:8]}"
        with Session(engine) as s:
            report = run_gap_analysis(s, tenant_id=tid, norms=["eu_ai_act"])
            report_status = report.status
            report_scope = report.norm_scope
            report_tenant = report.tenant_id
            s.commit()
        assert report_status in ("completed", "failed")
        assert report_scope == "eu_ai_act"
        assert report_tenant == tid

    def test_gap_report_persisted(self):
        from app.services.gap_analysis_agent import get_gap_report, run_gap_analysis

        tid = f"gap-persist-{uuid.uuid4().hex[:8]}"
        with Session(engine) as s:
            report = run_gap_analysis(s, tenant_id=tid, norms=["nis2"])
            s.commit()
            result = get_gap_report(s, tid, report.id)
        assert result is not None
        assert result["id"] == report.id
        assert result["norm_scope"] == "nis2"

    def test_list_gap_reports(self):
        from app.services.gap_analysis_agent import list_gap_reports, run_gap_analysis

        tid = f"gap-list-{uuid.uuid4().hex[:8]}"
        with Session(engine) as s:
            run_gap_analysis(s, tenant_id=tid, norms=["eu_ai_act"])
            run_gap_analysis(s, tenant_id=tid, norms=["dsgvo"])
            s.commit()
            reports = list_gap_reports(s, tid)
        assert len(reports) == 2

    def test_gap_report_not_found(self):
        from app.services.gap_analysis_agent import get_gap_report

        with Session(engine) as s:
            result = get_gap_report(s, "nonexistent", "nonexistent")
        assert result is None


# ── Integration tests: API endpoints ─────────────────────────────────────────


class TestBoardKpiEndpoint:
    def test_board_kpi_report_happy_path(self):
        resp = client.get(
            "/api/v1/enterprise/board/kpi-report",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "compliance_score" in data
        assert "high_risk_ai_systems" in data
        assert "upcoming_deadlines" in data

    def test_board_kpi_report_board_member_access(self):
        resp = client.get(
            "/api/v1/enterprise/board/kpi-report",
            headers=_board_headers(),
        )
        assert resp.status_code == 200

    def test_board_kpi_report_ciso_access(self):
        resp = client.get(
            "/api/v1/enterprise/board/kpi-report",
            headers=_ciso_headers(),
        )
        assert resp.status_code == 200


class TestDatevExportEndpoint:
    def test_datev_export_happy_path(self):
        resp = client.post(
            "/api/v1/enterprise/datev/export",
            headers=_admin_headers(),
            params={"period_from": "2026-01-01", "period_to": "2026-03-31"},
        )
        assert resp.status_code == 200
        assert '"EXTF"' in resp.text
        assert "X-Checksum-SHA256" in resp.headers

    def test_datev_export_creates_audit_log(self):
        resp = client.post(
            "/api/v1/enterprise/datev/export",
            headers=_admin_headers(),
            params={"period_from": "2026-04-01", "period_to": "2026-04-30"},
        )
        assert resp.status_code == 200
        with Session(engine) as s:
            logs = s.query(DatevExportLogDB).filter(DatevExportLogDB.tenant_id == _TENANT).all()
        assert len(logs) >= 1


class TestGapAnalysisEndpoint:
    def test_trigger_gap_analysis(self):
        resp = client.post(
            "/api/v1/enterprise/gap-analysis/run",
            headers=_admin_headers(),
            params={"norms": "eu_ai_act,nis2"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "report_id" in data
        assert data["norm_scope"] == "eu_ai_act,nis2"

    def test_list_gap_reports_endpoint(self):
        # Create one first
        client.post(
            "/api/v1/enterprise/gap-analysis/run",
            headers=_admin_headers(),
            params={"norms": "dsgvo"},
        )
        resp = client.get(
            "/api/v1/enterprise/gap-analysis/reports",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_gap_report_not_found(self):
        resp = client.get(
            "/api/v1/enterprise/gap-analysis/reports/nonexistent-id",
            headers=_admin_headers(),
        )
        assert resp.status_code == 404

    def test_get_gap_report_detail(self):
        # Create
        create_resp = client.post(
            "/api/v1/enterprise/gap-analysis/run",
            headers=_admin_headers(),
            params={"norms": "eu_ai_act"},
        )
        report_id = create_resp.json()["report_id"]

        # Retrieve
        resp = client.get(
            f"/api/v1/enterprise/gap-analysis/reports/{report_id}",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == report_id
        assert "gaps" in data


class TestRagIngestEndpoint:
    def test_ingest_norm_text(self):
        resp = client.post(
            "/api/v1/enterprise/rag/ingest",
            headers=_admin_headers(),
            params={
                "norm": "eu_ai_act",
                "article_ref": "Art. 9 Abs. 2",
                "text_content": "Risikomanagement-System für Hochrisiko-KI.",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ingested_chunks"] >= 1
        assert data["norm"] == "eu_ai_act"


# ── Negative tests: RBAC enforcement ────────────────────────────────────────


class TestPhase3NegativeAccess:
    def test_board_kpi_viewer_denied(self):
        """Viewer role cannot access executive dashboard."""
        resp = client.get(
            "/api/v1/enterprise/board/kpi-report",
            headers=_viewer_headers(),
        )
        assert resp.status_code == 403

    def test_datev_export_viewer_denied(self):
        """Viewer cannot export DATEV."""
        resp = client.post(
            "/api/v1/enterprise/datev/export",
            headers=_viewer_headers(),
            params={"period_from": "2026-01-01", "period_to": "2026-03-31"},
        )
        assert resp.status_code == 403

    def test_datev_export_board_member_denied(self):
        """Board member cannot export DATEV."""
        resp = client.post(
            "/api/v1/enterprise/datev/export",
            headers=_board_headers(),
            params={"period_from": "2026-01-01", "period_to": "2026-03-31"},
        )
        assert resp.status_code == 403

    def test_datev_export_ciso_denied(self):
        """CISO cannot export DATEV (only TENANT_ADMIN / COMPLIANCE_ADMIN)."""
        resp = client.post(
            "/api/v1/enterprise/datev/export",
            headers=_ciso_headers(),
            params={"period_from": "2026-01-01", "period_to": "2026-03-31"},
        )
        assert resp.status_code == 403

    def test_gap_analysis_viewer_denied(self):
        """Viewer cannot run gap analysis."""
        resp = client.post(
            "/api/v1/enterprise/gap-analysis/run",
            headers=_viewer_headers(),
        )
        assert resp.status_code == 403

    def test_gap_analysis_board_member_denied(self):
        """Board member can view but not run gap analysis."""
        resp = client.post(
            "/api/v1/enterprise/gap-analysis/run",
            headers=_board_headers(),
        )
        assert resp.status_code == 403

    def test_gap_reports_board_member_can_view(self):
        """Board member can view gap reports."""
        resp = client.get(
            "/api/v1/enterprise/gap-analysis/reports",
            headers=_board_headers(),
        )
        assert resp.status_code == 200

    def test_no_auth_returns_401_or_400(self):
        """No API key returns 401."""
        resp = client.get("/api/v1/enterprise/board/kpi-report")
        assert resp.status_code in (400, 401)

    def test_rag_ingest_viewer_denied(self):
        """Viewer cannot ingest norms."""
        resp = client.post(
            "/api/v1/enterprise/rag/ingest",
            headers=_viewer_headers(),
            params={
                "norm": "test",
                "article_ref": "Art. 1",
                "text_content": "test",
            },
        )
        assert resp.status_code == 403

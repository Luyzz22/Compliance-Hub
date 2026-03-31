"""E2E-Integration: High-Risk onboarden, klassifizieren, NIS2-KPIs, Actions, Evidenzen, Board.

Technischer Pfad für Demo „KRITIS Netzlast-Prognose“ (docs/e2e-demo-flow.md).
"""

from __future__ import annotations

import io
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.board_report_audit_records import _records

# Minimal-PDF-Stub (wie test_evidence_files)
MINIMAL_PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"

E2E_TENANT_A = "e2e-hr-gov-tenant-a"
E2E_TENANT_B = "e2e-hr-gov-tenant-b"
E2E_SYSTEM_ID = "e2e-nlz-prognose"
E2E_API_KEY = "board-kpi-key"


def _h(tenant_id: str) -> dict[str, str]:
    return {"x-api-key": E2E_API_KEY, "x-tenant-id": tenant_id}


def _high_risk_system_payload(system_id: str = E2E_SYSTEM_ID) -> dict:
    """High-Risk-Stammdaten ohne Runbooks/Supplier-Register (löst Board-Alerts aus)."""
    return {
        "id": system_id,
        "name": "KRITIS Netzlast-Prognose",
        "description": "Prognosemodell für Netzlaststeuerung – E2E-Demo",
        "business_unit": "Netzbetrieb",
        "risk_level": "high",
        "ai_act_category": "high_risk",
        "gdpr_dpia_required": True,
        "owner_email": "netzbetrieb@tenant.example",
        "criticality": "high",
        "data_sensitivity": "confidential",
        "has_incident_runbook": False,
        "has_supplier_risk_register": False,
        "has_backup_runbook": False,
    }


@pytest.fixture
def evidence_storage_e2e(tmp_path, monkeypatch: pytest.MonkeyPatch):
    d = tmp_path / "evidence_e2e"
    monkeypatch.setenv("EVIDENCE_STORAGE_PATH", str(d))
    return d


def test_e2e_high_risk_governance_flow(evidence_storage_e2e) -> None:
    """Happy Path bis Board: classify, NIS2-KPIs, Action, Evidenzen, Overview, Export."""
    with TestClient(app) as client:
        # 1) AI-System anlegen
        cr = client.post(
            "/api/v1/ai-systems",
            json=_high_risk_system_payload(),
            headers=_h(E2E_TENANT_A),
        )
        assert cr.status_code == 200, cr.text
        created = cr.json()
        assert created["id"] == E2E_SYSTEM_ID
        assert created["risk_level"] == "high"
        assert created["ai_act_category"] == "high_risk"

        # 2) EU-AI-Act-Klassifikation (Anhang III, kritische Infrastruktur → Kategorie 2)
        cl = client.post(
            f"/api/v1/ai-systems/{E2E_SYSTEM_ID}/classify",
            headers=_h(E2E_TENANT_A),
            json={"use_case_domain": "critical_infra"},
        )
        assert cl.status_code == 200, cl.text
        cls_body = cl.json()
        assert cls_body["risk_level"] == "high_risk"
        assert cls_body["classification_path"] == "annex_iii"
        assert cls_body["annex_iii_category"] == 2

        gc = client.get(
            f"/api/v1/ai-systems/{E2E_SYSTEM_ID}/classification",
            headers=_h(E2E_TENANT_A),
        )
        assert gc.status_code == 200
        assert gc.json()["ai_system_id"] == E2E_SYSTEM_ID

        # 3) NIS2-/KRITIS-KPIs (mittlere Werte → Aggregation + Export prüfbar)
        for kpi_type, pct in (
            ("INCIDENT_RESPONSE_MATURITY", 48),
            ("SUPPLIER_RISK_COVERAGE", 52),
            ("OT_IT_SEGREGATION", 55),
        ):
            pr = client.post(
                f"/api/v1/ai-systems/{E2E_SYSTEM_ID}/nis2-kritis-kpis",
                headers=_h(E2E_TENANT_A),
                json={"kpi_type": kpi_type, "value_percent": pct},
            )
            assert pr.status_code == 200, pr.text
            assert pr.json()["value_percent"] == pct

        # 4) Governance-Action
        ar = client.post(
            "/api/v1/ai-governance/actions",
            headers=_h(E2E_TENANT_A),
            json={
                "related_ai_system_id": E2E_SYSTEM_ID,
                "related_requirement": "NIS2 Art. 21 – Supply Chain / EU AI Act Art. 9",
                "title": "NIS2 Supplier-Risk-Register für Netzlast-KI vollständig aufbauen",
                "status": "open",
            },
        )
        assert ar.status_code == 201, ar.text
        action = ar.json()
        action_id = action["id"]
        assert action["tenant_id"] == E2E_TENANT_A
        assert action["related_ai_system_id"] == E2E_SYSTEM_ID

        # 5) Evidenzen: System, Action, Audit-Record
        up_sys = client.post(
            "/api/v1/evidence/uploads",
            headers=_h(E2E_TENANT_A) | {"x-uploaded-by": "ciso@tenant.example"},
            files={"file": ("dpia_stub.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")},
            data={
                "ai_system_id": E2E_SYSTEM_ID,
                "norm_framework": "EUAIACT",
                "norm_reference": "Art. 9 Risikomanagement",
            },
        )
        assert up_sys.status_code == 201, up_sys.text
        ev_sys = up_sys.json()
        assert ev_sys["ai_system_id"] == E2E_SYSTEM_ID
        assert ev_sys["tenant_id"] == E2E_TENANT_A
        ev_sys_id = ev_sys["id"]

        up_act = client.post(
            "/api/v1/evidence/uploads",
            headers=_h(E2E_TENANT_A),
            files={"file": ("massnahme.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")},
            data={"action_id": action_id, "norm_framework": "NIS2"},
        )
        assert up_act.status_code == 201, up_act.text
        ev_act_id = up_act.json()["id"]

        _records.clear()
        audit_r = client.post(
            "/api/v1/ai-governance/report/board/audit-records",
            json={"purpose": "E2E Board-Nachweis", "status": "draft"},
            headers=_h(E2E_TENANT_A),
        )
        assert audit_r.status_code == 201, audit_r.text
        audit_id = audit_r.json()["id"]

        up_aud = client.post(
            "/api/v1/evidence/uploads",
            headers=_h(E2E_TENANT_A),
            files={"file": ("audit_pack.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")},
            data={"audit_record_id": audit_id},
        )
        assert up_aud.status_code == 201, up_aud.text

        dl = client.get(
            f"/api/v1/evidence/{ev_sys_id}/download",
            headers=_h(E2E_TENANT_A),
        )
        assert dl.status_code == 200
        assert dl.content.startswith(b"%PDF")

        # 6) Compliance-Overview & EU-AI-Act-Readiness
        ov = client.get(
            "/api/v1/ai-governance/compliance/overview",
            headers=_h(E2E_TENANT_A),
        )
        assert ov.status_code == 200
        overview = ov.json()
        assert overview["tenant_id"] == E2E_TENANT_A
        assert 0.0 <= overview["overall_readiness"] <= 1.0
        assert overview["deadline"] == "2026-08-02"

        rd = client.get(
            "/api/v1/ai-governance/readiness/eu-ai-act",
            headers=_h(E2E_TENANT_A),
        )
        assert rd.status_code == 200
        readiness = rd.json()
        assert readiness["tenant_id"] == E2E_TENANT_A
        open_actions = readiness["open_governance_actions"]
        assert any(
            a.get("related_ai_system_id") == E2E_SYSTEM_ID or a.get("title") == action["title"]
            for a in open_actions
        )

        # 7) Tenant-Governance-KPIs (NIS2-Mittelwert) & Board-KPIs
        gk = client.get(
            f"/api/v1/tenants/{E2E_TENANT_A}/ai-governance-kpis",
            headers=_h(E2E_TENANT_A),
        )
        assert gk.status_code == 200
        gk_body = gk.json()
        assert gk_body["tenant_id"] == E2E_TENANT_A
        assert gk_body["nis2_kritis_kpi_mean_percent"] is not None
        assert 40.0 <= gk_body["nis2_kritis_kpi_mean_percent"] <= 60.0

        bk = client.get(
            "/api/v1/ai-governance/board-kpis",
            headers=_h(E2E_TENANT_A),
        )
        assert bk.status_code == 200
        bk_body = bk.json()
        assert bk_body["tenant_id"] == E2E_TENANT_A
        assert bk_body["high_risk_systems"] >= 1
        assert bk_body["nis2_kritis_kpi_mean_percent"] is not None

        # 8) Board-Alerts & KPI-/Alert-Export
        alerts = client.get(
            "/api/v1/ai-governance/alerts/board",
            headers=_h(E2E_TENANT_A),
        )
        assert alerts.status_code == 200
        alert_list = alerts.json()
        assert isinstance(alert_list, list)
        assert len(alert_list) >= 1
        assert all(a["tenant_id"] == E2E_TENANT_A for a in alert_list)
        severities = {a["severity"] for a in alert_list}
        assert severities & {"warning", "critical", "info"}

        exp_alerts = client.get(
            "/api/v1/ai-governance/alerts/board/export",
            params={"format": "json"},
            headers=_h(E2E_TENANT_A),
        )
        assert exp_alerts.status_code == 200
        export_alerts = exp_alerts.json()
        assert export_alerts["tenant_id"] == E2E_TENANT_A
        assert len(export_alerts["alerts"]) >= 1

        kpi_exp = client.get(
            "/api/v1/ai-governance/report/board/kpi-export",
            params={"format": "json"},
            headers=_h(E2E_TENANT_A),
        )
        assert kpi_exp.status_code == 200
        kpi_data = json.loads(kpi_exp.text)
        assert kpi_data["tenant_id"] == E2E_TENANT_A
        row = next(s for s in kpi_data["systems"] if s["ai_system_id"] == E2E_SYSTEM_ID)
        assert row["nis2_kritis_incident_response_maturity_percent"] == 48
        assert row["nis2_kritis_supplier_risk_coverage_percent"] == 52
        assert row["nis2_kritis_ot_it_segregation_percent"] == 55

        kpi_csv = client.get(
            "/api/v1/ai-governance/report/board/kpi-export",
            params={"format": "csv"},
            headers=_h(E2E_TENANT_A),
        )
        assert kpi_csv.status_code == 200
        assert E2E_SYSTEM_ID in kpi_csv.text

        # 9) Tenant-Isolation (fremder Mandant)
        client.post(
            "/api/v1/ai-systems",
            json=_high_risk_system_payload("e2e-other-sys"),
            headers=_h(E2E_TENANT_B),
        )

        dl_cross = client.get(
            f"/api/v1/evidence/{ev_sys_id}/download",
            headers=_h(E2E_TENANT_B),
        )
        assert dl_cross.status_code == 404

        act_cross = client.get(
            f"/api/v1/ai-governance/actions/{action_id}",
            headers=_h(E2E_TENANT_B),
        )
        assert act_cross.status_code == 404

        ev_act_cross = client.get(
            f"/api/v1/evidence/{ev_act_id}/download",
            headers=_h(E2E_TENANT_B),
        )
        assert ev_act_cross.status_code == 404


def test_e2e_csv_import_single_high_risk_then_classify(evidence_storage_e2e) -> None:
    """Alternativer Einstieg: einzeiliger CSV-Import, danach Klassifikation (wie Hauptpfad)."""
    tenant = "e2e-csv-import-tenant"
    csv_body = (
        "id,name,description,business_unit,risk_level,ai_act_category,gdpr_dpia_required\n"
        "e2e-csv-nlz,CSV Netzlast KI,Import-Test,Netz,high,high_risk,true\n"
    )
    with TestClient(app) as client:
        imp = client.post(
            "/api/v1/ai-systems/import",
            headers=_h(tenant),
            files={"file": ("one.csv", csv_body.encode("utf-8"), "text/csv")},
        )
        assert imp.status_code == 200, imp.text
        assert imp.json()["imported_count"] == 1

        cl = client.post(
            "/api/v1/ai-systems/e2e-csv-nlz/classify",
            headers=_h(tenant),
            json={"use_case_domain": "critical_infra"},
        )
        assert cl.status_code == 200
        assert cl.json()["risk_level"] == "high_risk"

        client.post(
            "/api/v1/ai-systems/e2e-csv-nlz/nis2-kritis-kpis",
            headers=_h(tenant),
            json={"kpi_type": "INCIDENT_RESPONSE_MATURITY", "value_percent": 45},
        )
        exp = client.get(
            "/api/v1/ai-governance/report/board/kpi-export",
            params={"format": "json"},
            headers=_h(tenant),
        )
        assert exp.status_code == 200
        systems = json.loads(exp.text)["systems"]
        assert any(s["ai_system_id"] == "e2e-csv-nlz" for s in systems)

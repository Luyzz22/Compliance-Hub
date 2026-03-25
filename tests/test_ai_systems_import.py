from __future__ import annotations

import io

from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.main import app
from tests.conftest import _headers


def _tenant_headers(tenant_id: str) -> dict[str, str]:
    h = _headers()
    return {**h, "x-tenant-id": tenant_id}


def test_import_csv_valid_three_systems() -> None:
    tenant = "csv-import-tenant-a"
    csv_body = (
        "id,name,description,business_unit,risk_level,ai_act_category,gdpr_dpia_required\n"
        "csv-sys-1,Alpha,Desc A,IT,high,high_risk,ja\n"
        ",Beta,Desc B,HR,limited,limited_risk,false\n"
        "csv-sys-3,Gamma,Desc C,Ops,LOW,minimal_risk,0\n"
    )
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/ai-systems/import",
            headers=_tenant_headers(tenant),
            files={"file": ("systems.csv", csv_body.encode("utf-8"), "text/csv")},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_rows"] == 3
    assert data["imported_count"] == 3
    assert data["failed_count"] == 0
    assert data["errors"] == []

    with TestClient(app) as client:
        listed = client.get(
            "/api/v1/ai-systems",
            headers=_tenant_headers(tenant),
        ).json()
    ids = {item["id"] for item in listed}
    assert "csv-sys-1" in ids
    assert "csv-sys-3" in ids
    assert any(item["name"] == "Beta" for item in listed)


def test_import_csv_partial_errors_continue() -> None:
    tenant = "csv-import-tenant-b"
    csv_body = (
        "name,description,business_unit,risk_level,ai_act_category\n"
        "OkOne,Good,IT,high,high_risk\n"
        "BadRisk,Bad row,IT,not_a_risk,high_risk\n"
        "OkTwo,Also good,Legal,hoch,minimal_risk\n"
    )
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/ai-systems/import",
            headers=_tenant_headers(tenant),
            files={"file": ("mixed.csv", csv_body.encode("utf-8"), "text/csv")},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_rows"] == 3
    assert data["imported_count"] == 2
    assert data["failed_count"] == 1
    assert len(data["errors"]) == 1
    assert data["errors"][0]["row_number"] == 3
    assert "risk_level" in data["errors"][0]["message"].lower() or "Ungültig" in data["errors"][0][
        "message"
    ]

    with TestClient(app) as client:
        listed = client.get(
            "/api/v1/ai-systems",
            headers=_tenant_headers(tenant),
        ).json()
    assert len([x for x in listed if x["name"] in ("OkOne", "OkTwo")]) == 2


def test_import_tenant_isolation() -> None:
    tenant_a = "csv-import-tenant-c"
    tenant_b = "csv-import-tenant-d"
    csv_a = (
        "id,name,description,business_unit,risk_level,ai_act_category\n"
        "iso-sys-a,Only A,Desc,IT,low,minimal_risk\n"
    )
    csv_b = (
        "id,name,description,business_unit,risk_level,ai_act_category\n"
        "iso-sys-b,Only B,Desc,IT,low,minimal_risk\n"
    )
    with TestClient(app) as client:
        client.post(
            "/api/v1/ai-systems/import",
            headers=_tenant_headers(tenant_a),
            files={"file": ("a.csv", csv_a.encode("utf-8"), "text/csv")},
        )
        client.post(
            "/api/v1/ai-systems/import",
            headers=_tenant_headers(tenant_b),
            files={"file": ("b.csv", csv_b.encode("utf-8"), "text/csv")},
        )
        list_a = client.get("/api/v1/ai-systems", headers=_tenant_headers(tenant_a)).json()
        list_b = client.get("/api/v1/ai-systems", headers=_tenant_headers(tenant_b)).json()
    ids_a = {item["id"] for item in list_a}
    ids_b = {item["id"] for item in list_b}
    assert "iso-sys-a" in ids_a
    assert "iso-sys-b" not in ids_a
    assert "iso-sys-b" in ids_b
    assert "iso-sys-a" not in ids_b


def test_import_xlsx_two_rows() -> None:
    tenant = "xlsx-import-tenant"
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.append(
        [
            "name",
            "description",
            "business_unit",
            "risk_level",
            "ai_act_category",
            "gdpr_dpia_required",
        ]
    )
    ws.append(["XL1", "D1", "IT", "high", "high_risk", "true"])
    ws.append(["XL2", "D2", "Ops", "niedrig", "minimal_risk", "nein"])
    buf = io.BytesIO()
    wb.save(buf)
    raw = buf.getvalue()

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/ai-systems/import",
            headers=_tenant_headers(tenant),
            files={
                "file": (
                    "systems.xlsx",
                    raw,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_rows"] == 2
    assert data["imported_count"] == 2
    assert data["failed_count"] == 0

    with TestClient(app) as client:
        listed = client.get(
            "/api/v1/ai-systems",
            headers=_tenant_headers(tenant),
        ).json()
    names = {item["name"] for item in listed}
    assert "XL1" in names
    assert "XL2" in names


def test_import_empty_file_400() -> None:
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/ai-systems/import",
            headers=_headers(),
            files={"file": ("empty.csv", b"", "text/csv")},
        )
    assert resp.status_code == 400

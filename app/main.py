from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.models import (
    ComplianceAction,
    ComplianceScoreResponse,
    DocumentIngestRequest,
    DocumentIngestResponse,
    DocumentType,
    EInvoiceFormat,
)
from app.services.compliance_engine import build_audit_hash, calculate_tenant_score, derive_actions

app = FastAPI(title="SBS-Nexus ComplianceHub", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_ACTION_STORE: dict[str, list[ComplianceAction]] = {}


def _parse_intake_payload(payload: dict) -> DocumentIngestRequest:
    try:
        return DocumentIngestRequest(
            tenant_id=str(payload["tenant_id"]),
            document_id=str(payload["document_id"]),
            document_type=DocumentType(payload["document_type"]),
            supplier_name=str(payload["supplier_name"]),
            supplier_country=str(payload["supplier_country"]).upper(),
            contains_personal_data=bool(payload.get("contains_personal_data", True)),
            e_invoice_format=EInvoiceFormat(payload.get("e_invoice_format", "unknown")),
            xml_valid_en16931=bool(payload.get("xml_valid_en16931", False)),
            amount_eur=float(payload.get("amount_eur", 0.0)),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid payload: {exc}") from exc


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok", "product": "ComplianceHub", "region": "DACH"}


@app.post("/api/v1/documents/intake")
def ingest_document(payload: dict) -> dict:
    parsed = _parse_intake_payload(payload)
    actions = derive_actions(parsed)
    _ACTION_STORE.setdefault(parsed.tenant_id, []).extend(actions)

    response = DocumentIngestResponse(
        document_id=parsed.document_id,
        accepted=True,
        timestamp_utc=datetime.now(timezone.utc),
        actions=actions,
        audit_hash=build_audit_hash(parsed),
    )
    return asdict(response)


@app.get("/api/v1/compliance/score/{tenant_id}")
def get_compliance_score(tenant_id: str) -> dict:
    history = _ACTION_STORE.get(tenant_id, [])
    score, risk_level, recommendations = calculate_tenant_score(history)

    response = ComplianceScoreResponse(
        tenant_id=tenant_id,
        score=score,
        risk_level=risk_level,
        recommendations=recommendations,
    )
    return asdict(response)


app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

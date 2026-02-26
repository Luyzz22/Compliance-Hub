from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.models import (
    ComplianceAction,
    DocumentIngestRequest,
    DocumentType,
    EInvoiceFormat,
)
from app.services.compliance_engine import build_audit_hash, derive_actions

app = FastAPI(title="ComplianceHub API", version="0.1.0")


class DocumentIntakeRequest(BaseModel):
    tenant_id: str = Field(..., examples=["tenant-001"])
    document_id: str = Field(..., examples=["doc-001"])
    document_type: DocumentType
    supplier_name: str
    supplier_country: str
    contains_personal_data: bool = True
    e_invoice_format: EInvoiceFormat = EInvoiceFormat.unknown
    xml_valid_en16931: bool = False
    amount_eur: float = 0.0


class ComplianceActionModel(BaseModel):
    action: str
    module: str
    severity: str
    rationale: str

    @classmethod
    def from_domain(cls, action: ComplianceAction) -> ComplianceActionModel:
        return cls(
            action=action.action,
            module=action.module,
            severity=action.severity,
            rationale=action.rationale,
        )


class DocumentIntakeResponse(BaseModel):
    document_id: str
    accepted: bool
    timestamp_utc: datetime
    actions: list[ComplianceActionModel]
    audit_hash: str


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "product": "ComplianceHub",
        "region": "DACH",
    }


@app.post("/api/v1/documents/intake", response_model=DocumentIntakeResponse)
def intake(payload: DocumentIntakeRequest) -> DocumentIntakeResponse:
    domain_payload = DocumentIngestRequest(
        tenant_id=payload.tenant_id,
        document_id=payload.document_id,
        document_type=payload.document_type,
        supplier_name=payload.supplier_name,
        supplier_country=payload.supplier_country,
        contains_personal_data=payload.contains_personal_data,
        e_invoice_format=payload.e_invoice_format,
        xml_valid_en16931=payload.xml_valid_en16931,
        amount_eur=payload.amount_eur,
    )

    actions = derive_actions(domain_payload)
    audit_hash = build_audit_hash(domain_payload)

    return DocumentIntakeResponse(
        document_id=payload.document_id,
        accepted=True,
        timestamp_utc=datetime.now(UTC),
        actions=[ComplianceActionModel.from_domain(action) for action in actions],
        audit_hash=audit_hash,
    )

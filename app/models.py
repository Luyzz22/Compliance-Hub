from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class DocumentType(str, Enum):
    invoice = "invoice"
    contract = "contract"


class EInvoiceFormat(str, Enum):
    xrechnung = "xrechnung"
    zugferd = "zugferd"
    unknown = "unknown"


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


@dataclass(slots=True)
class DocumentIngestRequest:
    tenant_id: str
    document_id: str
    document_type: DocumentType
    supplier_name: str
    supplier_country: str
    contains_personal_data: bool = True
    e_invoice_format: EInvoiceFormat = EInvoiceFormat.unknown
    xml_valid_en16931: bool = False
    amount_eur: float = 0.0


@dataclass(slots=True)
class ComplianceAction:
    action: str
    module: str
    severity: Severity
    rationale: str


@dataclass(slots=True)
class TenantComplianceProfile:
    tenant_id: str
    data_residency_region: str
    requires_human_approval: bool
    accepted_invoice_formats: tuple[EInvoiceFormat, ...] = (
        EInvoiceFormat.xrechnung,
        EInvoiceFormat.zugferd,
    )


@dataclass(slots=True)
class DocumentIngestResponse:
    document_id: str
    accepted: bool
    timestamp_utc: datetime
    actions: list[ComplianceAction]
    audit_hash: str


@dataclass(slots=True)
class ComplianceScoreResponse:
    tenant_id: str
    score: int
    risk_level: str
    recommendations: list[str]


@dataclass(slots=True)
class PlatformAuditFinding:
    control_id: str
    domain: str
    status: str
    severity: Severity
    recommendation: str

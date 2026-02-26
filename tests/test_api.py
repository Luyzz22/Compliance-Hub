from app.models import DocumentIngestRequest, DocumentType, EInvoiceFormat, Severity
from app.services.compliance_engine import (
    build_audit_hash,
    calculate_tenant_score,
    derive_actions,
    run_platform_audit,
)


def test_derive_actions_for_invalid_invoice() -> None:
    payload = DocumentIngestRequest(
        tenant_id="tenant-dach-1",
        document_id="inv-001",
        document_type=DocumentType.invoice,
        supplier_name="Cloud US Inc",
        supplier_country="US",
        contains_personal_data=True,
        e_invoice_format=EInvoiceFormat.xrechnung,
        xml_valid_en16931=False,
        amount_eur=1299.0,
    )

    actions = derive_actions(payload)

    assert any(a.action == "block_auto_posting" for a in actions)
    assert any(a.action == "create_or_update_ropa_entry" for a in actions)
    assert any(a.action == "require_human_approval" for a in actions)
    assert any(a.action == "append_worm_archive_record" for a in actions)


def test_audit_hash_and_score() -> None:
    payload = DocumentIngestRequest(
        tenant_id="tenant-dach-2",
        document_id="inv-002",
        document_type=DocumentType.invoice,
        supplier_name="Muster GmbH",
        supplier_country="DE",
        contains_personal_data=False,
        e_invoice_format=EInvoiceFormat.zugferd,
        xml_valid_en16931=True,
        amount_eur=99.9,
    )

    digest = build_audit_hash(payload)
    assert len(digest) == 64

    score, risk, recommendations = calculate_tenant_score(derive_actions(payload))
    assert 0 <= score <= 100
    assert risk in {"low", "medium", "high"}
    assert len(recommendations) >= 1


def test_platform_audit_baseline_is_present() -> None:
    findings = run_platform_audit()
    assert len(findings) == 4
    assert any(f.control_id == "AI-009" for f in findings)
    assert all(f.severity in (Severity.low, Severity.medium, Severity.high, Severity.critical) for f in findings)


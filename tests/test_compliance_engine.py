from app.models import DocumentIngestRequest, DocumentType, EInvoiceFormat
from app.services.compliance_engine import calculate_tenant_score, derive_actions


def test_derive_actions_invoice_flags():
    payload = DocumentIngestRequest(
        tenant_id="tenant-1",
        document_id="doc-1",
        document_type=DocumentType.invoice,
        supplier_name="Supplier GmbH",
        supplier_country="US",
        contains_personal_data=True,
        e_invoice_format=EInvoiceFormat.unknown,
        xml_valid_en16931=False,
        amount_eur=1200.0,
    )

    actions = derive_actions(payload)
    action_names = {action.action for action in actions}

    assert "request_einvoice_replacement" in action_names
    assert "block_auto_posting" in action_names
    assert "create_or_update_ropa_entry" in action_names
    assert "trigger_transfer_impact_assessment" in action_names
    assert "append_worm_archive_record" in action_names


def test_calculate_tenant_score_ranges():
    score, risk, recommendations = calculate_tenant_score([])

    assert score == 100
    assert risk == "low"
    assert isinstance(recommendations, list)

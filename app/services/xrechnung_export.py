"""XRechnung 3.0 / EN-16931 UBL 2.1 invoice export service.

Generates XML invoices conforming to the XRechnung 3.0 standard
(urn:xoev-de:kosit:standard:xrechnung_3.0) using stdlib xml.etree only.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from xml.etree.ElementTree import Element, SubElement, tostring

logger = logging.getLogger(__name__)

# UBL 2.1 / XRechnung namespaces
NS_INVOICE = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
NS_CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
NS_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"

XRECHNUNG_CUSTOMIZATION_ID = (
    "urn:cen.eu:en16931:2017#compliant#urn:xoev-de:kosit:standard:xrechnung_3.0"
)
XRECHNUNG_PROFILE_ID = "urn:fdc:peppol.eu:2017:poacc:billing:01:1.0"

# UBL InvoiceTypeCode 380 = Commercial Invoice
INVOICE_TYPE_CODE = "380"


@dataclass
class XRechnungInvoice:
    """Structured representation of an XRechnung invoice."""

    invoice_id: str
    issue_date: date
    due_date: date
    seller_name: str
    seller_tax_id: str
    seller_address: str
    buyer_name: str
    buyer_reference: str  # Leitweg-ID
    buyer_address: str = ""
    line_items: list[dict] = field(default_factory=list)
    currency: str = "EUR"
    note: str | None = None


def _dec(value: float | int | str) -> Decimal:
    """Convert to Decimal rounded to 2 places."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _cbc(parent: Element, tag: str, text: str, **attrs: str) -> Element:
    """Create a CommonBasicComponents child element."""
    el = SubElement(parent, f"{{{NS_CBC}}}{tag}")
    el.text = text
    for k, v in attrs.items():
        el.set(k, v)
    return el


def _cac(parent: Element, tag: str) -> Element:
    """Create a CommonAggregateComponents child element."""
    return SubElement(parent, f"{{{NS_CAC}}}{tag}")


def _build_party(parent_tag: Element, name: str, address: str, tax_id: str | None = None) -> None:
    """Build an AccountingSupplierParty or AccountingCustomerParty subtree."""
    party = _cac(parent_tag, "Party")

    # Postal address (simplified: single StreetName line)
    postal = _cac(party, "PostalAddress")
    _cbc(postal, "StreetName", address)
    country = _cac(postal, "Country")
    _cbc(country, "IdentificationCode", "DE")

    # Tax scheme
    if tax_id:
        tax_scheme_container = _cac(party, "PartyTaxScheme")
        _cbc(tax_scheme_container, "CompanyID", tax_id)
        scheme = _cac(tax_scheme_container, "TaxScheme")
        _cbc(scheme, "ID", "VAT")

    # Legal entity
    legal = _cac(party, "PartyLegalEntity")
    _cbc(legal, "RegistrationName", name)


def _build_invoice_line(
    parent: Element,
    line_id: int,
    item: dict,
    currency: str,
) -> tuple[Decimal, Decimal]:
    """Build a single InvoiceLine and return (line_net, line_tax)."""
    description = str(item.get("description", ""))
    quantity = _dec(item.get("quantity", 1))
    unit_price = _dec(item.get("unit_price", 0))
    tax_percent = _dec(item.get("tax_percent", 19))

    line_net = _dec(quantity * unit_price)
    line_tax = _dec(line_net * tax_percent / Decimal("100"))

    inv_line = _cac(parent, "InvoiceLine")
    _cbc(inv_line, "ID", str(line_id))
    _cbc(inv_line, "InvoicedQuantity", str(quantity), unitCode="C62")
    _cbc(inv_line, "LineExtensionAmount", str(line_net), currencyID=currency)

    # Item element
    cac_item = _cac(inv_line, "Item")
    _cbc(cac_item, "Name", description)
    tax_cat = _cac(cac_item, "ClassifiedTaxCategory")
    _cbc(tax_cat, "ID", "S")
    _cbc(tax_cat, "Percent", str(tax_percent))
    scheme = _cac(tax_cat, "TaxScheme")
    _cbc(scheme, "ID", "VAT")

    # Price
    price = _cac(inv_line, "Price")
    _cbc(price, "PriceAmount", str(unit_price), currencyID=currency)

    return line_net, line_tax


def generate_xrechnung_xml(invoice: XRechnungInvoice) -> str:
    """Create a UBL 2.1 XML string conforming to XRechnung 3.0 / EN-16931."""
    root = Element(f"{{{NS_INVOICE}}}Invoice")
    root.set("xmlns", NS_INVOICE)
    root.set("xmlns:cac", NS_CAC)
    root.set("xmlns:cbc", NS_CBC)

    # Header
    _cbc(root, "CustomizationID", XRECHNUNG_CUSTOMIZATION_ID)
    _cbc(root, "ProfileID", XRECHNUNG_PROFILE_ID)
    _cbc(root, "ID", invoice.invoice_id)
    _cbc(root, "IssueDate", invoice.issue_date.isoformat())
    _cbc(root, "DueDate", invoice.due_date.isoformat())
    _cbc(root, "InvoiceTypeCode", INVOICE_TYPE_CODE)

    if invoice.note:
        _cbc(root, "Note", invoice.note)

    _cbc(root, "DocumentCurrencyCode", invoice.currency)
    _cbc(root, "BuyerReference", invoice.buyer_reference)

    # Supplier party
    supplier = _cac(root, "AccountingSupplierParty")
    _build_party(supplier, invoice.seller_name, invoice.seller_address, invoice.seller_tax_id)

    # Customer party
    customer = _cac(root, "AccountingCustomerParty")
    _build_party(customer, invoice.buyer_name, invoice.buyer_address)

    # Invoice lines — accumulate totals per tax rate
    total_net = Decimal("0.00")
    total_tax = Decimal("0.00")
    tax_breakdown: dict[str, tuple[Decimal, Decimal]] = {}  # rate → (taxable, tax)
    for idx, item in enumerate(invoice.line_items, 1):
        line_net, line_tax = _build_invoice_line(root, idx, item, invoice.currency)
        total_net += line_net
        total_tax += line_tax
        rate_key = str(_dec(item.get("tax_percent", 19)))
        prev_taxable, prev_tax = tax_breakdown.get(rate_key, (Decimal("0.00"), Decimal("0.00")))
        tax_breakdown[rate_key] = (prev_taxable + line_net, prev_tax + line_tax)

    total_net = _dec(total_net)
    total_tax = _dec(total_tax)
    total_gross = _dec(total_net + total_tax)

    # TaxTotal with per-rate subtotals
    tax_total = _cac(root, "TaxTotal")
    _cbc(tax_total, "TaxAmount", str(total_tax), currencyID=invoice.currency)
    for rate_key, (taxable, tax_amt) in sorted(tax_breakdown.items()):
        tax_subtotal = _cac(tax_total, "TaxSubtotal")
        _cbc(tax_subtotal, "TaxableAmount", str(_dec(taxable)), currencyID=invoice.currency)
        _cbc(tax_subtotal, "TaxAmount", str(_dec(tax_amt)), currencyID=invoice.currency)
        tax_cat = _cac(tax_subtotal, "TaxCategory")
        _cbc(tax_cat, "ID", "S")
        _cbc(tax_cat, "Percent", rate_key)
        scheme = _cac(tax_cat, "TaxScheme")
        _cbc(scheme, "ID", "VAT")

    # LegalMonetaryTotal
    monetary = _cac(root, "LegalMonetaryTotal")
    _cbc(monetary, "LineExtensionAmount", str(total_net), currencyID=invoice.currency)
    _cbc(monetary, "TaxExclusiveAmount", str(total_net), currencyID=invoice.currency)
    _cbc(monetary, "TaxInclusiveAmount", str(total_gross), currencyID=invoice.currency)
    _cbc(monetary, "PayableAmount", str(total_gross), currencyID=invoice.currency)

    xml_str: str = tostring(root, encoding="unicode")
    xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'

    logger.info(
        "xrechnung_generated invoice_id=%s lines=%d total=%.2f",
        invoice.invoice_id,
        len(invoice.line_items),
        total_gross,
    )
    return xml_declaration + xml_str


def validate_xrechnung(xml_content: str) -> list[str]:
    """Basic structural validation of an XRechnung XML document.

    Checks that required UBL 2.1 / XRechnung elements are present.
    Returns a list of error messages (empty list means valid).
    """
    from xml.etree.ElementTree import ParseError, fromstring

    errors: list[str] = []

    try:
        root = fromstring(xml_content)
    except ParseError as exc:
        errors.append(f"XML parse error: {exc}")
        return errors

    def _find(tag: str, ns: str = NS_CBC) -> bool:
        return root.find(f".//{{{ns}}}{tag}") is not None

    def _find_cac(tag: str) -> bool:
        return root.find(f".//{{{NS_CAC}}}{tag}") is not None

    required_cbc = [
        "CustomizationID",
        "ProfileID",
        "ID",
        "IssueDate",
        "DueDate",
        "InvoiceTypeCode",
        "DocumentCurrencyCode",
        "BuyerReference",
    ]
    for tag in required_cbc:
        if not _find(tag):
            errors.append(f"Missing required element: cbc:{tag}")

    required_cac = [
        "AccountingSupplierParty",
        "AccountingCustomerParty",
        "TaxTotal",
        "LegalMonetaryTotal",
        "InvoiceLine",
    ]
    for tag in required_cac:
        if not _find_cac(tag):
            errors.append(f"Missing required element: cac:{tag}")

    # Validate CustomizationID value
    cust_el = root.find(f".//{{{NS_CBC}}}CustomizationID")
    if cust_el is not None and cust_el.text != XRECHNUNG_CUSTOMIZATION_ID:
        errors.append(
            f"Invalid CustomizationID: expected '{XRECHNUNG_CUSTOMIZATION_ID}', "
            f"got '{cust_el.text}'"
        )

    # Validate ProfileID value
    prof_el = root.find(f".//{{{NS_CBC}}}ProfileID")
    if prof_el is not None and prof_el.text != XRECHNUNG_PROFILE_ID:
        errors.append(f"Invalid ProfileID: expected '{XRECHNUNG_PROFILE_ID}', got '{prof_el.text}'")

    if errors:
        logger.warning("xrechnung_validation_failed errors=%d", len(errors))
    return errors

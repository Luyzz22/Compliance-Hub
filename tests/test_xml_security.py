from __future__ import annotations

import pytest

from app.xml_security import (
    XMLSecurityError,
    append_xml_element,
    new_xml_root,
    parse_untrusted_xml,
    serialize_xml,
)


def test_xml_builder_escapes_text_and_attributes() -> None:
    root = new_xml_root("Export", {"tenant": 'a&b"c'})
    append_xml_element(root, "Value", text="<private>&data")

    serialized = serialize_xml(root, declaration=True)

    assert "a&amp;b&quot;c" in serialized
    assert "&lt;private&gt;&amp;data" in serialized
    parsed = parse_untrusted_xml(serialized)
    assert parsed.attrib["tenant"] == 'a&b"c'
    assert parsed.find("Value").text == "<private>&data"


@pytest.mark.parametrize(
    "document",
    [
        '<!DOCTYPE data [<!ENTITY local "secret">]><data>&local;</data>',
        '<!DOCTYPE data [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><data>&xxe;</data>',
    ],
)
def test_parser_rejects_dtd_and_entities(document: str) -> None:
    with pytest.raises(XMLSecurityError, match="forbidden constructs"):
        parse_untrusted_xml(document)


def test_parser_rejects_empty_and_oversized_documents() -> None:
    with pytest.raises(XMLSecurityError, match="empty or exceeds"):
        parse_untrusted_xml("")
    with pytest.raises(XMLSecurityError, match="empty or exceeds"):
        parse_untrusted_xml("<root />", max_bytes=4)


@pytest.mark.parametrize("document", [None, "<root>\ud800</root>"])
def test_parser_normalizes_invalid_input_errors(document: object) -> None:
    with pytest.raises(XMLSecurityError, match="valid UTF-8"):
        parse_untrusted_xml(document)  # type: ignore[arg-type]

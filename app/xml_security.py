"""Centralized XML construction and fail-closed parsing primitives."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from defusedxml import ElementTree as SafeElementTree
from defusedxml.common import DefusedXmlException

MAX_XML_DOCUMENT_BYTES = 5 * 1024 * 1024


class XMLSecurityError(ValueError):
    """An XML document is malformed, oversized, or contains forbidden constructs."""


def new_xml_root(tag: str, attributes: Mapping[str, str] | None = None) -> Any:
    """Create an element without importing an unsafe parser in application modules."""
    root = SafeElementTree.fromstring(
        b"<root />",
        forbid_dtd=True,
        forbid_entities=True,
        forbid_external=True,
    )
    root.tag = tag
    if attributes:
        root.attrib.update(dict(attributes))
    return root


def append_xml_element(
    parent: Any,
    tag: str,
    *,
    text: str | None = None,
    attributes: Mapping[str, str] | None = None,
) -> Any:
    """Append an escaped element to an existing tree."""
    child = parent.makeelement(tag, dict(attributes or {}))
    child.text = text
    parent.append(child)
    return child


def serialize_xml(root: Any, *, declaration: bool = False) -> str:
    """Serialize an application-created tree as Unicode XML."""
    return SafeElementTree.tostring(
        root,
        encoding="unicode",
        xml_declaration=declaration,
    )


def parse_untrusted_xml(
    document: str | bytes,
    *,
    max_bytes: int = MAX_XML_DOCUMENT_BYTES,
) -> Any:
    """Parse bounded XML while rejecting DTDs, entities, and external references."""
    try:
        if isinstance(document, str):
            raw = document.encode("utf-8")
        elif isinstance(document, bytes):
            raw = document
        else:
            raise TypeError("XML document must be text or bytes")
    except (TypeError, UnicodeError) as exc:
        raise XMLSecurityError("XML document is not valid UTF-8 text or bytes") from exc
    if not raw or len(raw) > max_bytes:
        raise XMLSecurityError("XML document is empty or exceeds the permitted size")
    try:
        return SafeElementTree.fromstring(
            raw,
            forbid_dtd=True,
            forbid_entities=True,
            forbid_external=True,
        )
    except (DefusedXmlException, SafeElementTree.ParseError, TypeError, ValueError) as exc:
        raise XMLSecurityError(
            "XML document is malformed or contains forbidden constructs"
        ) from exc

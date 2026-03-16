"""Norm-Nachweise für Board-Report-Audit-Records (EU AI Act / NIS2 / ISO 42001)."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import uuid4

from app.ai_governance_models import (
    NormEvidenceLink,
    NormEvidenceLinkCreate,
    NormFramework,
)

_links: dict[str, NormEvidenceLink] = {}


def create_links(
    tenant_id: str,
    audit_record_id: str,
    payloads: Iterable[NormEvidenceLinkCreate],
) -> list[NormEvidenceLink]:
    """Legt einen oder mehrere NormEvidenceLinks für einen Audit-Record an."""
    created: list[NormEvidenceLink] = []
    for body in payloads:
        link_id = str(uuid4())
        link = NormEvidenceLink(
            id=link_id,
            tenant_id=tenant_id,
            audit_record_id=audit_record_id,
            framework=body.framework,
            reference=body.reference,
            evidence_type=body.evidence_type,
            note=body.note,
        )
        _links[link_id] = link
        created.append(link)
    return created


def list_by_audit(tenant_id: str, audit_record_id: str) -> list[NormEvidenceLink]:
    """Alle Norm-Nachweise für einen Audit-Record (Tenant-isoliert)."""
    return [
        link
        for link in _links.values()
        if link.tenant_id == tenant_id and link.audit_record_id == audit_record_id
    ]


def query_by_norm(
    tenant_id: str,
    framework: NormFramework | None,
    reference: str | None,
) -> list[NormEvidenceLink]:
    """Norm-Nachweise nach Framework/Referenz filtern (Tenant-isoliert)."""
    matches = [link for link in _links.values() if link.tenant_id == tenant_id]
    if framework is not None:
        matches = [link for link in matches if link.framework == framework]
    if reference is not None:
        matches = [link for link in matches if link.reference == reference]
    return matches

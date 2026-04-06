"""Enterprise tenant/mandant context for advisor presets.

Separates:
- SaaS tenant (our platform customer)
- Client / Mandant (Kanzlei's end client in DATEV context)
- AI system reference (for EU AI Act / ISO 42001 scoping)

All fields are additive and backward compatible — callers that
don't supply client_id or system_id get the same behaviour as before.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class EnterpriseContext(BaseModel):
    """Identifies the organisational context for a preset invocation.

    Example (DATEV Kanzlei):
        tenant_id="kanzlei-mueller"
        client_id="mandant-12345"
        system_id=None

    Example (SAP S/4HANA):
        tenant_id="acme-gmbh"
        client_id=None
        system_id="HR-AI-Recruiting-01"
    """

    tenant_id: str = Field(
        default="",
        description="ComplianceHub SaaS tenant identifier",
    )
    client_id: str = Field(
        default="",
        description=(
            "Mandant / client identifier within the tenant "
            "(e.g. DATEV Mandantennummer, SAP Buchungskreis)"
        ),
    )
    system_id: str = Field(
        default="",
        description=(
            "Reference to a specific AI system or use case "
            "(e.g. EU AI Act Anhang-III ID, internal asset ID)"
        ),
    )

    def evidence_dict(self) -> dict[str, str]:
        """Return non-empty context fields for evidence payloads."""
        d: dict[str, str] = {}
        if self.tenant_id:
            d["tenant_id"] = self.tenant_id
        if self.client_id:
            d["client_id"] = self.client_id
        if self.system_id:
            d["system_id"] = self.system_id
        return d

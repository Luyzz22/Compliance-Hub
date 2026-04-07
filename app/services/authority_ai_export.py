from __future__ import annotations

from datetime import UTC, datetime

from app.ai_inventory_models import (
    AuthorityExportEnvelope,
    AuthorityExportResponse,
    AuthorityExportScope,
    AuthorityExportSystemRow,
)
from app.repositories.ai_inventory import AISystemInventoryRepository
from app.repositories.ai_systems import AISystemRepository


def build_authority_export(
    tenant_id: str,
    scope: AuthorityExportScope,
    ai_repo: AISystemRepository,
    inventory_repo: AISystemInventoryRepository,
) -> AuthorityExportResponse:
    systems = ai_repo.list_for_tenant(tenant_id)
    rows: list[AuthorityExportSystemRow] = []
    for sys in sorted(systems, key=lambda s: s.id):
        profile = inventory_repo.get_profile(tenant_id, sys.id)
        reg = inventory_repo.get_latest_register_entry(tenant_id, sys.id)
        if scope == AuthorityExportScope.initial and reg and reg.status == "registered":
            continue
        if scope == AuthorityExportScope.updates and (reg is None or reg.version <= 1):
            continue
        if scope == AuthorityExportScope.incident_context and not (reg and reg.reportable_incident):
            continue
        rows.append(
            AuthorityExportSystemRow(
                system_id=sys.id,
                name=sys.name,
                risk_level=sys.risk_level.value,
                ai_act_category=sys.ai_act_category.value,
                register_status=(reg.status if reg else "unknown"),
                eu_ai_act_scope=(profile.eu_ai_act_scope if profile else "review_needed"),
                reportable_incident=bool(reg.reportable_incident) if reg else False,
                reportable_change=bool(reg.reportable_change) if reg else False,
            )
        )
    now = datetime.now(UTC)
    envelope = AuthorityExportEnvelope(
        tenant_id=tenant_id,
        generated_at=now,
        scope=scope,
        systems=rows,
    )
    markdown_lines = [
        "# Behoerdenexport EU AI Act (Arbeitsstand)",
        "",
        f"- Mandant: {tenant_id}",
        f"- Zeitpunkt (UTC): {now.isoformat()}",
        f"- Umfang: {scope.value}",
        f"- Systeme im Export: {len(rows)}",
        "- Hinweis: keine Rechtsberatung, nur strukturierte Aufbereitung.",
        "",
    ]
    for row in rows:
        markdown_lines.append(
            f"- `{row.system_id}` {row.name}: {row.ai_act_category}, Register={row.register_status}, Scope={row.eu_ai_act_scope}"
        )
    return AuthorityExportResponse(export=envelope, markdown_de="\n".join(markdown_lines).strip() + "\n")

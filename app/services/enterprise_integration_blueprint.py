from __future__ import annotations

from datetime import UTC, datetime

from app.enterprise_integration_blueprint_models import (
    EnterpriseIntegrationBlueprintResponse,
    EnterpriseIntegrationBlueprintRow,
    EnterpriseIntegrationCandidate,
    EvidenceDomain,
    IntegrationBlueprintStatus,
    IntegrationReadinessPosture,
    SourceSystemType,
)
from app.enterprise_onboarding_models import EnterpriseOnboardingReadinessResponse

_DEFAULT_SECURITY_PREREQS: tuple[str, ...] = (
    "SSO-Konfiguration validiert",
    "RBAC-Rollenmapping auf Least-Privilege abgestimmt",
    "API-/Schnittstellenverantwortung (Data Owner + Technical Owner) dokumentiert",
    "Audit-Log-Nachvollziehbarkeit fuer Integrationsaenderungen aktiviert",
)

_SOURCE_DOMAIN_BASELINE: dict[SourceSystemType, tuple[EvidenceDomain, ...]] = {
    SourceSystemType.sap_s4hana: (
        EvidenceDomain.invoice,
        EvidenceDomain.approval,
        EvidenceDomain.vendor,
        EvidenceDomain.workflow_evidence,
        EvidenceDomain.access,
    ),
    SourceSystemType.sap_btp: (
        EvidenceDomain.workflow_evidence,
        EvidenceDomain.access,
        EvidenceDomain.policy_artifact,
    ),
    SourceSystemType.datev: (
        EvidenceDomain.invoice,
        EvidenceDomain.tax_export_context,
    ),
    SourceSystemType.ms_dynamics: (
        EvidenceDomain.invoice,
        EvidenceDomain.approval,
        EvidenceDomain.access,
        EvidenceDomain.vendor,
    ),
    SourceSystemType.generic_api: (
        EvidenceDomain.ai_inventory,
        EvidenceDomain.policy_artifact,
    ),
}


def build_enterprise_integration_blueprint_response(
    *,
    tenant_id: str,
    blueprint_rows: list[EnterpriseIntegrationBlueprintRow],
    onboarding: EnterpriseOnboardingReadinessResponse | None,
    include_markdown: bool,
) -> EnterpriseIntegrationBlueprintResponse:
    now = datetime.now(UTC)
    rows = blueprint_rows or _baseline_blueprints_from_onboarding(tenant_id, onboarding)
    blockers: list[str] = []
    if onboarding is not None:
        blockers.extend(f"Onboarding: {b.title_de}" for b in onboarding.blockers[:6])
    for row in rows:
        blockers.extend(row.blockers)
        if not row.security_prerequisites:
            blockers.append(f"{row.blueprint_id}: Security-Prerequisites sind noch nicht gepflegt.")
        if not row.data_owner or not row.technical_owner:
            blockers.append(f"{row.blueprint_id}: Data/Technical Owner fehlen.")
    dedup_blockers = list(dict.fromkeys(b.strip() for b in blockers if b and b.strip()))
    candidates = _rank_candidates(rows)
    readiness = _overall_readiness(rows, dedup_blockers)
    markdown = (
        _build_markdown(tenant_id, rows, candidates, dedup_blockers)
        if include_markdown
        else None
    )
    return EnterpriseIntegrationBlueprintResponse(
        tenant_id=tenant_id,
        generated_at_utc=now,
        readiness_status=readiness,
        blueprint_rows=rows,
        blockers=dedup_blockers[:25],
        top_enterprise_integration_candidates=candidates[:3],
        markdown_de=markdown,
    )


def _overall_readiness(
    rows: list[EnterpriseIntegrationBlueprintRow],
    blockers: list[str],
) -> IntegrationReadinessPosture:
    if any(r.integration_status == IntegrationBlueprintStatus.blocked for r in rows) or blockers:
        return IntegrationReadinessPosture.blocked
    if any(r.integration_status == IntegrationBlueprintStatus.ready_for_build for r in rows):
        return IntegrationReadinessPosture.integration_ready
    return IntegrationReadinessPosture.preparing


def _rank_candidates(
    rows: list[EnterpriseIntegrationBlueprintRow],
) -> list[EnterpriseIntegrationCandidate]:
    out: list[EnterpriseIntegrationCandidate] = []
    for row in rows:
        score = 50
        if row.integration_status == IntegrationBlueprintStatus.ready_for_build:
            score += 35
        elif row.integration_status == IntegrationBlueprintStatus.designing:
            score += 20
        elif row.integration_status == IntegrationBlueprintStatus.blocked:
            score -= 25
        score -= min(20, len(row.blockers) * 8)
        if row.data_owner and row.technical_owner:
            score += 10
        if row.security_prerequisites:
            score += 5
        recommendation = (
            "Als Erst-Connector priorisieren."
            if score >= 75
            else "Voraussetzungen nachziehen, dann in Build-Welle ueberfuehren."
            if score >= 50
            else "Derzeit nicht priorisieren; Blocker zuerst aufloesen."
        )
        out.append(
            EnterpriseIntegrationCandidate(
                blueprint_id=row.blueprint_id,
                source_system_type=row.source_system_type,
                score=max(0, min(100, score)),
                recommendation_de=recommendation,
                unlocked_evidence_domains=row.evidence_domains,
                blockers=row.blockers,
            )
        )
    return sorted(out, key=lambda c: c.score, reverse=True)


def _baseline_blueprints_from_onboarding(
    tenant_id: str,
    onboarding: EnterpriseOnboardingReadinessResponse | None,
) -> list[EnterpriseIntegrationBlueprintRow]:
    inferred_types: list[SourceSystemType] = []
    if onboarding is not None:
        for item in onboarding.integration_readiness:
            inferred_types.append(SourceSystemType(item.target_type.value))
    if not inferred_types:
        inferred_types = [
            SourceSystemType.sap_s4hana,
            SourceSystemType.datev,
            SourceSystemType.generic_api,
        ]
    out: list[EnterpriseIntegrationBlueprintRow] = []
    for idx, source in enumerate(dict.fromkeys(inferred_types)):
        out.append(
            EnterpriseIntegrationBlueprintRow(
                blueprint_id=f"default-{source.value}-{idx + 1}",
                tenant_id=tenant_id,
                source_system_type=source,
                evidence_domains=list(
                    _SOURCE_DOMAIN_BASELINE.get(source, (EvidenceDomain.workflow_evidence,))
                ),
                onboarding_readiness_ref="enterprise_onboarding_readiness",
                security_prerequisites=list(_DEFAULT_SECURITY_PREREQS),
                data_owner=None,
                technical_owner=None,
                integration_status=IntegrationBlueprintStatus.planned,
                blockers=[],
                notes="Baseline-Blueprint aus Onboarding-Readiness abgeleitet.",
            )
        )
    return out


def _build_markdown(
    tenant_id: str,
    rows: list[EnterpriseIntegrationBlueprintRow],
    candidates: list[EnterpriseIntegrationCandidate],
    blockers: list[str],
) -> str:
    lines = [
        "# Integration Blueprint Playbook (Arbeitsstand)",
        "",
        f"- Mandant: {tenant_id}",
        "- Zweck: SAP/ERP-Evidence-Konnektoren priorisieren (ohne Live-Credentials).",
        "",
        "## Empfohlener erster Connector",
    ]
    if candidates:
        top = candidates[0]
        lines.append(
            f"- {top.source_system_type.value} ({top.blueprint_id}) "
            f"mit Score {top.score}/100: {top.recommendation_de}"
        )
        domains = ", ".join(d.value for d in top.unlocked_evidence_domains) or "keine"
        lines.append(f"- Freigeschaltete Evidence-Domaenen: {domains}")
    else:
        lines.append("- Keine Kandidaten vorhanden.")
    lines.extend(["", "## Erforderliche Voraussetzungen"])
    for row in rows[:6]:
        if row.security_prerequisites:
            lines.append(f"- {row.blueprint_id}: " + "; ".join(row.security_prerequisites[:4]))
    lines.extend(["", "## Risiko-/Blocker-Sicht"])
    if blockers:
        for blocker in blockers[:10]:
            lines.append(f"- {blocker}")
    else:
        lines.append("- Keine kritischen Blocker dokumentiert.")
    lines.extend(["", "## Naechste Umsetzungsschritte"])
    lines.extend(
        [
            (
                "- Schnittstellenvertrag je Source-System "
                "(Objekte, Felder, Aktualisierungszyklus) festziehen."
            ),
            "- Evidence-Domain-Mapping mit Fachbereich und Revision validieren.",
            "- Build-Wave fuer priorisierten Connector planen (BTP/API, Testtenant, Audit-Trace).",
        ]
    )
    return "\n".join(lines).strip() + "\n"

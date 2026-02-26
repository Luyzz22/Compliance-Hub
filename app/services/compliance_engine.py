from __future__ import annotations

from datetime import datetime, timezone
import hashlib

from app.models import (
    ComplianceAction,
    DocumentIngestRequest,
    PlatformAuditFinding,
    Severity,
    TenantComplianceProfile,
)

DACH_COUNTRIES = {"DE", "AT", "CH"}


def default_tenant_profile(tenant_id: str) -> TenantComplianceProfile:
    return TenantComplianceProfile(
        tenant_id=tenant_id,
        data_residency_region="eu-central-1",
        requires_human_approval=True,
    )


def build_audit_hash(payload: DocumentIngestRequest) -> str:
    normalized = (
        f"{payload.tenant_id}|{payload.document_id}|{payload.document_type.value}|"
        f"{payload.supplier_name}|{payload.supplier_country}|{payload.amount_eur}|"
        f"{payload.e_invoice_format.value}|{payload.xml_valid_en16931}|"
        f"{payload.contains_personal_data}|{datetime.now(timezone.utc).isoformat()}"
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def derive_actions(
    payload: DocumentIngestRequest,
    profile: TenantComplianceProfile | None = None,
) -> list[ComplianceAction]:
    tenant_profile = profile or default_tenant_profile(payload.tenant_id)
    actions: list[ComplianceAction] = []

    if payload.document_type.value == "invoice":
        if payload.e_invoice_format not in tenant_profile.accepted_invoice_formats:
            actions.append(
                ComplianceAction(
                    action="request_einvoice_replacement",
                    module="e-invoicing",
                    severity=Severity.high,
                    rationale=(
                        "Nur XRechnung/ZUGFeRD erfüllen die künftige "
                        "B2B-E-Rechnungspflicht vollständig."
                    ),
                )
            )
        if not payload.xml_valid_en16931:
            actions.append(
                ComplianceAction(
                    action="block_auto_posting",
                    module="tax",
                    severity=Severity.high,
                    rationale=(
                        "EN-16931 Validierung fehlgeschlagen; "
                        "Buchung wird bis Korrektur gestoppt."
                    ),
                )
            )

    if payload.contains_personal_data:
        actions.append(
            ComplianceAction(
                action="create_or_update_ropa_entry",
                module="gdpr",
                severity=Severity.medium,
                rationale=(
                    "Dokument enthält personenbezogene Daten; "
                    "VVT-Eintrag wird aktualisiert."
                ),
            )
        )
        if tenant_profile.requires_human_approval:
            actions.append(
                ComplianceAction(
                    action="require_human_approval",
                    module="ai-governance",
                    severity=Severity.medium,
                    rationale=(
                        "EU-AI-Act-konformer Human-Review wird vor finaler "
                        "Freigabe erzwungen."
                    ),
                )
            )

    if payload.supplier_country.upper() not in DACH_COUNTRIES:
        actions.append(
            ComplianceAction(
                action="trigger_transfer_impact_assessment",
                module="gdpr",
                severity=Severity.high,
                rationale=(
                    "Drittstaatenbezug erkannt; "
                    "Transfer Impact Assessment erforderlich."
                ),
            )
        )

    actions.append(
        ComplianceAction(
            action="append_worm_archive_record",
            module="gobd",
            severity=Severity.low,
            rationale=(
                "Dokument wurde revisionssicher mit Hash und "
                "Zeitstempel archiviert."
            ),
        )
    )

    return actions


def calculate_tenant_score(
    action_history: list[ComplianceAction],
) -> tuple[int, str, list[str]]:
    score = 100
    critical = sum(1 for a in action_history if a.severity == Severity.critical)
    high = sum(1 for a in action_history if a.severity == Severity.high)
    medium = sum(1 for a in action_history if a.severity == Severity.medium)

    score -= critical * 20
    score -= high * 12
    score -= medium * 5
    score = max(score, 0)

    if score >= 85:
        risk = "low"
    elif score >= 65:
        risk = "medium"
    else:
        risk = "high"

    recommendations = [
        "DATEV-Export täglich automatisieren und Fehlbuchungen in <24h schließen.",
        "Monatliche Human-in-the-Loop-Freigabe für DSGVO-VVT fortführen.",
        "Quartalsweise Rezertifizierung der Auftragsverarbeiter durchführen.",
    ]

    if critical or high:
        recommendations.insert(
            0,
            "E-Rechnungs- und Drittland-Fehler mit Lieferanten-SLA beheben.",
        )

    return score, risk, recommendations


def run_platform_audit() -> list[PlatformAuditFinding]:
    """Static audit baseline for enterprise SaaS governance reporting."""
    return [
        PlatformAuditFinding(
            control_id="GOV-001",
            domain="Governance",
            status="implemented",
            severity=Severity.low,
            recommendation="Code-Ownership und PR-Review-Policy verbindlich halten.",
        ),
        PlatformAuditFinding(
            control_id="SEC-014",
            domain="Security",
            status="partially_implemented",
            severity=Severity.medium,
            recommendation="SBOM + Dependency-Scanning im CI ergänzen.",
        ),
        PlatformAuditFinding(
            control_id="REG-021",
            domain="Regulatory",
            status="implemented",
            severity=Severity.low,
            recommendation=(
                "GoBD Audit-Trail inkl. Hash/Timestamp regelmäßig stichprobenprüfen."
            ),
        ),
        PlatformAuditFinding(
            control_id="AI-009",
            domain="AI Governance",
            status="implemented",
            severity=Severity.medium,
            recommendation=(
                "Human-approval checkpoint bei personenbezogenen "
                "Daten beibehalten."
            ),
        ),
    ]

from __future__ import annotations

from datetime import datetime, timezone
import hashlib

from app.models import ComplianceAction, DocumentIngestRequest


def build_audit_hash(payload: DocumentIngestRequest) -> str:
    normalized = (
        f"{payload.tenant_id}|{payload.document_id}|{payload.document_type.value}|"
        f"{payload.supplier_name}|{payload.supplier_country}|{payload.amount_eur}|"
        f"{payload.e_invoice_format.value}|{payload.xml_valid_en16931}|"
        f"{payload.contains_personal_data}|{datetime.now(timezone.utc).isoformat()}"
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def derive_actions(payload: DocumentIngestRequest) -> list[ComplianceAction]:
    actions: list[ComplianceAction] = []

    if payload.document_type.value == "invoice":
        if payload.e_invoice_format.value not in {"xrechnung", "zugferd"}:
            actions.append(
                ComplianceAction(
                    action="request_einvoice_replacement",
                    module="e-invoicing",
                    severity="high",
                    rationale="Nur XRechnung/ZUGFeRD erfüllen die künftige B2B-E-Rechnungspflicht vollständig.",
                )
            )

        if not payload.xml_valid_en16931:
            actions.append(
                ComplianceAction(
                    action="block_auto_posting",
                    module="tax",
                    severity="high",
                    rationale="EN-16931 Validierung fehlgeschlagen; Buchung wird bis Korrektur gestoppt.",
                )
            )

    if payload.contains_personal_data:
        actions.append(
            ComplianceAction(
                action="create_or_update_ropa_entry",
                module="gdpr",
                severity="medium",
                rationale="Dokument enthält personenbezogene Daten; VVT-Eintrag wird aktualisiert.",
            )
        )

    if payload.supplier_country.upper() not in {"DE", "AT", "CH"}:
        actions.append(
            ComplianceAction(
                action="trigger_transfer_impact_assessment",
                module="gdpr",
                severity="medium",
                rationale="Drittstaatenbezug erkannt; Transfer Impact Assessment erforderlich.",
            )
        )

    actions.append(
        ComplianceAction(
            action="append_worm_archive_record",
            module="gobd",
            severity="low",
            rationale="Dokument wurde revisionssicher mit Hash und Zeitstempel archiviert.",
        )
    )

    return actions


def calculate_tenant_score(action_history: list[ComplianceAction]) -> tuple[int, str, list[str]]:
    score = 100
    high = sum(1 for a in action_history if a.severity == "high")
    medium = sum(1 for a in action_history if a.severity == "medium")

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
        "Datev-Export täglich automatisieren und Fehlbuchungen in <24h schließen.",
        "Monatliche Human-in-the-Loop-Freigabe für DSGVO-VVT fortführen.",
    ]

    if high:
        recommendations.insert(0, "E-Rechnungs-Validierungsfehler mit Lieferanten-SLA beheben.")

    return score, risk, recommendations

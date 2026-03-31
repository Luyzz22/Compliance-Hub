"""Payload mappers — translate internal GRC artefacts to connector payloads.

Two payload families:
- **DATEV-friendly**: compact, Mandant-oriented, German labels where useful.
- **SAP/BTP-friendly**: structured JSON envelopes with stable IDs and
  lifecycle/readiness/GRC fields.

All payloads include schema_version, tenant/client/system refs, source
record IDs, timestamps, and machine-readable tags.  No raw prompts or
PII beyond business-safe identifiers.
"""

from __future__ import annotations

from typing import Any

from app.grc.models import (
    AiRiskAssessment,
    AiSystem,
    Iso42001GapRecord,
    Nis2ObligationRecord,
)


def _base_envelope(
    *,
    schema_version: str,
    record_type: str,
    tenant_id: str,
    client_id: str,
    system_id: str,
    source_id: str,
    created_at: str,
    tags: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "record_type": record_type,
        "tenant_id": tenant_id,
        "client_id": client_id,
        "system_id": system_id,
        "source_id": source_id,
        "created_at": created_at,
        "tags": tags,
    }


# ── AI Risk Assessment ────────────────────────────────────────────────


def map_risk_datev(rec: AiRiskAssessment) -> dict[str, Any]:
    return {
        **_base_envelope(
            schema_version="v1",
            record_type="Risikobewertung_KI",
            tenant_id=rec.tenant_id,
            client_id=rec.client_id,
            system_id=rec.system_id,
            source_id=rec.id,
            created_at=rec.created_at,
            tags=rec.tags,
        ),
        "risikokategorie": rec.risk_category,
        "anwendungsfall": rec.use_case_type,
        "hochrisiko_wahrscheinlichkeit": rec.high_risk_likelihood,
        "anhang_iii_kategorie": rec.annex_iii_category,
        "konformitaetsbewertung_erforderlich": (rec.conformity_assessment_required),
        "status": rec.status.value,
        "naechste_schritte": rec.suggested_next_steps,
    }


def map_risk_sap(rec: AiRiskAssessment) -> dict[str, Any]:
    return {
        **_base_envelope(
            schema_version="v1",
            record_type="ai_risk_assessment",
            tenant_id=rec.tenant_id,
            client_id=rec.client_id,
            system_id=rec.system_id,
            source_id=rec.id,
            created_at=rec.created_at,
            tags=rec.tags,
        ),
        "risk_category": rec.risk_category,
        "use_case_type": rec.use_case_type,
        "high_risk_likelihood": rec.high_risk_likelihood,
        "annex_iii_category": rec.annex_iii_category,
        "conformity_assessment_required": (rec.conformity_assessment_required),
        "status": rec.status.value,
        "suggested_next_steps": rec.suggested_next_steps,
    }


# ── NIS2 Obligation ──────────────────────────────────────────────────


def map_nis2_datev(rec: Nis2ObligationRecord) -> dict[str, Any]:
    return {
        **_base_envelope(
            schema_version="v1",
            record_type="NIS2_Pflicht",
            tenant_id=rec.tenant_id,
            client_id=rec.client_id,
            system_id=rec.system_id,
            source_id=rec.id,
            created_at=rec.created_at,
            tags=rec.tags,
        ),
        "nis2_entitaetstyp": rec.nis2_entity_type,
        "pflicht_tags": rec.obligation_tags,
        "meldefristen": rec.reporting_deadlines,
        "rolle": rec.entity_role,
        "sektor": rec.sector,
        "status": rec.status.value,
        "naechste_schritte": rec.suggested_next_steps,
    }


def map_nis2_sap(rec: Nis2ObligationRecord) -> dict[str, Any]:
    return {
        **_base_envelope(
            schema_version="v1",
            record_type="nis2_obligation",
            tenant_id=rec.tenant_id,
            client_id=rec.client_id,
            system_id=rec.system_id,
            source_id=rec.id,
            created_at=rec.created_at,
            tags=rec.tags,
        ),
        "nis2_entity_type": rec.nis2_entity_type,
        "obligation_tags": rec.obligation_tags,
        "reporting_deadlines": rec.reporting_deadlines,
        "entity_role": rec.entity_role,
        "sector": rec.sector,
        "status": rec.status.value,
        "suggested_next_steps": rec.suggested_next_steps,
    }


# ── ISO 42001 Gap ────────────────────────────────────────────────────


def map_gap_datev(rec: Iso42001GapRecord) -> dict[str, Any]:
    return {
        **_base_envelope(
            schema_version="v1",
            record_type="ISO42001_Luecke",
            tenant_id=rec.tenant_id,
            client_id=rec.client_id,
            system_id=rec.system_id,
            source_id=rec.id,
            created_at=rec.created_at,
            tags=rec.tags,
        ),
        "kontroll_familien": rec.control_families,
        "schweregrad": rec.gap_severity,
        "iso27001_ueberschneidung": rec.iso27001_overlap,
        "aktuelle_massnahmen": rec.current_measures_summary,
        "status": rec.status.value,
        "naechste_schritte": rec.suggested_next_steps,
    }


def map_gap_sap(rec: Iso42001GapRecord) -> dict[str, Any]:
    return {
        **_base_envelope(
            schema_version="v1",
            record_type="iso42001_gap",
            tenant_id=rec.tenant_id,
            client_id=rec.client_id,
            system_id=rec.system_id,
            source_id=rec.id,
            created_at=rec.created_at,
            tags=rec.tags,
        ),
        "control_families": rec.control_families,
        "gap_severity": rec.gap_severity,
        "iso27001_overlap": rec.iso27001_overlap,
        "current_measures_summary": rec.current_measures_summary,
        "status": rec.status.value,
        "suggested_next_steps": rec.suggested_next_steps,
    }


# ── Board Report Summary ─────────────────────────────────────────────


def map_board_report_datev(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "v1",
        "record_type": "Mandanten_Board_Bericht",
        "tenant_id": report.get("tenant_id", ""),
        "client_id": report.get("client_id", ""),
        "berichtszeitraum": report.get("reporting_period", ""),
        "systeme_enthalten": report.get("systems_included", 0),
        "highlights": report.get("highlights", []),
        "created_at": report.get("created_at", ""),
        "source_id": report.get("id", ""),
        "tags": [],
    }


def map_board_report_sap(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "v1",
        "record_type": "board_report_summary",
        "tenant_id": report.get("tenant_id", ""),
        "client_id": report.get("client_id", ""),
        "reporting_period": report.get("reporting_period", ""),
        "systems_included": report.get("systems_included", 0),
        "highlights": report.get("highlights", []),
        "created_at": report.get("created_at", ""),
        "source_id": report.get("id", ""),
        "tags": [],
    }


# ── AI System Readiness Snapshot ─────────────────────────────────────


def map_readiness_datev(sys: AiSystem) -> dict[str, Any]:
    return {
        **_base_envelope(
            schema_version="v1",
            record_type="KI_System_Bereitschaft",
            tenant_id=sys.tenant_id,
            client_id=sys.client_id,
            system_id=sys.system_id,
            source_id=sys.id,
            created_at=sys.updated_at,
            tags=sys.tags,
        ),
        "lebenszyklus_stufe": sys.lifecycle_stage.value,
        "bereitschaftsgrad": sys.readiness_level.value,
        "ki_act_klassifikation": sys.ai_act_classification.value,
        "nis2_relevant": sys.nis2_relevant,
        "iso42001_im_scope": sys.iso42001_in_scope,
        "zieldatum_go_live": sys.go_live_target_date,
        "letzte_pruefung": sys.last_reviewed_at,
    }


def map_readiness_sap(sys: AiSystem) -> dict[str, Any]:
    return {
        **_base_envelope(
            schema_version="v1",
            record_type="ai_system_readiness_snapshot",
            tenant_id=sys.tenant_id,
            client_id=sys.client_id,
            system_id=sys.system_id,
            source_id=sys.id,
            created_at=sys.updated_at,
            tags=sys.tags,
        ),
        "lifecycle_stage": sys.lifecycle_stage.value,
        "readiness_level": sys.readiness_level.value,
        "ai_act_classification": sys.ai_act_classification.value,
        "nis2_relevant": sys.nis2_relevant,
        "iso42001_in_scope": sys.iso42001_in_scope,
        "go_live_target_date": sys.go_live_target_date,
        "last_reviewed_at": sys.last_reviewed_at,
    }


# ── Dispatcher helper ────────────────────────────────────────────────

_MAPPER_REGISTRY: dict[
    tuple[str, str],
    Any,
] = {
    ("ai_risk_assessment", "datev_export"): map_risk_datev,
    ("ai_risk_assessment", "sap_btp"): map_risk_sap,
    ("ai_risk_assessment", "generic_partner_api"): map_risk_sap,
    ("nis2_obligation", "datev_export"): map_nis2_datev,
    ("nis2_obligation", "sap_btp"): map_nis2_sap,
    ("nis2_obligation", "generic_partner_api"): map_nis2_sap,
    ("iso42001_gap", "datev_export"): map_gap_datev,
    ("iso42001_gap", "sap_btp"): map_gap_sap,
    ("iso42001_gap", "generic_partner_api"): map_gap_sap,
    ("board_report_summary", "datev_export"): map_board_report_datev,
    ("board_report_summary", "sap_btp"): map_board_report_sap,
    ("board_report_summary", "generic_partner_api"): map_board_report_sap,
    ("ai_system_readiness_snapshot", "datev_export"): map_readiness_datev,
    ("ai_system_readiness_snapshot", "sap_btp"): map_readiness_sap,
    ("ai_system_readiness_snapshot", "generic_partner_api"): (map_readiness_sap),
}


def resolve_mapper(
    payload_type: str,
    target: str,
) -> Any | None:
    """Return the mapper function for a (payload_type, target) pair."""
    return _MAPPER_REGISTRY.get((payload_type, target))

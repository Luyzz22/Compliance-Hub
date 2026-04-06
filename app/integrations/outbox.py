"""Outbox helper — enqueue integration jobs from internal GRC artefacts.

Provides a single entry-point for the anti-corruption layer: internal
domain events call ``enqueue_for_entity`` and the outbox decides
whether to create an IntegrationJob based on opt-in config.
"""

from __future__ import annotations

from app.integrations.models import (
    IntegrationJob,
    IntegrationPayloadType,
    IntegrationTarget,
)
from app.integrations.store import enqueue_job

ENTITY_TYPE_TO_PAYLOAD: dict[str, IntegrationPayloadType] = {
    "AiRiskAssessment": IntegrationPayloadType.ai_risk_assessment,
    "Nis2ObligationRecord": IntegrationPayloadType.nis2_obligation,
    "Iso42001GapRecord": IntegrationPayloadType.iso42001_gap,
    "ClientBoardReport": IntegrationPayloadType.board_report_summary,
    "AiSystemReadinessSnapshot": (IntegrationPayloadType.ai_system_readiness_snapshot),
    "MandantComplianceDossier": (IntegrationPayloadType.mandant_compliance_dossier),
}


def enqueue_for_entity(
    *,
    entity_type: str,
    entity_id: str,
    tenant_id: str,
    client_id: str = "",
    system_id: str = "",
    target: IntegrationTarget = IntegrationTarget.generic_partner_api,
    trace_id: str = "",
    payload: dict | None = None,
) -> IntegrationJob | None:
    """Create an outbox job for the given entity, if the type is mapped."""
    payload_type = ENTITY_TYPE_TO_PAYLOAD.get(entity_type)
    if payload_type is None:
        return None

    idem_key = f"{target.value}:{entity_type}:{entity_id}"

    job = IntegrationJob(
        tenant_id=tenant_id,
        client_id=client_id,
        system_id=system_id,
        target=target,
        payload_type=payload_type,
        idempotency_key=idem_key,
        source_entity_type=entity_type,
        source_entity_id=entity_id,
        trace_id=trace_id,
        payload=payload or {},
    )
    return enqueue_job(job)


def enqueue_mandant_dossier(
    *,
    tenant_id: str,
    client_id: str,
    period: str = "",
    export_version: int = 1,
    trace_id: str = "",
    mandant_kurzname: str = "",
    branche: str = "",
) -> IntegrationJob | None:
    """Create an outbox job for a Mandanten-Compliance-Dossier export."""
    idem_key = (
        f"datev_export:MandantComplianceDossier:{tenant_id}:{client_id}:{period}:v{export_version}"
    )
    job = IntegrationJob(
        tenant_id=tenant_id,
        client_id=client_id,
        target=IntegrationTarget.datev_export,
        payload_type=IntegrationPayloadType.mandant_compliance_dossier,
        idempotency_key=idem_key,
        source_entity_type="MandantComplianceDossier",
        source_entity_id=f"{tenant_id}:{client_id}:{period}",
        trace_id=trace_id,
        period=period,
        export_version=export_version,
        payload={
            "mandant_kurzname": mandant_kurzname,
            "branche": branche,
        },
    )
    return enqueue_job(job)

from __future__ import annotations

from pydantic import BaseModel, Field

from app.enterprise_connector_runtime_models import (
    ConnectorManualSyncResponse,
    ConnectorRuntimeStatusResponse,
    ConnectorSyncStatus,
)
from app.enterprise_integration_blueprint_models import EvidenceDomain
from app.repositories.enterprise_connector_runtime import EnterpriseConnectorRuntimeRepository


class _IncomingEvidenceRecord(BaseModel):
    record_id: str = Field(..., min_length=1, max_length=255)
    domain: str = Field(..., min_length=1, max_length=64)
    amount_eur: float | None = None
    approver: str | None = None
    status: str | None = None
    source_ref: str | None = None


class _IncomingPayload(BaseModel):
    source_system_type: str = "generic_api"
    records: list[_IncomingEvidenceRecord]


def build_connector_runtime_status(
    tenant_id: str,
    *,
    actor: str,
    repo: EnterpriseConnectorRuntimeRepository,
) -> ConnectorRuntimeStatusResponse:
    instance = repo.get_or_create_instance(tenant_id, actor=actor)
    return ConnectorRuntimeStatusResponse(
        tenant_id=tenant_id,
        connector_instance=instance,
        last_sync_result=repo.get_last_sync_result(tenant_id),
    )


def run_manual_connector_sync(
    tenant_id: str,
    *,
    actor: str,
    repo: EnterpriseConnectorRuntimeRepository,
) -> ConnectorManualSyncResponse:
    instance = repo.get_or_create_instance(tenant_id, actor=actor)
    repo.mark_sync_running(tenant_id, actor=actor)
    sync_run = repo.create_sync_run(tenant_id, instance.connector_instance_id)

    # Wave 57 choice: generic_api as first live connector skeleton.
    incoming = _IncomingPayload(
        source_system_type="generic_api",
        records=[
            {
                "record_id": "inv-1001",
                "domain": "invoice",
                "amount_eur": 18420.5,
                "status": "posted",
                "source_ref": "ERP-INV-1001",
            },
            {
                "record_id": "apr-5202",
                "domain": "approval",
                "approver": "maria.schulz@example.org",
                "status": "approved",
                "source_ref": "WF-5202",
            },
        ],
    )
    normalized_preview: list[dict[str, str]] = []
    ingested = 0
    for rec in incoming.records:
        if rec.domain not in {EvidenceDomain.invoice.value, EvidenceDomain.approval.value}:
            continue
        normalized = {
            "external_record_id": rec.record_id,
            "evidence_domain": rec.domain,
            "status": rec.status or "unknown",
            "source_ref": rec.source_ref or rec.record_id,
        }
        repo.upsert_evidence_record(
            tenant_id=tenant_id,
            connector_instance_id=instance.connector_instance_id,
            sync_run_id=sync_run.sync_run_id,
            evidence_domain=rec.domain,
            external_record_id=rec.record_id,
            source_payload=rec.model_dump(mode="json"),
            normalized_payload=normalized,
        )
        normalized_preview.append(
            {
                "record_id": rec.record_id,
                "domain": rec.domain,
                "status": normalized["status"],
            }
        )
        ingested += 1

    summary = (
        "Manueller Connector-Sync erfolgreich: "
        f"{ingested} Datensätze für invoice/approval normalisiert."
    )
    sync_result, connector = repo.finalize_sync_run(
        tenant_id=tenant_id,
        sync_run_id=sync_run.sync_run_id,
        status=ConnectorSyncStatus.success,
        records_ingested=ingested,
        last_error=None,
        summary_de=summary,
        details_json={
            "records_ingested": ingested,
            "source_system_type": incoming.source_system_type,
        },
        actor=actor,
    )
    return ConnectorManualSyncResponse(
        tenant_id=tenant_id,
        connector_instance=connector,
        sync_result=sync_result,
        normalized_records_preview=normalized_preview,
    )

from __future__ import annotations

from fastapi import HTTPException, status
from pydantic import BaseModel, Field

from app.enterprise_connector_runtime_models import (
    ConnectorConnectionStatus,
    ConnectorFailureCategory,
    ConnectorHealthSnapshot,
    ConnectorManualSyncResponse,
    ConnectorRuntimeStatusResponse,
    ConnectorSyncHistoryResponse,
    ConnectorSyncResult,
    SyncRunLifecycle,
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
    health = repo.build_health_snapshot(tenant_id, instance)
    return ConnectorRuntimeStatusResponse(
        tenant_id=tenant_id,
        connector_instance=instance,
        last_sync_result=repo.get_last_sync_result(tenant_id),
        health=health,
    )


def get_connector_health_snapshot(
    tenant_id: str,
    *,
    actor: str,
    repo: EnterpriseConnectorRuntimeRepository,
) -> ConnectorHealthSnapshot:
    instance = repo.get_or_create_instance(tenant_id, actor=actor)
    return repo.build_health_snapshot(tenant_id, instance)


def list_connector_sync_history(
    tenant_id: str,
    *,
    actor: str,
    repo: EnterpriseConnectorRuntimeRepository,
    limit: int = 30,
) -> ConnectorSyncHistoryResponse:
    repo.get_or_create_instance(tenant_id, actor=actor)
    runs = repo.list_sync_runs(tenant_id, limit=limit)
    return ConnectorSyncHistoryResponse(tenant_id=tenant_id, runs=runs)


def get_latest_connector_failure(
    tenant_id: str,
    *,
    actor: str,
    repo: EnterpriseConnectorRuntimeRepository,
) -> ConnectorSyncResult | None:
    repo.get_or_create_instance(tenant_id, actor=actor)
    for run in repo.list_sync_runs(tenant_id, limit=50):
        if run.sync_status == SyncRunLifecycle.failed and run.finished_at_utc is not None:
            return run
    return None


def run_manual_connector_sync(
    tenant_id: str,
    *,
    actor: str,
    repo: EnterpriseConnectorRuntimeRepository,
) -> ConnectorManualSyncResponse:
    return _execute_connector_sync(
        tenant_id,
        actor=actor,
        repo=repo,
        retry_of_sync_run_id=None,
    )


def retry_connector_sync(
    tenant_id: str,
    *,
    actor: str,
    repo: EnterpriseConnectorRuntimeRepository,
    sync_run_id: str | None,
) -> ConnectorManualSyncResponse:
    if sync_run_id:
        target = repo.get_sync_run(tenant_id, sync_run_id)
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sync run not found for tenant",
            )
        if target.finished_at_utc is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Sync run still active; retry not allowed",
            )
        if target.sync_status not in (
            SyncRunLifecycle.failed,
            SyncRunLifecycle.partial_success,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only failed or partial_success runs can be retried safely via this action",
            )
        parent_id = target.sync_run_id
    else:
        target = repo.get_last_retryable_sync_run(tenant_id)
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No failed or partial_success sync run available to retry",
            )
        parent_id = target.sync_run_id

    return _execute_connector_sync(
        tenant_id,
        actor=actor,
        repo=repo,
        retry_of_sync_run_id=parent_id,
    )


def _stub_incoming_payload() -> _IncomingPayload:
    """Deterministic skeleton payload: two valid domains (invoice, approval)."""
    return _IncomingPayload(
        source_system_type="generic_api",
        records=[
            _IncomingEvidenceRecord(
                record_id="inv-1001",
                domain="invoice",
                amount_eur=18420.5,
                status="posted",
                source_ref="ERP-INV-1001",
            ),
            _IncomingEvidenceRecord(
                record_id="apr-5202",
                domain="approval",
                approver="maria.schulz@example.org",
                status="approved",
                source_ref="WF-5202",
            ),
        ],
    )


def _execute_connector_sync(
    tenant_id: str,
    *,
    actor: str,
    repo: EnterpriseConnectorRuntimeRepository,
    retry_of_sync_run_id: str | None,
) -> ConnectorManualSyncResponse:
    instance = repo.get_or_create_instance(tenant_id, actor=actor)
    repo.mark_sync_running(tenant_id, actor=actor)
    sync_run = repo.create_sync_run(
        tenant_id,
        instance.connector_instance_id,
        retry_of_sync_run_id=retry_of_sync_run_id,
    )
    repo.transition_sync_run_to_running(tenant_id, sync_run.sync_run_id)

    if instance.connection_status == ConnectorConnectionStatus.not_configured:
        summary = (
            "Sync abgebrochen: Verbindung ist nicht konfiguriert. "
            "Zugangsdaten und Endpunkte im Integrations-Setup hinterlegen."
        )
        sync_result, connector = repo.finalize_sync_run(
            tenant_id=tenant_id,
            sync_run_id=sync_run.sync_run_id,
            lifecycle=SyncRunLifecycle.failed,
            records_received=0,
            records_normalized=0,
            records_rejected=0,
            last_error="connection_not_configured",
            failure_category=ConnectorFailureCategory.auth_config,
            summary_de=summary,
            details_json={"safe_retry": True, "requires_config_fix": True},
            actor=actor,
        )
        return ConnectorManualSyncResponse(
            tenant_id=tenant_id,
            connector_instance=connector,
            sync_result=sync_result,
            normalized_records_preview=[],
        )

    if instance.connection_status == ConnectorConnectionStatus.degraded:
        summary = (
            "Sync fehlgeschlagen: Quellsystem temporär nicht erreichbar oder degradiert. "
            "Später erneut versuchen."
        )
        sync_result, connector = repo.finalize_sync_run(
            tenant_id=tenant_id,
            sync_run_id=sync_run.sync_run_id,
            lifecycle=SyncRunLifecycle.failed,
            records_received=0,
            records_normalized=0,
            records_rejected=0,
            last_error="source_degraded",
            failure_category=ConnectorFailureCategory.source_unavailable,
            summary_de=summary,
            details_json={"safe_retry": True},
            actor=actor,
        )
        return ConnectorManualSyncResponse(
            tenant_id=tenant_id,
            connector_instance=connector,
            sync_result=sync_result,
            normalized_records_preview=[],
        )

    incoming = _stub_incoming_payload()
    normalized_preview: list[dict[str, str]] = []
    received = 0
    normalized = 0
    rejected = 0
    mapping_errors: list[str] = []

    for rec in incoming.records:
        received += 1
        if rec.domain not in {EvidenceDomain.invoice.value, EvidenceDomain.approval.value}:
            rejected += 1
            mapping_errors.append(f"unsupported_domain:{rec.record_id}")
            continue
        norm = {
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
            normalized_payload=norm,
        )
        normalized_preview.append(
            {
                "record_id": rec.record_id,
                "domain": rec.domain,
                "status": norm["status"],
            }
        )
        normalized += 1

    if rejected and normalized == 0:
        summary = (
            "Sync fehlgeschlagen: alle Datensätze verworfen (Validierung/Mapping). "
            "Payload gegen Blueprint prüfen."
        )
        sync_result, connector = repo.finalize_sync_run(
            tenant_id=tenant_id,
            sync_run_id=sync_run.sync_run_id,
            lifecycle=SyncRunLifecycle.failed,
            records_received=received,
            records_normalized=normalized,
            records_rejected=rejected,
            last_error="all_records_rejected",
            failure_category=ConnectorFailureCategory.payload_validation,
            summary_de=summary,
            details_json={
                "errors": mapping_errors[:50],
                "safe_retry": False,
                "requires_manual_review": True,
            },
            actor=actor,
        )
        return ConnectorManualSyncResponse(
            tenant_id=tenant_id,
            connector_instance=connector,
            sync_result=sync_result,
            normalized_records_preview=normalized_preview,
        )

    if rejected:
        summary = (
            f"Sync teilweise erfolgreich: {normalized} normalisiert, {rejected} verworfen. "
            "Abgelehnte Einträge prüfen; Retry ist idempotent."
        )
        sync_result, connector = repo.finalize_sync_run(
            tenant_id=tenant_id,
            sync_run_id=sync_run.sync_run_id,
            lifecycle=SyncRunLifecycle.partial_success,
            records_received=received,
            records_normalized=normalized,
            records_rejected=rejected,
            last_error="partial_reject",
            failure_category=ConnectorFailureCategory.normalization_mapping,
            summary_de=summary,
            details_json={
                "errors": mapping_errors[:50],
                "safe_retry": True,
            },
            actor=actor,
        )
        return ConnectorManualSyncResponse(
            tenant_id=tenant_id,
            connector_instance=connector,
            sync_result=sync_result,
            normalized_records_preview=normalized_preview,
        )

    summary = (
        "Manueller Connector-Sync erfolgreich: "
        f"{normalized} Datensätze für invoice/approval normalisiert."
    )
    sync_result, connector = repo.finalize_sync_run(
        tenant_id=tenant_id,
        sync_run_id=sync_run.sync_run_id,
        lifecycle=SyncRunLifecycle.succeeded,
        records_received=received,
        records_normalized=normalized,
        records_rejected=rejected,
        last_error=None,
        failure_category=None,
        summary_de=summary,
        details_json={
            "records_normalized": normalized,
            "source_system_type": incoming.source_system_type,
            "retry_of_sync_run_id": retry_of_sync_run_id,
        },
        actor=actor,
    )
    return ConnectorManualSyncResponse(
        tenant_id=tenant_id,
        connector_instance=connector,
        sync_result=sync_result,
        normalized_records_preview=normalized_preview,
    )

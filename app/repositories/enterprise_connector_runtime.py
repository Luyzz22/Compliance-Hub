from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.enterprise_connector_runtime_models import (
    ConnectorConnectionStatus,
    ConnectorFailureCategory,
    ConnectorHealthSnapshot,
    ConnectorInstanceRuntime,
    ConnectorInstanceSyncState,
    ConnectorSyncResult,
    SyncRunLifecycle,
)
from app.enterprise_integration_blueprint_models import EvidenceDomain, SourceSystemType
from app.models_db import (
    EnterpriseConnectorEvidenceRecordDB,
    EnterpriseConnectorInstanceDB,
    EnterpriseConnectorSyncRunDB,
)


def _normalize_instance_sync_state(raw: str) -> ConnectorInstanceSyncState:
    if raw == "success":
        return ConnectorInstanceSyncState.succeeded
    return ConnectorInstanceSyncState(raw)


def _normalize_run_lifecycle(raw: str) -> SyncRunLifecycle:
    if raw == "success":
        return SyncRunLifecycle.succeeded
    return SyncRunLifecycle(raw)


class EnterpriseConnectorRuntimeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def count_evidence_records(self, tenant_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(EnterpriseConnectorEvidenceRecordDB)
            .where(EnterpriseConnectorEvidenceRecordDB.tenant_id == tenant_id)
        )
        return int(self._session.execute(stmt).scalar_one())

    def get_or_create_instance(self, tenant_id: str, actor: str) -> ConnectorInstanceRuntime:
        stmt = select(EnterpriseConnectorInstanceDB).where(
            EnterpriseConnectorInstanceDB.tenant_id == tenant_id
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            now = datetime.now(UTC)
            row = EnterpriseConnectorInstanceDB(
                connector_instance_id=f"conn-{tenant_id}-generic-api",
                tenant_id=tenant_id,
                source_system_type=SourceSystemType.generic_api.value,
                connection_status=ConnectorConnectionStatus.connected.value,
                sync_status=ConnectorInstanceSyncState.idle.value,
                enabled_evidence_domains={
                    "domains": [EvidenceDomain.approval.value, EvidenceDomain.invoice.value]
                },
                last_sync_at=None,
                last_error=None,
                updated_at_utc=now,
                updated_by=actor,
            )
            self._session.add(row)
            self._session.commit()
            self._session.refresh(row)
        return self._to_instance(row)

    def mark_sync_running(self, tenant_id: str, actor: str) -> ConnectorInstanceRuntime:
        row = self._get_instance_row(tenant_id)
        row.sync_status = ConnectorInstanceSyncState.running.value
        row.last_error = None
        row.updated_at_utc = datetime.now(UTC)
        row.updated_by = actor
        self._session.commit()
        self._session.refresh(row)
        return self._to_instance(row)

    def upsert_evidence_record(
        self,
        *,
        tenant_id: str,
        connector_instance_id: str,
        sync_run_id: str,
        evidence_domain: str,
        external_record_id: str,
        source_payload: dict,
        normalized_payload: dict,
    ) -> None:
        stmt = select(EnterpriseConnectorEvidenceRecordDB).where(
            EnterpriseConnectorEvidenceRecordDB.tenant_id == tenant_id,
            EnterpriseConnectorEvidenceRecordDB.connector_instance_id == connector_instance_id,
            EnterpriseConnectorEvidenceRecordDB.evidence_domain == evidence_domain,
            EnterpriseConnectorEvidenceRecordDB.external_record_id == external_record_id,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        now = datetime.now(UTC)
        if row is None:
            row = EnterpriseConnectorEvidenceRecordDB(
                tenant_id=tenant_id,
                connector_instance_id=connector_instance_id,
                sync_run_id=sync_run_id,
                evidence_domain=evidence_domain,
                external_record_id=external_record_id,
                source_payload=source_payload,
                normalized_payload=normalized_payload,
                ingested_at_utc=now,
            )
            self._session.add(row)
        else:
            row.sync_run_id = sync_run_id
            row.source_payload = source_payload
            row.normalized_payload = normalized_payload
            row.ingested_at_utc = now

    def create_sync_run(
        self,
        tenant_id: str,
        connector_instance_id: str,
        *,
        retry_of_sync_run_id: str | None = None,
    ) -> ConnectorSyncResult:
        now = datetime.now(UTC)
        row = EnterpriseConnectorSyncRunDB(
            sync_run_id=f"sync-{tenant_id}-{int(now.timestamp() * 1000)}",
            tenant_id=tenant_id,
            connector_instance_id=connector_instance_id,
            sync_status=SyncRunLifecycle.queued.value,
            started_at_utc=now,
            finished_at_utc=None,
            records_ingested=0,
            records_received=0,
            records_normalized=0,
            records_rejected=0,
            duration_ms=None,
            failure_category=None,
            retry_of_sync_run_id=retry_of_sync_run_id,
            last_error=None,
            summary_de="Sync in Warteschlange.",
            details_json={},
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_sync_result(row)

    def transition_sync_run_to_running(
        self, tenant_id: str, sync_run_id: str
    ) -> ConnectorSyncResult:
        stmt = select(EnterpriseConnectorSyncRunDB).where(
            EnterpriseConnectorSyncRunDB.tenant_id == tenant_id,
            EnterpriseConnectorSyncRunDB.sync_run_id == sync_run_id,
        )
        run = self._session.execute(stmt).scalar_one()
        run.sync_status = SyncRunLifecycle.running.value
        run.summary_de = "Synchronisation läuft."
        self._session.commit()
        self._session.refresh(run)
        return self._to_sync_result(run)

    def finalize_sync_run(
        self,
        *,
        tenant_id: str,
        sync_run_id: str,
        lifecycle: SyncRunLifecycle,
        records_received: int,
        records_normalized: int,
        records_rejected: int,
        last_error: str | None,
        failure_category: ConnectorFailureCategory | None,
        summary_de: str,
        details_json: dict,
        actor: str,
    ) -> tuple[ConnectorSyncResult, ConnectorInstanceRuntime]:
        stmt = select(EnterpriseConnectorSyncRunDB).where(
            EnterpriseConnectorSyncRunDB.tenant_id == tenant_id,
            EnterpriseConnectorSyncRunDB.sync_run_id == sync_run_id,
        )
        run = self._session.execute(stmt).scalar_one()
        now = datetime.now(UTC)
        started = run.started_at_utc
        if started.tzinfo is None:
            started = started.replace(tzinfo=UTC)
        duration_ms = int((now - started).total_seconds() * 1000)

        run.sync_status = lifecycle.value
        run.finished_at_utc = now
        run.records_received = records_received
        run.records_normalized = records_normalized
        run.records_rejected = records_rejected
        run.records_ingested = records_normalized
        run.duration_ms = duration_ms
        run.failure_category = failure_category.value if failure_category else None
        run.last_error = last_error
        run.summary_de = summary_de
        run.details_json = details_json

        instance = self._get_instance_row(tenant_id)
        if lifecycle in (SyncRunLifecycle.running, SyncRunLifecycle.queued):
            instance.sync_status = ConnectorInstanceSyncState.running.value
        elif lifecycle == SyncRunLifecycle.succeeded:
            instance.sync_status = ConnectorInstanceSyncState.succeeded.value
            instance.last_error = None
            instance.last_sync_at = now
        elif lifecycle == SyncRunLifecycle.partial_success:
            instance.sync_status = ConnectorInstanceSyncState.partial_success.value
            instance.last_error = last_error
            instance.last_sync_at = now
        elif lifecycle == SyncRunLifecycle.failed:
            instance.sync_status = ConnectorInstanceSyncState.failed.value
            instance.last_error = last_error
            instance.last_sync_at = now
        elif lifecycle == SyncRunLifecycle.cancelled:
            instance.sync_status = ConnectorInstanceSyncState.idle.value
            instance.last_error = last_error
        instance.updated_at_utc = now
        instance.updated_by = actor
        self._session.commit()
        self._session.refresh(run)
        self._session.refresh(instance)
        return self._to_sync_result(run), self._to_instance(instance)

    def get_sync_run(self, tenant_id: str, sync_run_id: str) -> ConnectorSyncResult | None:
        stmt = select(EnterpriseConnectorSyncRunDB).where(
            EnterpriseConnectorSyncRunDB.tenant_id == tenant_id,
            EnterpriseConnectorSyncRunDB.sync_run_id == sync_run_id,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        return self._to_sync_result(row) if row is not None else None

    def list_sync_runs(self, tenant_id: str, *, limit: int = 30) -> list[ConnectorSyncResult]:
        stmt = (
            select(EnterpriseConnectorSyncRunDB)
            .where(EnterpriseConnectorSyncRunDB.tenant_id == tenant_id)
            .order_by(EnterpriseConnectorSyncRunDB.started_at_utc.desc())
            .limit(limit)
        )
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_sync_result(r) for r in rows]

    def get_last_sync_result(self, tenant_id: str) -> ConnectorSyncResult | None:
        stmt = (
            select(EnterpriseConnectorSyncRunDB)
            .where(EnterpriseConnectorSyncRunDB.tenant_id == tenant_id)
            .order_by(EnterpriseConnectorSyncRunDB.started_at_utc.desc())
            .limit(1)
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        return self._to_sync_result(row) if row is not None else None

    def get_last_completed_sync_result(self, tenant_id: str) -> ConnectorSyncResult | None:
        stmt = (
            select(EnterpriseConnectorSyncRunDB)
            .where(
                EnterpriseConnectorSyncRunDB.tenant_id == tenant_id,
                EnterpriseConnectorSyncRunDB.finished_at_utc.is_not(None),
            )
            .order_by(EnterpriseConnectorSyncRunDB.finished_at_utc.desc())
            .limit(1)
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        return self._to_sync_result(row) if row is not None else None

    def get_last_retryable_sync_run(self, tenant_id: str) -> ConnectorSyncResult | None:
        terminal = (
            SyncRunLifecycle.failed.value,
            SyncRunLifecycle.partial_success.value,
        )
        stmt = (
            select(EnterpriseConnectorSyncRunDB)
            .where(
                EnterpriseConnectorSyncRunDB.tenant_id == tenant_id,
                EnterpriseConnectorSyncRunDB.finished_at_utc.is_not(None),
                EnterpriseConnectorSyncRunDB.sync_status.in_(terminal),
            )
            .order_by(EnterpriseConnectorSyncRunDB.finished_at_utc.desc())
            .limit(1)
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        return self._to_sync_result(row) if row is not None else None

    def build_health_snapshot(
        self, tenant_id: str, instance: ConnectorInstanceRuntime
    ) -> ConnectorHealthSnapshot:
        last_completed = self.get_last_completed_sync_result(tenant_id)
        last_any = self.get_last_sync_result(tenant_id)
        evidence_count = self.count_evidence_records(tenant_id)
        has_issue = False
        summary: str | None = None
        if instance.connection_status != ConnectorConnectionStatus.connected:
            has_issue = True
            summary = (
                "Verbindung nicht produktiv konfiguriert oder degradiert — "
                "Zugangsdaten und Erreichbarkeit prüfen."
            )
        elif last_any and last_any.sync_status == SyncRunLifecycle.running:
            started = last_any.started_at_utc
            if started.tzinfo is None:
                started = started.replace(tzinfo=UTC)
            age_s = (datetime.now(UTC) - started).total_seconds()
            if age_s > 900:
                has_issue = True
                summary = (
                    "Ein Sync-Lauf wirkt hängend (länger als 15 Minuten in running) — "
                    "technisch prüfen oder erneut starten."
                )
        elif last_completed and last_completed.sync_status == SyncRunLifecycle.failed:
            has_issue = True
            summary = (
                last_completed.summary_de[:280]
                if last_completed.summary_de
                else "Letzter Sync fehlgeschlagen."
            )
        elif last_completed and last_completed.sync_status == SyncRunLifecycle.partial_success:
            has_issue = True
            summary = (
                "Letzter Sync nur teilweise erfolgreich — abgelehnte Datensätze prüfen "
                "und bei Bedarf erneut anstoßen."
            )
        return ConnectorHealthSnapshot(
            connection_status=instance.connection_status,
            last_terminal_sync=last_completed.sync_status if last_completed else None,
            last_finished_at_utc=last_completed.finished_at_utc if last_completed else None,
            last_failure_category=last_completed.failure_category if last_completed else None,
            evidence_record_count=evidence_count,
            has_material_connector_issue=has_issue,
            material_issue_summary_de=summary,
        )

    def _get_instance_row(self, tenant_id: str) -> EnterpriseConnectorInstanceDB:
        stmt = select(EnterpriseConnectorInstanceDB).where(
            EnterpriseConnectorInstanceDB.tenant_id == tenant_id
        )
        row = self._session.execute(stmt).scalar_one()
        return row

    @staticmethod
    def _to_instance(row: EnterpriseConnectorInstanceDB) -> ConnectorInstanceRuntime:
        domains = (
            row.enabled_evidence_domains.get("domains", []) if row.enabled_evidence_domains else []
        )
        return ConnectorInstanceRuntime(
            connector_instance_id=row.connector_instance_id,
            tenant_id=row.tenant_id,
            source_system_type=SourceSystemType(row.source_system_type),
            connection_status=ConnectorConnectionStatus(row.connection_status),
            sync_status=_normalize_instance_sync_state(row.sync_status),
            last_sync_at=row.last_sync_at,
            last_error=row.last_error,
            enabled_evidence_domains=[EvidenceDomain(d) for d in domains],
        )

    @staticmethod
    def _to_sync_result(row: EnterpriseConnectorSyncRunDB) -> ConnectorSyncResult:
        life = _normalize_run_lifecycle(row.sync_status)
        cat = ConnectorFailureCategory(row.failure_category) if row.failure_category else None
        rec_norm = int(row.records_normalized or row.records_ingested)
        rec_rec = int(row.records_received or rec_norm)
        rec_rej = int(row.records_rejected or 0)
        duration = getattr(row, "duration_ms", None)
        retry_of = getattr(row, "retry_of_sync_run_id", None)
        retry_rec = life in (SyncRunLifecycle.failed, SyncRunLifecycle.partial_success) and (
            row.finished_at_utc is not None
        )
        next_step = _operator_next_step_de(life, cat, retry_rec)
        return ConnectorSyncResult(
            sync_run_id=row.sync_run_id,
            tenant_id=row.tenant_id,
            connector_instance_id=row.connector_instance_id,
            sync_status=life,
            started_at_utc=row.started_at_utc,
            finished_at_utc=row.finished_at_utc,
            duration_ms=duration,
            records_received=rec_rec,
            records_normalized=rec_norm,
            records_rejected=rec_rej,
            records_ingested=row.records_ingested,
            failure_category=cat,
            retry_of_sync_run_id=retry_of,
            retry_recommended=retry_rec,
            operator_next_step_de=next_step,
            last_error=row.last_error,
            summary_de=row.summary_de,
        )


def _operator_next_step_de(
    life: SyncRunLifecycle,
    cat: ConnectorFailureCategory | None,
    retry_recommended: bool,
) -> str:
    if life == SyncRunLifecycle.succeeded:
        return (
            "Kein Handlungsbedarf — nächsten planmäßigen Sync abwarten "
            "oder bei Bedarf manuell wiederholen."
        )
    if life == SyncRunLifecycle.partial_success:
        return (
            "Abgelehnte Datensätze im Sync-Verlauf prüfen; Mapping/Validierung anpassen; "
            "danach sicheren Retry ausführen (idempotent)."
        )
    if life == SyncRunLifecycle.failed:
        if cat == ConnectorFailureCategory.auth_config:
            return (
                "Anmeldedaten, Secrets-Rotation und Ziel-URL im Integrations-Setup prüfen; "
                "danach Retry."
            )
        if cat == ConnectorFailureCategory.source_unavailable:
            return (
                "Quellsystem-Erreichbarkeit und Wartungsfenster prüfen; "
                "später erneut synchronisieren."
            )
        if cat == ConnectorFailureCategory.payload_validation:
            return (
                "Payload-Schema und Pflichtfelder gegen Blueprint prüfen; "
                "Daten bereinigen und erneut senden."
            )
        if cat == ConnectorFailureCategory.normalization_mapping:
            return "Feld-Mapping und Domänen-Zuordnung prüfen; bei Bedarf Advisor einbeziehen."
        if cat == ConnectorFailureCategory.internal_processing:
            return "Internen Verarbeitungsfehler logbasiert eskalieren; Support kontaktieren."
        return (
            "Fehlerursache anhand Kategorie und Log prüfen; "
            "bei transienten Fehlern Retry, sonst manuelle Klärung."
        )
    if life == SyncRunLifecycle.running:
        return "Sync läuft — Abschluss abwarten. Bei längerer Laufzeit Logs und Quellsystem prüfen."
    if life == SyncRunLifecycle.queued:
        return "Sync ist eingeplant — Verarbeitung abwarten."
    if life == SyncRunLifecycle.cancelled:
        return "Lauf wurde abgebrochen — bei Bedarf neu starten."
    if retry_recommended:
        return "Retry ist vorgesehen, sofern keine manuelle Datenkorrektur nötig ist."
    return "Status im Sync-Verlauf prüfen."

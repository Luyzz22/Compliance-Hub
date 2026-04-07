from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enterprise_connector_runtime_models import (
    ConnectorConnectionStatus,
    ConnectorInstanceRuntime,
    ConnectorSyncResult,
    ConnectorSyncStatus,
)
from app.enterprise_integration_blueprint_models import EvidenceDomain, SourceSystemType
from app.models_db import (
    EnterpriseConnectorEvidenceRecordDB,
    EnterpriseConnectorInstanceDB,
    EnterpriseConnectorSyncRunDB,
)


class EnterpriseConnectorRuntimeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

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
                sync_status=ConnectorSyncStatus.idle.value,
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
        row.sync_status = ConnectorSyncStatus.running.value
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

    def create_sync_run(self, tenant_id: str, connector_instance_id: str) -> ConnectorSyncResult:
        now = datetime.now(UTC)
        row = EnterpriseConnectorSyncRunDB(
            sync_run_id=f"sync-{tenant_id}-{int(now.timestamp())}",
            tenant_id=tenant_id,
            connector_instance_id=connector_instance_id,
            sync_status=ConnectorSyncStatus.running.value,
            started_at_utc=now,
            finished_at_utc=None,
            records_ingested=0,
            last_error=None,
            summary_de="Synchronisation läuft.",
            details_json={},
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_sync_result(row)

    def finalize_sync_run(
        self,
        *,
        tenant_id: str,
        sync_run_id: str,
        status: ConnectorSyncStatus,
        records_ingested: int,
        last_error: str | None,
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
        run.sync_status = status.value
        run.finished_at_utc = now
        run.records_ingested = records_ingested
        run.last_error = last_error
        run.summary_de = summary_de
        run.details_json = details_json

        instance = self._get_instance_row(tenant_id)
        instance.sync_status = status.value
        instance.last_sync_at = now
        instance.last_error = last_error
        instance.updated_at_utc = now
        instance.updated_by = actor
        self._session.commit()
        self._session.refresh(run)
        self._session.refresh(instance)
        return self._to_sync_result(run), self._to_instance(instance)

    def get_last_sync_result(self, tenant_id: str) -> ConnectorSyncResult | None:
        stmt = (
            select(EnterpriseConnectorSyncRunDB)
            .where(EnterpriseConnectorSyncRunDB.tenant_id == tenant_id)
            .order_by(EnterpriseConnectorSyncRunDB.started_at_utc.desc())
            .limit(1)
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        return self._to_sync_result(row) if row is not None else None

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
            sync_status=ConnectorSyncStatus(row.sync_status),
            last_sync_at=row.last_sync_at,
            last_error=row.last_error,
            enabled_evidence_domains=[EvidenceDomain(d) for d in domains],
        )

    @staticmethod
    def _to_sync_result(row: EnterpriseConnectorSyncRunDB) -> ConnectorSyncResult:
        return ConnectorSyncResult(
            sync_run_id=row.sync_run_id,
            tenant_id=row.tenant_id,
            connector_instance_id=row.connector_instance_id,
            sync_status=ConnectorSyncStatus(row.sync_status),
            started_at_utc=row.started_at_utc,
            finished_at_utc=row.finished_at_utc,
            records_ingested=row.records_ingested,
            last_error=row.last_error,
            summary_de=row.summary_de,
        )

"""Connector interface and stub implementations.

Abstract base defines the ``dispatch`` contract.  Stub connectors write
to a deterministic, testable mock sink (in-memory log) instead of calling
real external APIs.

Wave 15.1 enhancements:
- SAP connector builds a CloudEvents-style BTP envelope and stores it.
- DATEV connector produces a named JSON export artifact.
- Both return structured DispatchResult with artifact/envelope refs.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from app.integrations.datev_export import (
    build_artifact_name,
    render_json,
    store_artifact,
)
from app.integrations.models import DispatchResult, IntegrationJob
from app.integrations.sap_envelope import build_sap_envelope

logger = logging.getLogger(__name__)

_dispatch_log: list[dict[str, Any]] = []


def get_dispatch_log() -> list[dict[str, Any]]:
    return list(_dispatch_log)


def clear_dispatch_log() -> None:
    _dispatch_log.clear()


class BaseConnector(ABC):
    @abstractmethod
    def dispatch(self, job: IntegrationJob, payload: dict[str, Any]) -> DispatchResult: ...


class DatevExportConnector(BaseConnector):
    """Writes a DATEV-friendly JSON export artefact to the artifact store."""

    def dispatch(self, job: IntegrationJob, payload: dict[str, Any]) -> DispatchResult:
        artifact_name = build_artifact_name(
            tenant_id=job.tenant_id,
            client_id=job.client_id,
            version=job.payload_version,
        )
        content = render_json([payload])
        store_artifact(
            artifact_name,
            content,
            tenant_id=job.tenant_id,
            client_id=job.client_id,
            job_id=job.job_id,
        )

        entry = {
            "connector": "datev_export",
            "job_id": job.job_id,
            "tenant_id": job.tenant_id,
            "client_id": job.client_id,
            "format": "json",
            "artifact_name": artifact_name,
            "payload": payload,
        }
        _dispatch_log.append(entry)
        logger.info(
            "datev_export_dispatched",
            extra={"job_id": job.job_id, "artifact": artifact_name},
        )
        return DispatchResult(
            success=True,
            message="DATEV export artifact written",
            connector_ref=f"datev:{job.job_id}",
            artifact_name=artifact_name,
        )


class SapBtpConnector(BaseConnector):
    """Builds a CloudEvents SAP BTP envelope and writes to mock sink."""

    def dispatch(self, job: IntegrationJob, payload: dict[str, Any]) -> DispatchResult:
        envelope = build_sap_envelope(
            event_type=job.payload_type.value,
            tenant_id=job.tenant_id,
            client_id=job.client_id,
            system_id=job.system_id,
            payload_type=job.payload_type.value,
            payload_version=job.payload_version,
            data=payload,
            job_id=job.job_id,
            trace_id=job.trace_id,
        )
        envelope_id = envelope["id"]

        entry = {
            "connector": "sap_btp",
            "job_id": job.job_id,
            "tenant_id": job.tenant_id,
            "system_id": job.system_id,
            "envelope_id": envelope_id,
            "envelope": envelope,
        }
        _dispatch_log.append(entry)
        logger.info(
            "sap_btp_dispatched",
            extra={"job_id": job.job_id, "envelope_id": envelope_id},
        )
        return DispatchResult(
            success=True,
            message="SAP BTP event envelope created",
            connector_ref=f"sap_btp:{job.job_id}",
            envelope_id=envelope_id,
        )


class GenericPartnerApiConnector(BaseConnector):
    """Generic partner API stub — logs the full payload."""

    def dispatch(self, job: IntegrationJob, payload: dict[str, Any]) -> DispatchResult:
        entry = {
            "connector": "generic_partner_api",
            "job_id": job.job_id,
            "tenant_id": job.tenant_id,
            "payload": payload,
        }
        _dispatch_log.append(entry)
        logger.info(
            "generic_partner_api_dispatched",
            extra={"job_id": job.job_id},
        )
        return DispatchResult(
            success=True,
            message="Partner API payload written to mock sink",
            connector_ref=f"generic:{job.job_id}",
        )


class FailingConnector(BaseConnector):
    """Always fails — useful for testing retry / dead-letter logic."""

    def dispatch(self, job: IntegrationJob, payload: dict[str, Any]) -> DispatchResult:
        return DispatchResult(
            success=False,
            message="Simulated connector failure",
            connector_ref="",
        )


_TARGET_TO_CONNECTOR: dict[str, BaseConnector] = {
    "datev_export": DatevExportConnector(),
    "sap_btp": SapBtpConnector(),
    "generic_partner_api": GenericPartnerApiConnector(),
}


def connector_for_target(target: str) -> BaseConnector:
    conn = _TARGET_TO_CONNECTOR.get(target)
    if conn is None:
        raise ValueError(f"Unknown integration target: {target}")
    return conn


def register_connector(target: str, connector: BaseConnector) -> None:
    """Override a connector (useful for tests)."""
    _TARGET_TO_CONNECTOR[target] = connector


def reset_connectors() -> None:
    """Restore default stub connectors (for test teardown)."""
    _TARGET_TO_CONNECTOR.clear()
    _TARGET_TO_CONNECTOR["datev_export"] = DatevExportConnector()
    _TARGET_TO_CONNECTOR["sap_btp"] = SapBtpConnector()
    _TARGET_TO_CONNECTOR["generic_partner_api"] = GenericPartnerApiConnector()

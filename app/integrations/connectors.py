"""Connector interface and stub implementations.

Abstract base defines the ``dispatch`` contract.  Stub connectors write
to a deterministic, testable mock sink (in-memory log) instead of calling
real external APIs.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from app.integrations.models import DispatchResult, IntegrationJob

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
    """Writes a DATEV-friendly JSON export artefact to the mock sink."""

    def dispatch(self, job: IntegrationJob, payload: dict[str, Any]) -> DispatchResult:
        entry = {
            "connector": "datev_export",
            "job_id": job.job_id,
            "tenant_id": job.tenant_id,
            "client_id": job.client_id,
            "format": "json",
            "payload": payload,
        }
        _dispatch_log.append(entry)
        logger.info(
            "datev_export_dispatched",
            extra={"job_id": job.job_id},
        )
        return DispatchResult(
            success=True,
            message="DATEV export written to mock sink",
            connector_ref=f"datev:{job.job_id}",
        )


class SapBtpConnector(BaseConnector):
    """Writes a structured JSON envelope as if posting to SAP BTP."""

    def dispatch(self, job: IntegrationJob, payload: dict[str, Any]) -> DispatchResult:
        envelope = {
            "connector": "sap_btp",
            "job_id": job.job_id,
            "tenant_id": job.tenant_id,
            "system_id": job.system_id,
            "btp_event_type": job.payload_type.value,
            "payload": payload,
        }
        _dispatch_log.append(envelope)
        logger.info(
            "sap_btp_dispatched",
            extra={"job_id": job.job_id},
        )
        return DispatchResult(
            success=True,
            message="SAP BTP event envelope written to mock sink",
            connector_ref=f"sap_btp:{job.job_id}",
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

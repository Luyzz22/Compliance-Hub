"""Compliance Compass — fusionsbasiertes Steuerungssignal (Mandant, x-api-key + x-tenant-id)."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth_dependencies import get_api_key_and_tenant
from app.compliance_compass_models import ComplianceCompassSnapshotOut
from app.db import get_session
from app.services.compliance_compass_service import (
    ComplianceCompassError,
    build_compass_snapshot,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/governance/compass",
    tags=["governance", "compliance-compass"],
)


@router.get(
    "/snapshot",
    response_model=ComplianceCompassSnapshotOut,
    status_code=status.HTTP_200_OK,
    summary="Aktuellen Compliance-Kompass (Fusions-Index) für den Mandanten abrufen",
    description="Readiness + Workflow-Signale, ohne PII, Board-tauglich.",
)
def get_compass_snapshot(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
) -> ComplianceCompassSnapshotOut:
    try:
        return build_compass_snapshot(session, tenant_id)
    except ComplianceCompassError:
        # Service hat die Session bereits zurückgerollt und Details geloggt;
        # nach außen nur eine generische 503 ohne interne Hinweise.
        logger.warning("compliance_compass.snapshot_503 tenant=%s", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="compass_snapshot_unavailable",
        ) from None

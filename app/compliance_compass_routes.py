"""Compliance Compass — fusionsbasiertes Steuerungssignal (Mandant, x-api-key + x-tenant-id)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth_dependencies import get_api_key_and_tenant
from app.compliance_compass_models import ComplianceCompassSnapshotOut
from app.db import get_session
from app.services.compliance_compass_service import build_compass_snapshot

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
    return build_compass_snapshot(session, tenant_id)

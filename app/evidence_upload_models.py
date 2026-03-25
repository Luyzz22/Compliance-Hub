from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class EvidenceUploadMetadata(BaseModel):
    """Metadaten für spätere Ablage in Objekt-Storage (S3/Blob); noch ohne Binärdaten."""

    id: str
    tenant_id: str
    ai_system_id: str | None = None
    related_action_id: str | None = None
    filename: str
    content_type: str
    size: int = Field(..., ge=0)
    created_at: datetime


class EvidenceUploadRegisterRequest(BaseModel):
    """Registrierung eines Uploads ohne Datei-Body (Platzhalter bis Storage angebunden ist)."""

    filename: str
    content_type: str
    size: int = Field(..., ge=0)
    ai_system_id: str | None = None
    related_action_id: str | None = None

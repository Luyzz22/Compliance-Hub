"""DATEV export artifact builder.

Produces stable CSV/JSON export files suitable for Kanzlei workflows.
Artifacts are written to an in-memory export store (future: file/S3)
and linked back to IntegrationJob + Evidence events.

Naming convention:
  ai_compliance_mandant_export_{tenant}_{client}_{period}_{version}.{ext}

German field labels for Mandant-facing columns, English technical IDs.
"""

from __future__ import annotations

import csv
import io
import json
import logging
from datetime import UTC, datetime
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

_lock = Lock()
_artifacts: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Artifact naming
# ---------------------------------------------------------------------------


def build_artifact_name(
    *,
    tenant_id: str,
    client_id: str,
    period: str = "",
    version: str = "v1",
    ext: str = "json",
) -> str:
    """Deterministic artifact name following DATEV export convention."""

    def safe(s: str) -> str:
        return s.replace("/", "-").replace(" ", "_") or "unknown"

    ts = period or datetime.now(UTC).strftime("%Y%m%d")
    return (
        f"ai_compliance_mandant_export"
        f"_{safe(tenant_id)}"
        f"_{safe(client_id)}"
        f"_{safe(ts)}"
        f"_{safe(version)}"
        f".{ext}"
    )


# ---------------------------------------------------------------------------
# CSV rendering
# ---------------------------------------------------------------------------

_CSV_HEADERS = [
    "Datensatz_Typ",
    "Datensatz_ID",
    "Mandant_ID",
    "System_ID",
    "Status",
    "Risikokategorie",
    "NIS2_Entitaetstyp",
    "ISO42001_Schweregrad",
    "Bereitschaftsgrad",
    "Lebenszyklus_Stufe",
    "Erstellt_Am",
    "Schema_Version",
]


def _row_from_payload(payload: dict[str, Any]) -> dict[str, str]:
    """Flatten a mapped payload into a CSV row dict."""
    record_type = payload.get("record_type", "")
    return {
        "Datensatz_Typ": record_type,
        "Datensatz_ID": payload.get("source_id", ""),
        "Mandant_ID": payload.get("client_id", ""),
        "System_ID": payload.get("system_id", ""),
        "Status": payload.get("status", ""),
        "Risikokategorie": payload.get("risikokategorie", payload.get("risk_category", "")),
        "NIS2_Entitaetstyp": payload.get("nis2_entitaetstyp", payload.get("nis2_entity_type", "")),
        "ISO42001_Schweregrad": payload.get("schweregrad", payload.get("gap_severity", "")),
        "Bereitschaftsgrad": payload.get("bereitschaftsgrad", payload.get("readiness_level", "")),
        "Lebenszyklus_Stufe": payload.get("lebenszyklus_stufe", payload.get("lifecycle_stage", "")),
        "Erstellt_Am": payload.get("created_at", ""),
        "Schema_Version": payload.get("schema_version", "v1"),
    }


def render_csv(payloads: list[dict[str, Any]]) -> str:
    """Render a list of mapped payloads to a CSV string."""
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=_CSV_HEADERS,
        extrasaction="ignore",
    )
    writer.writeheader()
    for p in payloads:
        writer.writerow(_row_from_payload(p))
    return buf.getvalue()


def render_json(payloads: list[dict[str, Any]]) -> str:
    """Render a list of mapped payloads to a JSON string."""
    return json.dumps(
        {
            "schema_version": "v1",
            "export_type": "datev_mandant_export",
            "exported_at": datetime.now(UTC).isoformat(),
            "records": payloads,
        },
        ensure_ascii=False,
        indent=2,
    )


# ---------------------------------------------------------------------------
# Artifact store (in-memory, swappable for S3/DB later)
# ---------------------------------------------------------------------------


def store_artifact(
    name: str,
    content: str,
    *,
    tenant_id: str,
    client_id: str = "",
    job_id: str = "",
    fmt: str = "json",
    period: str = "",
    export_version: int = 0,
    schema_version: str = "v1",
) -> dict[str, Any]:
    """Persist an export artifact and return its metadata."""
    meta: dict[str, Any] = {
        "name": name,
        "tenant_id": tenant_id,
        "client_id": client_id,
        "job_id": job_id,
        "format": fmt,
        "size_bytes": len(content.encode("utf-8")),
        "stored_at": datetime.now(UTC).isoformat(),
        "period": period,
        "export_version": export_version,
        "schema_version": schema_version,
    }
    with _lock:
        _artifacts[name] = {"meta": meta, "content": content}
    return meta


def get_artifact(
    name: str,
    *,
    tenant_id: str | None = None,
) -> dict[str, Any] | None:
    """Retrieve an artifact.  Returns None if not found or tenant mismatch."""
    with _lock:
        entry = _artifacts.get(name)
    if entry is None:
        return None
    if tenant_id and entry["meta"]["tenant_id"] != tenant_id:
        return None
    return entry


def list_artifact_names(
    *,
    tenant_id: str | None = None,
    client_id: str | None = None,
) -> list[str]:
    with _lock:
        names = list(_artifacts.keys())
    if tenant_id:
        names = [n for n in names if _artifacts[n]["meta"]["tenant_id"] == tenant_id]
    if client_id:
        names = [n for n in names if _artifacts[n]["meta"]["client_id"] == client_id]
    return names


def clear_artifacts_for_tests() -> None:
    with _lock:
        _artifacts.clear()

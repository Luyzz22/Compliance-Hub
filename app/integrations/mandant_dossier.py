"""Mandanten-Compliance-Dossier builder for Kanzlei-Exports.

Produces a structured compliance dossier per Mandant (client_id) that a
Steuerkanzlei can use as AI-Compliance-Beilage (GoBD-Umfeld):

- Stammdaten (tenant, client, Branche)
- AI-System-Inventar (lifecycle, classification, readiness)
- GRC-Sicht (AiRiskAssessments, NIS2-Pflichten, ISO 42001-Gaps)
- Compliance-Flags (deployment_check_used, board_reports_recent)
- Period/Version tracking for GoBD-Nachvollziehbarkeit

No external calls.  Output is a stable JSON structure versioned via
``schema_version``.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from app.grc.models import (
    AiSystem,
)
from app.grc.store import (
    list_ai_systems,
    list_iso42001_gaps,
    list_nis2_obligations,
    list_risks,
)
from app.services.rag.evidence_store import record_event

logger = logging.getLogger(__name__)

DOSSIER_SCHEMA_VERSION = "v1"


def build_dossier(
    *,
    tenant_id: str,
    client_id: str,
    period: str = "",
    export_version: int = 1,
    mandant_kurzname: str = "",
    branche: str = "",
) -> dict[str, Any]:
    """Build a Mandanten-Compliance-Dossier for a given client."""
    systems = list_ai_systems(tenant_id=tenant_id, client_id=client_id)
    risks = list_risks(tenant_id=tenant_id, client_id=client_id)
    nis2 = list_nis2_obligations(tenant_id=tenant_id, client_id=client_id)
    gaps = list_iso42001_gaps(tenant_id=tenant_id, client_id=client_id)

    risk_status_counts = Counter(r.status.value for r in risks)
    nis2_status_counts = Counter(n.status.value for n in nis2)

    gap_by_family: dict[str, dict[str, int]] = {}
    for g in gaps:
        for fam in g.control_families or ["unknown"]:
            entry = gap_by_family.setdefault(fam, {})
            entry[g.status.value] = entry.get(g.status.value, 0) + 1

    has_board_reports = _check_recent_board_reports(tenant_id, client_id)
    has_deployment_checks = _check_deployment_checks(tenant_id, client_id)

    return {
        "schema_version": DOSSIER_SCHEMA_VERSION,
        "export_type": "mandant_compliance_dossier",
        "period": period,
        "export_version": export_version,
        "exported_at": datetime.now(UTC).isoformat(),
        "stammdaten": {
            "tenant_id": tenant_id,
            "client_id": client_id,
            "mandant_kurzname": mandant_kurzname or client_id,
            "branche": branche,
        },
        "ai_system_inventar": [_system_summary(s) for s in systems],
        "ai_systeme_gesamt": len(systems),
        "grc_sicht": {
            "ai_risk_assessments": {
                "gesamt": len(risks),
                "status_verteilung": dict(risk_status_counts),
            },
            "nis2_pflichten": {
                "gesamt": len(nis2),
                "status_verteilung": dict(nis2_status_counts),
            },
            "iso42001_gaps": {
                "gesamt": len(gaps),
                "nach_control_family": gap_by_family,
            },
        },
        "compliance_flags": {
            "deployment_check_verwendet": has_deployment_checks,
            "board_reports_aktuell": has_board_reports,
        },
    }


def _system_summary(s: AiSystem) -> dict[str, Any]:
    return {
        "system_id": s.system_id,
        "name": s.name,
        "beschreibung": s.description,
        "business_owner": s.business_owner,
        "technical_owner": s.technical_owner,
        "lebenszyklus_stufe": s.lifecycle_stage.value,
        "ki_act_klassifikation": s.ai_act_classification.value,
        "bereitschaftsgrad": s.readiness_level.value,
        "nis2_relevant": s.nis2_relevant,
        "iso42001_im_scope": s.iso42001_in_scope,
    }


def _check_recent_board_reports(tenant_id: str, client_id: str) -> bool:
    """Check if recent board reports exist for this Mandant."""
    try:
        from app.grc.client_board_report_service import list_reports

        reports = list_reports(tenant_id=tenant_id, client_id=client_id)
        return len(reports) > 0
    except Exception:
        return False


def _check_deployment_checks(tenant_id: str, client_id: str) -> bool:
    """Check if deployment checks have been run for any system."""
    try:
        from app.services.rag.evidence_store import list_all_events

        events = list_all_events(limit=200)
        return any(
            e.get("event_type") == "deployment_check" and e.get("tenant_id") == tenant_id
            for e in events
        )
    except Exception:
        return False


def render_dossier_json(dossier: dict[str, Any]) -> str:
    """Render dossier to a JSON string."""
    return json.dumps(dossier, ensure_ascii=False, indent=2)


def log_dossier_evidence(
    *,
    tenant_id: str,
    client_id: str,
    period: str,
    export_version: int,
    schema_version: str,
    artifact_name: str = "",
    job_id: str = "",
    trace_id: str = "",
) -> None:
    """Emit an evidence event for a Mandanten-Dossier export."""
    record_event(
        {
            "event_type": "mandant_compliance_export",
            "tenant_id": tenant_id,
            "client_id": client_id,
            "period": period,
            "export_version": export_version,
            "schema_version": schema_version,
            "artifact_name": artifact_name,
            "job_id": job_id,
            "trace_id": trace_id,
        }
    )

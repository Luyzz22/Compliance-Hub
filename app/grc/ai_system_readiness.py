"""Release-gate readiness evaluation for AiSystems.

Computes per-framework readiness hints and an overall readiness_level
by inspecting linked GRC records (risks, NIS2 obligations, ISO 42001 gaps)
and cross-framework mappings.

Rules are deliberately simple, transparent, and documented so they can
be reviewed by compliance officers.  This is an *advisory* check — it
never blocks deployments automatically.

Readiness levels:
  unknown              — no evidence at all for this system
  insufficient_evidence — some records exist but key areas are missing
  partially_covered    — core areas have evidence, some gaps remain open
  ready_for_review     — all key areas covered, suitable for human go/no-go
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from app.grc.framework_mapping import build_system_overview_hints
from app.grc.models import (
    AiSystem,
    AiSystemClassification,
    GapStatus,
    ObligationStatus,
    ReadinessLevel,
)
from app.grc.store import (
    get_ai_system,
    list_iso42001_gaps,
    list_nis2_obligations,
    list_risks,
    upsert_ai_system,
)
from app.services.rag.evidence_store import record_event

logger = logging.getLogger(__name__)

CORE_GAP_FAMILIES = {"governance", "data", "monitoring"}


# ---------------------------------------------------------------------------
# Per-framework hint builders
# ---------------------------------------------------------------------------


def _ai_act_hints(
    ai_sys: AiSystem,
    risks: list[Any],
) -> dict[str, Any]:
    """EU AI Act readiness hints."""
    has_risk_assessment = len(risks) > 0
    classification = ai_sys.ai_act_classification.value
    is_high_risk_candidate = classification in (
        AiSystemClassification.high_risk_candidate,
        AiSystemClassification.high_risk,
    )

    findings: list[str] = []
    if not has_risk_assessment:
        findings.append("Keine Risikobewertung vorhanden")
    if is_high_risk_candidate:
        findings.append(
            f"System als {classification} markiert — Konformitätsbewertung erforderlich"
        )
    elif has_risk_assessment:
        findings.append("Risikobewertung vorhanden")

    return {
        "framework": "eu_ai_act",
        "has_risk_assessment": has_risk_assessment,
        "classification": classification,
        "is_high_risk_candidate": is_high_risk_candidate,
        "findings": findings,
    }


def _nis2_hints(
    ai_sys: AiSystem,
    nis2_records: list[Any],
) -> dict[str, Any]:
    """NIS2 readiness hints."""
    if not ai_sys.nis2_relevant:
        return {
            "framework": "nis2",
            "relevant": False,
            "findings": ["System nicht als NIS2-relevant markiert"],
        }

    total = len(nis2_records)
    open_count = sum(1 for r in nis2_records if r.status != ObligationStatus.fulfilled)

    findings: list[str] = []
    if total == 0:
        findings.append("Keine NIS2-Pflichten erfasst")
    else:
        findings.append(f"{total} Pflicht(en) identifiziert, {open_count} offen")

    return {
        "framework": "nis2",
        "relevant": True,
        "total_obligations": total,
        "open_obligations": open_count,
        "findings": findings,
    }


def _iso42001_hints(
    ai_sys: AiSystem,
    gap_records: list[Any],
) -> dict[str, Any]:
    """ISO 42001 readiness hints."""
    if not ai_sys.iso42001_in_scope:
        return {
            "framework": "iso42001",
            "in_scope": False,
            "findings": ["System nicht im ISO 42001-Scope"],
        }

    total = len(gap_records)
    open_gaps = [g for g in gap_records if g.status == GapStatus.open]
    open_count = len(open_gaps)

    open_families: set[str] = set()
    for g in open_gaps:
        open_families.update(g.control_families)
    core_open = open_families & CORE_GAP_FAMILIES

    findings: list[str] = []
    if total == 0:
        findings.append("Keine Gap-Analyse durchgeführt")
    else:
        findings.append(f"{total} Gap(s) erfasst, {open_count} offen")
    if core_open:
        findings.append(f"Offene Kern-Gaps: {', '.join(sorted(core_open))}")

    return {
        "framework": "iso42001",
        "in_scope": True,
        "total_gaps": total,
        "open_gaps": open_count,
        "open_core_families": sorted(core_open),
        "findings": findings,
    }


# ---------------------------------------------------------------------------
# Overall readiness computation
# ---------------------------------------------------------------------------

# Rules (kept simple and adjustable):
#
# ready_for_review:
#   - At least one risk assessment exists
#   - If high_risk_candidate: no open core ISO 42001 gaps
#     (governance, data, monitoring)
#   - If NIS2-relevant: all obligations at least in_progress
#
# partially_covered:
#   - Risk assessment exists but some gaps/obligations are still open
#
# insufficient_evidence:
#   - Risk assessment exists but too many key areas are missing
#
# unknown:
#   - No GRC records at all for this system


def compute_readiness(
    ai_sys: AiSystem,
    *,
    risks: list[Any] | None = None,
    nis2_records: list[Any] | None = None,
    gap_records: list[Any] | None = None,
) -> dict[str, Any]:
    """Compute release-gate readiness for an AiSystem.

    Returns a dict with readiness_level, per-framework hints,
    blocking_items, and framework_coverage.
    """
    tid = ai_sys.tenant_id
    sid = ai_sys.system_id

    if risks is None:
        risks = list_risks(tenant_id=tid, system_id=sid)
    if nis2_records is None:
        all_nis2 = list_nis2_obligations(tenant_id=tid)
        nis2_records = [r for r in all_nis2 if r.system_id == sid]
    if gap_records is None:
        all_gaps = list_iso42001_gaps(tenant_id=tid)
        gap_records = [g for g in all_gaps if g.system_id == sid]

    ai_act = _ai_act_hints(ai_sys, risks)
    nis2 = _nis2_hints(ai_sys, nis2_records)
    iso42001 = _iso42001_hints(ai_sys, gap_records)

    framework_coverage = build_system_overview_hints(
        risks=risks,
        nis2_records=nis2_records,
        gap_records=gap_records,
    )

    blocking: list[str] = []
    level = _derive_level(ai_sys, risks, nis2_records, gap_records, blocking)

    return {
        "system_id": sid,
        "lifecycle_stage": ai_sys.lifecycle_stage.value,
        "readiness_level": level.value,
        "framework_hints": {
            "eu_ai_act": ai_act,
            "nis2": nis2,
            "iso42001": iso42001,
        },
        "blocking_items": blocking,
        "framework_coverage": framework_coverage,
    }


def _derive_level(
    ai_sys: AiSystem,
    risks: list[Any],
    nis2_records: list[Any],
    gap_records: list[Any],
    blocking: list[str],
) -> ReadinessLevel:
    has_risks = len(risks) > 0
    if not has_risks:
        blocking.append("Keine Risikobewertung vorhanden")
        if not nis2_records and not gap_records:
            return ReadinessLevel.unknown
        return ReadinessLevel.insufficient_evidence

    is_hrc = ai_sys.ai_act_classification in (
        AiSystemClassification.high_risk_candidate,
        AiSystemClassification.high_risk,
    )

    open_core_gaps: set[str] = set()
    for g in gap_records:
        if g.status == GapStatus.open:
            open_core_gaps.update(set(g.control_families) & CORE_GAP_FAMILIES)

    if open_core_gaps:
        blocking.append(f"Offene ISO 42001 Kern-Gaps: {', '.join(sorted(open_core_gaps))}")

    nis2_all_progressing = all(r.status != ObligationStatus.identified for r in nis2_records)
    if ai_sys.nis2_relevant and not nis2_all_progressing:
        blocking.append("NIS2-Pflichten noch nicht in Bearbeitung")

    if blocking:
        if is_hrc and open_core_gaps:
            return ReadinessLevel.insufficient_evidence
        return ReadinessLevel.partially_covered

    return ReadinessLevel.ready_for_review


# ---------------------------------------------------------------------------
# Evaluate + persist + log evidence
# ---------------------------------------------------------------------------


def evaluate_and_update(
    *,
    tenant_id: str,
    system_id: str,
    trace_id: str = "",
) -> dict[str, Any]:
    """Run readiness evaluation, update the AiSystem record, and log an
    evidence event.  Returns the full readiness result."""
    ai_sys = get_ai_system(tenant_id=tenant_id, system_id=system_id)
    if ai_sys is None:
        return {"error": f"AiSystem not found: {tenant_id}:{system_id}"}

    result = compute_readiness(ai_sys)
    new_level = ReadinessLevel(result["readiness_level"])

    ai_sys.readiness_level = new_level
    ai_sys.last_reviewed_at = datetime.now(UTC).isoformat()
    upsert_ai_system(ai_sys)

    _log_readiness_evidence(ai_sys, result, trace_id)
    return result


def _log_readiness_evidence(
    ai_sys: AiSystem,
    result: dict[str, Any],
    trace_id: str,
) -> None:
    payload: dict[str, Any] = {
        "event_type": "readiness_evaluation",
        "tenant_id": ai_sys.tenant_id,
        "system_id": ai_sys.system_id,
        "ai_system_id": ai_sys.id,
        "lifecycle_stage": ai_sys.lifecycle_stage.value,
        "readiness_level": result["readiness_level"],
        "blocking_items_count": len(result["blocking_items"]),
        "trace_id": trace_id or f"readiness-{uuid.uuid4().hex[:8]}",
    }
    record_event(payload)
    logger.info("readiness_evaluation_logged", extra=payload)

"""Client/Mandant-level AI Compliance Board Report service (Wave 13).

Aggregates AiSystem inventory + GRC records for one client, synthesises
a German advisory board report, persists it in-memory, and logs
evidence/metrics events.

All operations are read-only w.r.t. AiSystems and GRC records.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from pydantic import BaseModel, Field

from app.grc.ai_system_readiness import compute_readiness
from app.grc.framework_mapping import build_system_overview_hints
from app.grc.models import (
    GapStatus,
    ObligationStatus,
)
from app.grc.store import (
    list_ai_systems,
    list_iso42001_gaps,
    list_nis2_obligations,
    list_risks,
)
from app.services.rag.evidence_store import record_event

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Report model
# ---------------------------------------------------------------------------


class ClientBoardReport(BaseModel):
    id: str = Field(default_factory=lambda: f"CBR-{uuid.uuid4().hex[:12]}")
    tenant_id: str = ""
    client_id: str = ""
    reporting_period: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    systems_included: int = 0
    system_ids: list[str] = Field(default_factory=list)
    snapshot: dict[str, Any] = Field(default_factory=dict)
    report_markdown: str = ""
    highlights: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# In-memory report store
# ---------------------------------------------------------------------------

_lock = Lock()
_reports: dict[str, ClientBoardReport] = {}


def _store_report(report: ClientBoardReport) -> ClientBoardReport:
    with _lock:
        _reports[report.id] = report
    return report


def get_report(report_id: str) -> ClientBoardReport | None:
    with _lock:
        return _reports.get(report_id)


def list_reports(*, tenant_id: str, client_id: str) -> list[ClientBoardReport]:
    with _lock:
        return [
            r for r in _reports.values() if r.tenant_id == tenant_id and r.client_id == client_id
        ]


def clear_reports_for_tests() -> None:
    with _lock:
        _reports.clear()


# ---------------------------------------------------------------------------
# In-memory workflow tracker
# ---------------------------------------------------------------------------

_wf_lock = Lock()
_workflows: dict[str, dict[str, Any]] = {}


def _track_workflow(workflow_id: str, tenant_id: str, client_id: str, period: str) -> None:
    with _wf_lock:
        _workflows[workflow_id] = {
            "status": "RUNNING",
            "tenant_id": tenant_id,
            "client_id": client_id,
            "reporting_period": period,
            "report_id": None,
            "systems_included": 0,
            "started_at": datetime.now(UTC).isoformat(),
        }


def _complete_workflow(workflow_id: str, report_id: str, systems_included: int) -> None:
    with _wf_lock:
        if workflow_id in _workflows:
            _workflows[workflow_id]["status"] = "COMPLETED"
            _workflows[workflow_id]["report_id"] = report_id
            _workflows[workflow_id]["systems_included"] = systems_included


def get_workflow_status(workflow_id: str) -> dict[str, Any] | None:
    with _wf_lock:
        return _workflows.get(workflow_id)


def clear_workflows_for_tests() -> None:
    with _wf_lock:
        _workflows.clear()


# ---------------------------------------------------------------------------
# Task 2: Data aggregation
# ---------------------------------------------------------------------------


def aggregate_client_data(
    *,
    tenant_id: str,
    client_id: str,
    system_filter: list[str] | None = None,
) -> dict[str, Any]:
    """Aggregate AiSystem inventory + GRC records for one Mandant.

    Returns a structured snapshot dict — purely read-only, no status
    changes.
    """
    systems = list_ai_systems(tenant_id=tenant_id, client_id=client_id)
    if not systems:
        systems = [
            s
            for s in list_ai_systems(tenant_id=tenant_id)
            if s.client_id == client_id or s.client_id == ""
        ]

    if system_filter:
        systems = [s for s in systems if s.system_id in system_filter]

    system_summaries: list[dict[str, Any]] = []
    for ai_sys in systems:
        risks = list_risks(tenant_id=tenant_id, system_id=ai_sys.system_id)
        all_nis2 = list_nis2_obligations(tenant_id=tenant_id)
        nis2 = [r for r in all_nis2 if r.system_id == ai_sys.system_id]
        all_gaps = list_iso42001_gaps(tenant_id=tenant_id)
        gaps = [g for g in all_gaps if g.system_id == ai_sys.system_id]

        open_gaps = [g for g in gaps if g.status == GapStatus.open]
        open_nis2 = [r for r in nis2 if r.status != ObligationStatus.fulfilled]

        readiness = compute_readiness(ai_sys, risks=risks, nis2_records=nis2, gap_records=gaps)

        coverage = build_system_overview_hints(risks=risks, nis2_records=nis2, gap_records=gaps)

        system_summaries.append(
            {
                "system_id": ai_sys.system_id,
                "name": ai_sys.name or ai_sys.system_id,
                "classification": ai_sys.ai_act_classification.value,
                "lifecycle_stage": ai_sys.lifecycle_stage.value,
                "readiness_level": readiness["readiness_level"],
                "nis2_relevant": ai_sys.nis2_relevant,
                "iso42001_in_scope": ai_sys.iso42001_in_scope,
                "risk_assessments_count": len(risks),
                "open_gaps_count": len(open_gaps),
                "open_obligations_count": len(open_nis2),
                "framework_coverage": coverage,
                "blocking_items": readiness.get("blocking_items", []),
            }
        )

    high_risk_count = sum(
        1 for s in system_summaries if s["classification"] in ("high_risk_candidate", "high_risk")
    )

    return {
        "tenant_id": tenant_id,
        "client_id": client_id,
        "systems": system_summaries,
        "systems_count": len(system_summaries),
        "high_risk_systems": high_risk_count,
        "total_open_gaps": sum(s["open_gaps_count"] for s in system_summaries),
        "total_open_obligations": sum(s["open_obligations_count"] for s in system_summaries),
    }


# ---------------------------------------------------------------------------
# Task 3: Report synthesis (LLM or deterministic fallback)
# ---------------------------------------------------------------------------

_DISCLAIMER = (
    "\n\n---\n*Hinweis: Dieser Report dient ausschließlich der "
    "unverbindlichen Einordnung und stellt keine Rechtsberatung dar. "
    "Für verbindliche Bewertungen wenden Sie sich bitte an Ihre "
    "Rechtsabteilung oder einen spezialisierten Anwalt.*\n"
)


def synthesise_report(
    *,
    tenant_id: str,
    client_id: str,
    reporting_period: str,
    snapshot: dict[str, Any],
    llm_fn: Any | None = None,
) -> ClientBoardReport:
    """Build a Mandant board report from the aggregated snapshot.

    Uses the guardrailed LLM if ``llm_fn`` is provided, otherwise falls
    back to deterministic Markdown rendering.
    """
    systems = snapshot.get("systems", [])
    system_ids = [s["system_id"] for s in systems]

    if llm_fn is not None:
        md = _synthesise_with_llm(tenant_id, client_id, reporting_period, snapshot, llm_fn)
    else:
        md = _render_deterministic(client_id, reporting_period, snapshot)

    highlights = _extract_highlights(snapshot)

    report = ClientBoardReport(
        tenant_id=tenant_id,
        client_id=client_id,
        reporting_period=reporting_period,
        systems_included=len(systems),
        system_ids=system_ids,
        snapshot=snapshot,
        report_markdown=md,
        highlights=highlights,
    )
    _store_report(report)
    return report


def _synthesise_with_llm(
    tenant_id: str,
    client_id: str,
    period: str,
    snapshot: dict[str, Any],
    llm_fn: Any,
) -> str:
    from app.services.rag.llm import LlmCallContext

    prompt = _build_prompt(client_id, period, snapshot)
    ctx = LlmCallContext(
        tenant_id=tenant_id,
        role="kanzlei_advisor",
        action="generate_client_board_report",
        metadata={"client_id": client_id, "period": period},
    )
    resp = llm_fn(prompt, ctx)
    return resp.text + _DISCLAIMER


def _build_prompt(
    client_id: str,
    period: str,
    snapshot: dict[str, Any],
) -> str:
    n_sys = snapshot.get("systems_count", 0)
    hr = snapshot.get("high_risk_systems", 0)
    gaps = snapshot.get("total_open_gaps", 0)
    obls = snapshot.get("total_open_obligations", 0)

    system_lines: list[str] = []
    for s in snapshot.get("systems", []):
        system_lines.append(
            f"- {s['name']}: Klassifizierung={s['classification']}, "
            f"Lifecycle={s['lifecycle_stage']}, "
            f"Readiness={s['readiness_level']}, "
            f"Risikobewertungen={s['risk_assessments_count']}, "
            f"Offene Gaps={s['open_gaps_count']}, "
            f"Offene NIS2-Pflichten={s['open_obligations_count']}"
        )

    return (
        f"Erstelle einen AI Compliance Board-Report für Mandant "
        f"'{client_id}' (Berichtszeitraum: {period or 'aktuell'}).\n\n"
        f"Zusammenfassung:\n"
        f"- {n_sys} AI-System(e) erfasst\n"
        f"- {hr} als high_risk_candidate/high_risk eingestuft\n"
        f"- {gaps} offene ISO 42001 Gaps\n"
        f"- {obls} offene NIS2-Verpflichtungen\n\n"
        f"AI-Systeme:\n" + "\n".join(system_lines) + "\n\n"
        "Gliedere den Report in:\n"
        "1. AI Systemübersicht\n"
        "2. EU AI Act Risikoeinschätzungen & offene Punkte\n"
        "3. NIS2-relevante Verpflichtungen\n"
        "4. ISO 42001/27001 Governance & Gap-Status\n"
        "5. Empfehlungen\n\n"
        "Schreibe auf Deutsch, sachlich, keine Rechtsberatung."
    )


def _render_deterministic(
    client_id: str,
    period: str,
    snapshot: dict[str, Any],
) -> str:
    """Deterministic Markdown fallback (no LLM needed)."""
    n_sys = snapshot.get("systems_count", 0)
    hr = snapshot.get("high_risk_systems", 0)
    gaps = snapshot.get("total_open_gaps", 0)
    obls = snapshot.get("total_open_obligations", 0)
    period_label = period or "aktuell"

    lines = [
        f"# AI Compliance Board-Report — Mandant {client_id}",
        f"**Berichtszeitraum:** {period_label}",
        "",
        "## AI Systemübersicht",
        f"- **{n_sys}** AI-System(e) erfasst",
        f"- **{hr}** als high_risk_candidate / high_risk eingestuft",
        "",
    ]

    for s in snapshot.get("systems", []):
        lines.append(f"### {s['name']} ({s['system_id']})")
        lines.append(f"- Klassifizierung: {s['classification']}")
        lines.append(f"- Lifecycle: {s['lifecycle_stage']}")
        lines.append(f"- Readiness: {s['readiness_level']}")
        if s.get("risk_assessments_count"):
            lines.append(f"- Risikobewertungen: {s['risk_assessments_count']}")
        if s.get("open_gaps_count"):
            lines.append(f"- Offene ISO 42001 Gaps: {s['open_gaps_count']}")
        if s.get("open_obligations_count"):
            lines.append(f"- Offene NIS2-Pflichten: {s['open_obligations_count']}")
        lines.append("")

    lines.append("## EU AI Act Risikoeinschätzungen")
    if hr > 0:
        lines.append(
            f"- {hr} System(e) als high_risk_candidate markiert — Konformitätsbewertung prüfen"
        )
    else:
        lines.append("- Keine Hochrisiko-Systeme identifiziert")
    lines.append("")

    lines.append("## NIS2-relevante Verpflichtungen")
    if obls > 0:
        lines.append(f"- {obls} offene Verpflichtung(en)")
    else:
        lines.append("- Keine offenen NIS2-Verpflichtungen")
    lines.append("")

    lines.append("## ISO 42001/27001 Governance & Gap-Status")
    if gaps > 0:
        lines.append(f"- {gaps} offene Gap(s)")
    else:
        lines.append("- Keine offenen Gaps")
    lines.append("")

    lines.append(_DISCLAIMER)
    return "\n".join(lines)


def _extract_highlights(snapshot: dict[str, Any]) -> list[str]:
    highlights: list[str] = []
    hr = snapshot.get("high_risk_systems", 0)
    gaps = snapshot.get("total_open_gaps", 0)
    obls = snapshot.get("total_open_obligations", 0)
    n_sys = snapshot.get("systems_count", 0)

    highlights.append(f"{n_sys} AI-System(e) erfasst")
    if hr > 0:
        highlights.append(f"{hr} high_risk_candidate System(e)")
    if gaps > 0:
        highlights.append(f"{gaps} offene ISO 42001 Gap(s)")
    if obls > 0:
        highlights.append(f"{obls} offene NIS2-Verpflichtung(en)")
    return highlights


# ---------------------------------------------------------------------------
# Task 5: Evidence & metrics
# ---------------------------------------------------------------------------


def log_report_evidence(report: ClientBoardReport) -> None:
    """Emit evidence event for a completed client board report."""
    payload: dict[str, Any] = {
        "event_type": "client_board_report_generated",
        "tenant_id": report.tenant_id,
        "client_id": report.client_id,
        "report_id": report.id,
        "reporting_period": report.reporting_period,
        "systems_included": report.systems_included,
        "system_ids": report.system_ids,
    }
    record_event(payload)
    logger.info("client_board_report_evidence", extra=payload)


# ---------------------------------------------------------------------------
# Orchestrator: run workflow synchronously (in-memory, no Temporal needed)
# ---------------------------------------------------------------------------


def run_client_board_report(
    *,
    tenant_id: str,
    client_id: str,
    reporting_period: str = "",
    system_filter: list[str] | None = None,
    llm_fn: Any | None = None,
    workflow_id: str | None = None,
) -> dict[str, Any]:
    """Run a full client board report workflow synchronously.

    This is the primary entry point used by the API layer and tests.
    In production with Temporal, the Temporal workflow would call
    aggregate_client_data and synthesise_report as activities.
    """
    wf_id = workflow_id or f"cbr-{uuid.uuid4().hex[:12]}"
    _track_workflow(wf_id, tenant_id, client_id, reporting_period)

    snapshot = aggregate_client_data(
        tenant_id=tenant_id,
        client_id=client_id,
        system_filter=system_filter,
    )

    report = synthesise_report(
        tenant_id=tenant_id,
        client_id=client_id,
        reporting_period=reporting_period,
        snapshot=snapshot,
        llm_fn=llm_fn,
    )

    _complete_workflow(wf_id, report.id, report.systems_included)
    log_report_evidence(report)

    return {
        "workflow_id": wf_id,
        "report_id": report.id,
        "tenant_id": tenant_id,
        "client_id": client_id,
        "reporting_period": reporting_period,
        "systems_included": report.systems_included,
        "status": "COMPLETED",
    }

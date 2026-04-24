"""Deterministic remediation candidates — kein LLM; merge-fähige Dedupe-Schlüssel."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import Select, func, not_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models_db import (
    AISystemTable,
    BoardReportActionTable,
    GovernanceAuditCaseControlTable,
    GovernanceAuditCaseTable,
    GovernanceControlEvidenceTable,
    GovernanceControlReviewTable,
    GovernanceControlTable,
    NIS2IncidentTable,
    RemediationActionLinkTable,
    RemediationActionTable,
    ServiceHealthIncidentTable,
)

# Framework tags (same literals as governance_control_models.FrameworkTag).
TAG_EU_AI_ACT = "EU_AI_ACT"
TAG_NIS2 = "NIS2"

RULE_EVIDENCE_GAP = "evidence_gap"
RULE_WEAK_CONTROL = "weak_control"
RULE_OVERDUE_REVIEW = "overdue_review"
RULE_SERVICE_INCIDENT_CRITICAL = "service_incident_critical"
RULE_BOARD_ACTION_OPEN = "board_action_open"
RULE_AI_ACT_HIGH_BASELINE = "ai_act_high_risk_baseline"
RULE_NIS2_BASELINE_PRIORITY = "nis2_baseline_priority"

ENTITY_GOVERNANCE_CONTROL = "governance_control"
ENTITY_GOVERNANCE_AUDIT_CASE = "governance_audit_case"
ENTITY_BOARD_REPORT_ACTION = "board_report_action"
ENTITY_BOARD_REPORT = "board_report"
ENTITY_SERVICE_HEALTH_INCIDENT = "service_health_incident"
ENTITY_GOVERNANCE_REVIEW = "governance_control_review"
ENTITY_AI_SYSTEM = "ai_system"


def _norm_ai_high(risk_level: str) -> bool:
    rl = risk_level.strip().lower()
    return rl in {"high", "unacceptable"}


async def _scalar_int(session: AsyncSession, stmt: Select) -> int:
    return int((await session.execute(stmt)).scalar_one())


async def _dedupe_exists(session: AsyncSession, tenant_id: str, dedupe_key: str) -> bool:
    row = (
        await session.scalars(
            select(RemediationActionTable.id).where(
                RemediationActionTable.tenant_id == tenant_id,
                RemediationActionTable.dedupe_key == dedupe_key,
            )
        )
    ).first()
    return row is not None


async def _open_critical_incident_density(session: AsyncSession, tenant_id: str) -> int:
    ops = await _scalar_int(
        session,
        select(func.count()).where(
            ServiceHealthIncidentTable.tenant_id == tenant_id,
            ServiceHealthIncidentTable.incident_state == "open",
            ServiceHealthIncidentTable.severity == "critical",
        ),
    )
    nis2 = await _scalar_int(
        session,
        select(func.count()).where(
            NIS2IncidentTable.tenant_id == tenant_id,
            NIS2IncidentTable.workflow_status.in_(["detected", "reported", "contained"]),
            NIS2IncidentTable.severity.in_(["high", "critical"]),
        ),
    )
    return ops + nis2


async def generate_remediation_actions(
    session: AsyncSession,
    *,
    tenant_id: str,
    actor: str,
    now: datetime | None = None,
) -> tuple[int, list[str]]:
    """Apply small, auditable rules. Returns (created_count, ordered rule_keys with any insert)."""
    ts = now or datetime.now(UTC)
    created = 0
    touched: set[str] = set()

    async def _create(
        *,
        dedupe_key: str,
        title: str,
        description: str,
        category: str,
        rule_key: str,
        priority: str,
        due: datetime | None,
        links: list[tuple[str, str]],
        owner: str | None = None,
    ) -> None:
        nonlocal created
        if await _dedupe_exists(session, tenant_id, dedupe_key):
            return
        aid = str(uuid4())
        session.add(
            RemediationActionTable(
                id=aid,
                tenant_id=tenant_id,
                title=title,
                description=description,
                status="open",
                priority=priority,
                owner=owner,
                due_at_utc=due,
                category=category,
                rule_key=rule_key,
                dedupe_key=dedupe_key,
                created_at_utc=ts,
                updated_at_utc=ts,
                created_by=actor,
            )
        )
        for entity_type, entity_id in links:
            session.add(
                RemediationActionLinkTable(
                    id=str(uuid4()),
                    tenant_id=tenant_id,
                    action_id=aid,
                    entity_type=entity_type,
                    entity_id=entity_id,
                )
            )
        created += 1
        touched.add(rule_key)

    # 1) Evidence gap — implemented controls ohne Evidence (wie Board KPI „evidence gaps“).
    evidence_gap_stmt = (
        select(
            GovernanceControlTable.id, GovernanceControlTable.title, GovernanceControlTable.owner
        )
        .where(
            GovernanceControlTable.tenant_id == tenant_id,
            GovernanceControlTable.status == "implemented",
            not_(
                GovernanceControlTable.id.in_(
                    select(GovernanceControlEvidenceTable.control_id).where(
                        GovernanceControlEvidenceTable.tenant_id == tenant_id,
                    )
                )
            ),
        )
        .limit(150)
    )
    for cid, title, owner in (await session.execute(evidence_gap_stmt)).all():
        dk = f"{RULE_EVIDENCE_GAP}:{cid}"
        await _create(
            dedupe_key=dk,
            title=f"Nachweis nachreichen: {title}",
            description=(
                "Kontrolle ist als umgesetzt markiert, aber es liegt kein Evidence-Datensatz vor. "
                "Bitte Nachweis anlegen oder Status korrigieren."
            ),
            category="audit",
            rule_key=RULE_EVIDENCE_GAP,
            priority="high",
            due=ts + timedelta(days=14),
            links=[(ENTITY_GOVERNANCE_CONTROL, str(cid))],
            owner=owner,
        )

    # 2) Schwache / überfällige Controls (angepasst an Board „open critical controls“).
    weak_stmt = (
        select(
            GovernanceControlTable.id, GovernanceControlTable.title, GovernanceControlTable.owner
        )
        .where(
            GovernanceControlTable.tenant_id == tenant_id,
            GovernanceControlTable.status.in_(["overdue", "needs_review"]),
        )
        .limit(150)
    )
    for cid, title, owner in (await session.execute(weak_stmt)).all():
        dk = f"{RULE_WEAK_CONTROL}:{cid}"
        await _create(
            dedupe_key=dk,
            title=f"Kontrolle nachziehen: {title}",
            description=(
                "Status überfällig oder Review erforderlich — Umsetzung oder Review planen."
            ),
            category="control",
            rule_key=RULE_WEAK_CONTROL,
            priority="medium",
            due=ts + timedelta(days=21),
            links=[(ENTITY_GOVERNANCE_CONTROL, str(cid))],
            owner=owner,
        )

    # 3) Überfällige Reviews.
    overdue_rev_stmt = select(GovernanceControlReviewTable).where(
        GovernanceControlReviewTable.tenant_id == tenant_id,
        GovernanceControlReviewTable.completed_at.is_(None),
        GovernanceControlReviewTable.due_at < ts,
    )
    for rev in (await session.scalars(overdue_rev_stmt)).unique().all():
        dk = f"{RULE_OVERDUE_REVIEW}:{rev.id}"
        await _create(
            dedupe_key=dk,
            title="Überfälliges Control-Review durchführen",
            description=(
                f"Review für Kontrolle {rev.control_id} ist überfällig (Fälligkeit "
                f"{rev.due_at.isoformat()})."
            ),
            category="audit",
            rule_key=RULE_OVERDUE_REVIEW,
            priority="high",
            due=ts + timedelta(days=7),
            links=[
                (ENTITY_GOVERNANCE_REVIEW, rev.id),
                (ENTITY_GOVERNANCE_CONTROL, rev.control_id),
            ],
            owner=rev.reviewer,
        )

    # 4) Kritische Service-Health-Incidents (offen).
    crit_inc_stmt = select(ServiceHealthIncidentTable).where(
        ServiceHealthIncidentTable.tenant_id == tenant_id,
        ServiceHealthIncidentTable.incident_state == "open",
        ServiceHealthIncidentTable.severity == "critical",
    )
    for inc in (await session.scalars(crit_inc_stmt)).unique().all():
        dk = f"{RULE_SERVICE_INCIDENT_CRITICAL}:{inc.id}"
        await _create(
            dedupe_key=dk,
            title=f"Incident-Remediation: {inc.title}",
            description=inc.summary
            or "Kritisches Service-Incident — Ursachenanalyse und Maßnahmenplan.",
            category="incident",
            rule_key=RULE_SERVICE_INCIDENT_CRITICAL,
            priority="critical",
            due=ts + timedelta(days=3),
            links=[(ENTITY_SERVICE_HEALTH_INCIDENT, inc.id)],
            owner=None,
        )

    # 5) Offene Board-Report-Actions → übernehmen als Remediation (Dedupe pro Board-Action-ID).
    board_stmt = select(BoardReportActionTable).where(
        BoardReportActionTable.tenant_id == tenant_id,
        BoardReportActionTable.status == "open",
    )
    for ba in (await session.scalars(board_stmt)).unique().all():
        dk = f"{RULE_BOARD_ACTION_OPEN}:{ba.id}"
        await _create(
            dedupe_key=dk,
            title=ba.action_title,
            description=ba.action_detail or "Maßnahme aus Management Pack / Board Report.",
            category="board",
            rule_key=RULE_BOARD_ACTION_OPEN,
            priority=ba.priority
            if ba.priority in {"critical", "high", "medium", "low"}
            else "medium",
            due=ba.due_at,
            links=[
                (ENTITY_BOARD_REPORT_ACTION, ba.id),
                (ENTITY_BOARD_REPORT, ba.report_id),
            ],
            owner=ba.owner,
        )

    # 6) AI Act high risk ohne ausreichende EU-AI-Act-Kontrollen (Baselinesignal).
    high_ai = (
        await session.scalars(
            select(AISystemTable).where(
                AISystemTable.tenant_id == tenant_id,
            )
        )
    ).all()
    high_ids = [s for s in high_ai if _norm_ai_high(s.risk_level)]
    eu_ai_impl = await _scalar_int(
        session,
        select(func.count()).where(
            GovernanceControlTable.tenant_id == tenant_id,
            GovernanceControlTable.status == "implemented",
            GovernanceControlTable.framework_tags_json.like(f"%{TAG_EU_AI_ACT}%"),
        ),
    )
    if len(high_ids) > 0 and eu_ai_impl == 0:
        dk = RULE_AI_ACT_HIGH_BASELINE
        await _create(
            dedupe_key=dk,
            title="KI-Governance-Baseline für Hochrisiko-Systeme etablieren",
            description=(
                f"{len(high_ids)} KI-System(e) mit hohem Risiko, aber keine umgesetzte EU_AI_ACT-"
                "Kontrolle im Unified-Control-Register. Mindestens eine umgesetzte Kontrolle "
                "anlegen und verknüpfen."
            ),
            category="ai_act",
            rule_key=RULE_AI_ACT_HIGH_BASELINE,
            priority="critical",
            due=ts + timedelta(days=30),
            links=[(ENTITY_AI_SYSTEM, s.id) for s in high_ids[:20]],
            owner=None,
        )

    # 7) NIS2 Exposure hoch + wenige Baseline-Kontrollen (wie Board KPI „open_critical_incidents“).
    exposure = await _open_critical_incident_density(session, tenant_id)
    nis2_impl = await _scalar_int(
        session,
        select(func.count()).where(
            GovernanceControlTable.tenant_id == tenant_id,
            GovernanceControlTable.status == "implemented",
            GovernanceControlTable.framework_tags_json.like(f"%{TAG_NIS2}%"),
        ),
    )
    if exposure >= 5 and nis2_impl < 3:
        dk = RULE_NIS2_BASELINE_PRIORITY
        await _create(
            dedupe_key=dk,
            title="NIS2-Basiskontrollen priorisieren",
            description=(
                f"Offene kritische Incident-Lage ({exposure} Summe Ops+NIS2) bei nur {nis2_impl} "
                "umgesetzten NIS2-Kontrollen. Baseline-Kontrollen beschleunigen."
            ),
            category="nis2",
            rule_key=RULE_NIS2_BASELINE_PRIORITY,
            priority="high",
            due=ts + timedelta(days=14),
            links=[],
            owner=None,
        )

    # 8) Audit-Scope: je Audit-Case + Control ohne Evidence, nicht „implemented“ (Dedupe pro Case).
    scoped_pairs = (
        await session.execute(
            select(
                GovernanceAuditCaseControlTable.audit_case_id,
                GovernanceAuditCaseControlTable.control_id,
            )
            .where(GovernanceAuditCaseControlTable.tenant_id == tenant_id)
            .distinct()
        )
    ).all()
    for audit_case_id, cid in scoped_pairs[:200]:
        ac = await session.get(GovernanceAuditCaseTable, audit_case_id)
        if ac is None or ac.tenant_id != tenant_id:
            continue
        ctl = await session.get(GovernanceControlTable, cid)
        if ctl is None or ctl.tenant_id != tenant_id:
            continue
        if ctl.status == "implemented":
            continue
        has_ev = await _scalar_int(
            session,
            select(func.count()).where(
                GovernanceControlEvidenceTable.tenant_id == tenant_id,
                GovernanceControlEvidenceTable.control_id == cid,
            ),
        )
        if has_ev > 0:
            continue
        dk = f"audit_scope_no_evidence:{audit_case_id}:{cid}"
        await _create(
            dedupe_key=dk,
            title=f"Audit Readiness: Nachweis vorbereiten — {ctl.title}",
            description=(
                f"Kontrolle ist Audit-Case {audit_case_id} zugeordnet, ist aber nicht umgesetzt "
                "und ohne Evidence — Umsetzung oder Nachweisplan für Audit Readiness."
            ),
            category="audit",
            rule_key=RULE_EVIDENCE_GAP,
            priority="medium",
            due=ts + timedelta(days=21),
            links=[
                (ENTITY_GOVERNANCE_AUDIT_CASE, audit_case_id),
                (ENTITY_GOVERNANCE_CONTROL, cid),
            ],
            owner=ctl.owner,
        )

    return created, sorted(touched)


async def tenant_summary_counts(
    session: AsyncSession, tenant_id: str, *, now: datetime | None = None
) -> dict[str, int]:
    """Aggregierte KPIs für Workspace-Kacheln (mandantenweit)."""
    ts = now or datetime.now(UTC)
    week_end = ts + timedelta(days=7)
    active_states = ("open", "in_progress", "blocked")
    open_like = ("open", "in_progress")

    open_actions = await _scalar_int(
        session,
        select(func.count()).where(
            RemediationActionTable.tenant_id == tenant_id,
            RemediationActionTable.status.in_(open_like),
        ),
    )
    overdue_actions = await _scalar_int(
        session,
        select(func.count()).where(
            RemediationActionTable.tenant_id == tenant_id,
            RemediationActionTable.status.in_(active_states),
            RemediationActionTable.due_at_utc.is_not(None),
            RemediationActionTable.due_at_utc < ts,
        ),
    )
    blocked_actions = await _scalar_int(
        session,
        select(func.count()).where(
            RemediationActionTable.tenant_id == tenant_id,
            RemediationActionTable.status == "blocked",
        ),
    )
    due_this_week = await _scalar_int(
        session,
        select(func.count()).where(
            RemediationActionTable.tenant_id == tenant_id,
            RemediationActionTable.status.in_(active_states),
            RemediationActionTable.due_at_utc.is_not(None),
            RemediationActionTable.due_at_utc >= ts,
            RemediationActionTable.due_at_utc <= week_end,
        ),
    )
    backlog_actions = await _scalar_int(
        session,
        select(func.count()).where(
            RemediationActionTable.tenant_id == tenant_id,
            RemediationActionTable.status.in_(active_states),
        ),
    )
    return {
        "open_actions": open_actions,
        "backlog_actions": backlog_actions,
        "overdue_actions": overdue_actions,
        "blocked_actions": blocked_actions,
        "due_this_week": due_this_week,
    }

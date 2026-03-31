"""
Read-model aggregation for AI Act evidence (audit_events + board report rows).

No dedicated evidence table in v1; metadata only, no prompt/answer bodies.
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy import and_, desc, select
from sqlalchemy.orm import Session

from app.evidence.models import (
    AiEvidenceBoardReportCompletedDetailSection,
    AiEvidenceBoardReportWorkflowDetailSection,
    AiEvidenceEventDetail,
    AiEvidenceEventListItem,
    AiEvidenceEventListResponse,
    AiEvidenceLlmDetailSection,
    AiEvidenceRagDetailSection,
    AiEvidenceRagScoreAuditRow,
)
from app.models_db import AiComplianceBoardReportDB
from app.repositories.ai_compliance_board_reports import AiComplianceBoardReportRepository
from app.repositories.audit import AuditEventTable

ENTITY_RAG = "advisor_regulatory_rag"
ENTITY_WORKFLOW_START = "temporal_board_report_workflow"
ENTITY_LLM_CONTRACT = "llm_contract_violation"
ENTITY_LLM_GUARDRAIL = "llm_guardrail_block"

EVENT_RAG = "rag_query"
EVENT_WF_START = "board_report_workflow_started"
EVENT_WF_DONE = "board_report_completed"
EVENT_LLM_VIOLATION = "llm_contract_violation"
EVENT_LLM_GUARD = "llm_guardrail_block"

ALL_AUDIT_ENTITY_TYPES = frozenset(
    {
        ENTITY_RAG,
        ENTITY_WORKFLOW_START,
        ENTITY_LLM_CONTRACT,
        ENTITY_LLM_GUARDRAIL,
    },
)


def _audit_entity_to_event_type(entity_type: str) -> str:
    return {
        ENTITY_RAG: EVENT_RAG,
        ENTITY_WORKFLOW_START: EVENT_WF_START,
        ENTITY_LLM_CONTRACT: EVENT_LLM_VIOLATION,
        ENTITY_LLM_GUARDRAIL: EVENT_LLM_GUARD,
    }.get(entity_type, entity_type)


def _audit_source(entity_type: str) -> str:
    if entity_type == ENTITY_RAG:
        return "rag"
    if entity_type == ENTITY_WORKFLOW_START:
        return "temporal"
    return "llm"


def _summary_de_for_audit(entity_type: str, action: str, meta: dict[str, Any] | None) -> str:
    meta = meta or {}
    if entity_type == ENTITY_RAG:
        cl = str(meta.get("confidence_level") or "")
        tg = int(meta.get("tenant_guidance_citation_count") or 0)
        if cl == "low":
            base = "RAG-Abfrage mit niedriger Konfidenz"
        elif cl == "medium":
            base = "RAG-Abfrage mit mittlerer Konfidenz"
        else:
            base = "RAG-Abfrage (EU AI Act / NIS2 / ISO-Pilot)"
        if tg > 0:
            return f"{base}; Mandanten-Leitfaden-Zitate verwendet"
        return base
    if entity_type == ENTITY_WORKFLOW_START:
        return "Board-Report-Workflow über Temporal gestartet"
    if entity_type == ENTITY_LLM_CONTRACT:
        return "LLM-Ausgabe entsprach nicht dem JSON-Vertrag (Contract Violation)"
    if entity_type == ENTITY_LLM_GUARDRAIL:
        return "LLM-Aufruf durch Guardrail oder Berechtigung gestoppt"
    return f"Audit-Ereignis {entity_type}/{action}"


def _list_item_from_audit(row: AuditEventTable) -> AiEvidenceEventListItem:
    meta = row.metadata_json or {}
    et = row.entity_type
    ev_type = _audit_entity_to_event_type(et)
    user_role = str(meta.get("opa_user_role") or row.actor_type or "")
    cl = meta.get("confidence_level") if et == ENTITY_RAG else None
    purpose = None
    system_id = None
    risk = None
    inp_src: str | None = "human" if et == ENTITY_RAG else None
    out_tgt = None
    if et == ENTITY_RAG:
        purpose = "regulatory_qa"
        out_tgt = "advisor"
        risk = "governance_support"
    elif et == ENTITY_WORKFLOW_START:
        purpose = "board_reporting"
        out_tgt = "board_report"
        inp_src = "human"
        risk = "high_risk_governance"
    elif et in (ENTITY_LLM_CONTRACT, ENTITY_LLM_GUARDRAIL):
        purpose = "llm_inference"
        inp_src = "system"
        risk = "model_output_quality"
    return AiEvidenceEventListItem(
        event_id=f"audit:{row.id}",
        timestamp=row.timestamp,
        event_type=ev_type,
        tenant_id=row.tenant_id,
        user_role=user_role,
        source=_audit_source(et),  # type: ignore[arg-type]
        summary_de=_summary_de_for_audit(et, row.action, meta),
        confidence_level=str(cl) if cl is not None else None,
        purpose=purpose,
        system_id=system_id,
        risk_category=risk,
        input_source=inp_src,  # type: ignore[arg-type]
        output_target=out_tgt,
    )


def _list_item_from_board_report(row: AiComplianceBoardReportDB) -> AiEvidenceEventListItem:
    summary = "Board-Report aus Temporal-Workflow fertiggestellt (KI-generierter Bericht)"
    return AiEvidenceEventListItem(
        event_id=f"board_report:{row.id}",
        timestamp=row.created_at_utc,
        event_type=EVENT_WF_DONE,
        tenant_id=row.tenant_id,
        user_role=str(row.created_by or "system"),
        source="temporal",
        summary_de=summary,
        confidence_level=None,
        purpose="board_reporting",
        system_id=None,
        risk_category="high_risk_governance",
        input_source="human",
        output_target="board_report",
    )


@dataclass
class EvidenceQueryParams:
    tenant_id: str
    from_ts: datetime | None
    to_ts: datetime | None
    event_types: frozenset[str] | None
    confidence_level: str | None
    limit: int
    offset: int


def _normalize_ts(ts: datetime | None) -> datetime | None:
    if ts is None:
        return None
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts


def _audit_types_for_event_filter(
    event_types: frozenset[str] | None,
) -> list[str] | None:
    """None = query all audit-backed types; empty list = skip audit query."""
    if event_types is None or len(event_types) == 0:
        return list(ALL_AUDIT_ENTITY_TYPES)
    mapping = {
        EVENT_RAG: ENTITY_RAG,
        EVENT_WF_START: ENTITY_WORKFLOW_START,
        EVENT_LLM_VIOLATION: ENTITY_LLM_CONTRACT,
        EVENT_LLM_GUARD: ENTITY_LLM_GUARDRAIL,
    }
    out: list[str] = []
    for et in event_types:
        if et in mapping:
            out.append(mapping[et])
    return out


def _merged_evidence_items(
    session: Session,
    *,
    tenant_id: str,
    from_ts: datetime | None,
    to_ts: datetime | None,
    event_types: frozenset[str] | None,
    fetch_limit: int = 5000,
) -> list[AiEvidenceEventListItem]:
    from_ts_n = _normalize_ts(from_ts)
    to_ts_n = _normalize_ts(to_ts)
    audit_types = _audit_types_for_event_filter(event_types)
    items: list[AiEvidenceEventListItem] = []

    if audit_types is not None and len(audit_types) > 0:
        cond = [
            AuditEventTable.tenant_id == tenant_id,
            AuditEventTable.entity_type.in_(audit_types),
        ]
        if from_ts_n is not None:
            cond.append(AuditEventTable.timestamp >= from_ts_n)
        if to_ts_n is not None:
            cond.append(AuditEventTable.timestamp <= to_ts_n)
        stmt = (
            select(AuditEventTable)
            .where(and_(*cond))
            .order_by(desc(AuditEventTable.timestamp), desc(AuditEventTable.id))
            .limit(fetch_limit)
        )
        for row in session.execute(stmt).scalars().all():
            items.append(_list_item_from_audit(row))

    want_reports = event_types is None or len(event_types) == 0 or EVENT_WF_DONE in event_types
    if want_reports:
        cond = [
            AiComplianceBoardReportDB.tenant_id == tenant_id,
            AiComplianceBoardReportDB.raw_payload["source"].as_string()
            == "temporal_board_report_workflow",
        ]
        if from_ts_n is not None:
            cond.append(AiComplianceBoardReportDB.created_at_utc >= from_ts_n)
        if to_ts_n is not None:
            cond.append(AiComplianceBoardReportDB.created_at_utc <= to_ts_n)
        stmt = (
            select(AiComplianceBoardReportDB)
            .where(and_(*cond))
            .order_by(desc(AiComplianceBoardReportDB.created_at_utc))
            .limit(fetch_limit)
        )
        for row in session.execute(stmt).scalars().all():
            items.append(_list_item_from_board_report(row))

    if event_types and len(event_types) > 0:
        allowed = set(event_types)
        items = [i for i in items if i.event_type in allowed]

    return items


def list_ai_events(session: Session, params: EvidenceQueryParams) -> AiEvidenceEventListResponse:
    """Merge audit + completed board reports, filter, paginate."""
    items = _merged_evidence_items(
        session,
        tenant_id=params.tenant_id,
        from_ts=params.from_ts,
        to_ts=params.to_ts,
        event_types=params.event_types,
    )
    if params.confidence_level:
        cl = params.confidence_level.lower()
        items = [
            i
            for i in items
            if i.event_type != EVENT_RAG or (i.confidence_level or "").lower() == cl
        ]
    items.sort(key=lambda x: x.timestamp, reverse=True)
    total = len(items)
    page = items[params.offset : params.offset + params.limit]
    return AiEvidenceEventListResponse(
        items=page,
        total=total,
        limit=params.limit,
        offset=params.offset,
    )


def get_ai_event_detail(
    session: Session,
    tenant_id: str,
    event_id: str,
) -> AiEvidenceEventDetail | None:
    if event_id.startswith("audit:"):
        aid = event_id.split(":", 1)[1]
        row = session.get(AuditEventTable, aid)
        if row is None or row.tenant_id != tenant_id:
            return None
        meta = row.metadata_json or {}
        et = row.entity_type
        ev_type = _audit_entity_to_event_type(et)
        item = _list_item_from_audit(row)
        detail = AiEvidenceEventDetail(
            event_id=event_id,
            timestamp=item.timestamp,
            event_type=ev_type,
            tenant_id=item.tenant_id,
            user_role=item.user_role,
            source=item.source,  # type: ignore[arg-type]
            summary_de=item.summary_de,
            purpose=item.purpose,
            system_id=item.system_id,
            risk_category=item.risk_category,
            input_source=item.input_source,  # type: ignore[arg-type]
            output_target=item.output_target,
        )
        if et == ENTITY_RAG:
            tg = int(meta.get("tenant_guidance_citation_count") or 0)
            raw_audit = meta.get("retrieval_hit_audit") or []
            score_rows: list[AiEvidenceRagScoreAuditRow] = []
            if isinstance(raw_audit, list):
                for row in raw_audit[:20]:
                    if isinstance(row, dict):
                        try:
                            score_rows.append(AiEvidenceRagScoreAuditRow.model_validate(row))
                        except ValidationError:
                            continue
            detail.rag = AiEvidenceRagDetailSection(
                query_sha256=meta.get("query_sha256"),
                citation_doc_ids=list(meta.get("citation_doc_ids") or []),
                tenant_guidance_citation_count=tg,
                confidence_level=meta.get("confidence_level"),
                trace_id=meta.get("trace_id"),
                span_id=meta.get("span_id"),
                citation_count=int(meta.get("citation_count") or 0),
                retrieval_mode=meta.get("retrieval_mode"),
                score_audit=score_rows,
            )
        elif et == ENTITY_WORKFLOW_START:
            detail.board_report_workflow = AiEvidenceBoardReportWorkflowDetailSection(
                workflow_id=row.entity_id,
                task_queue=meta.get("task_queue"),
                status_hint=row.action,
            )
        elif et in (ENTITY_LLM_CONTRACT, ENTITY_LLM_GUARDRAIL):
            detail.llm = AiEvidenceLlmDetailSection(
                action_name=meta.get("llm_action_name"),
                task_type=meta.get("task_type"),
                contract_schema=meta.get("contract_schema"),
                error_class=meta.get("error_class"),
                guardrail_flags=meta.get("guardrail_flags"),
            )
        return detail

    if event_id.startswith("board_report:"):
        rid = event_id.split(":", 1)[1]
        row = AiComplianceBoardReportRepository(session).get(rid, tenant_id)
        if row is None:
            return None
        raw = row.raw_payload or {}
        activities: list[str] = ["load_snapshot"]
        if raw.get("langgraph_oami_explanation"):
            activities.append("langgraph_explain")
        activities.append("persist_board_report")
        item = _list_item_from_board_report(row)
        return AiEvidenceEventDetail(
            event_id=event_id,
            timestamp=item.timestamp,
            event_type=EVENT_WF_DONE,
            tenant_id=item.tenant_id,
            user_role=item.user_role,
            source="temporal",
            summary_de=item.summary_de,
            purpose=item.purpose,
            system_id=item.system_id,
            risk_category=item.risk_category,
            input_source=item.input_source,  # type: ignore[arg-type]
            output_target=item.output_target,
            board_report_completed=AiEvidenceBoardReportCompletedDetailSection(
                report_id=row.id,
                temporal_workflow_id=raw.get("temporal_workflow_id"),
                temporal_run_id=raw.get("temporal_run_id"),
                audience_type=row.audience_type,
                activities_executed=activities,
                title=row.title,
            ),
        )
    return None


def list_ai_events_for_export(
    session: Session,
    params: EvidenceQueryParams,
) -> list[AiEvidenceEventListItem]:
    items = _merged_evidence_items(
        session,
        tenant_id=params.tenant_id,
        from_ts=params.from_ts,
        to_ts=params.to_ts,
        event_types=params.event_types,
        fetch_limit=10_000,
    )
    if params.confidence_level:
        cl = params.confidence_level.lower()
        items = [
            i
            for i in items
            if i.event_type != EVENT_RAG or (i.confidence_level or "").lower() == cl
        ]
    items.sort(key=lambda x: x.timestamp, reverse=True)
    return items


def export_csv_chunks(items: list[AiEvidenceEventListItem]) -> Iterator[bytes]:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "event_id",
            "timestamp",
            "event_type",
            "tenant_id",
            "user_role",
            "source",
            "summary_de",
            "confidence_level",
            "purpose",
            "system_id",
            "risk_category",
            "input_source",
            "output_target",
        ],
    )
    yield buf.getvalue().encode("utf-8")
    buf.seek(0)
    buf.truncate(0)
    for it in items:
        w.writerow(
            [
                it.event_id,
                it.timestamp.isoformat(),
                it.event_type,
                it.tenant_id,
                it.user_role,
                it.source,
                it.summary_de,
                it.confidence_level or "",
                it.purpose or "",
                it.system_id or "",
                it.risk_category or "",
                it.input_source or "",
                it.output_target or "",
            ],
        )
        yield buf.getvalue().encode("utf-8")
        buf.seek(0)
        buf.truncate(0)


def export_json_bytes(items: list[AiEvidenceEventListItem]) -> bytes:
    payload = [i.model_dump(mode="json") for i in items]
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")

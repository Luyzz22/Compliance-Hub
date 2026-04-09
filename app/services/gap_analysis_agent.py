"""RAG-powered gap analysis agent — identifies compliance gaps per tenant (Phase 3).

Uses norm embeddings + tenant compliance status to generate structured gap reports.
LLM: multi-model router, primary Claude Sonnet 4 (no vendor lock-in).
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models_db import ComplianceScoreDB, GapReportDB, NormEmbeddingDB

logger = logging.getLogger(__name__)

GAP_ANALYSIS_LLM_MODEL = os.getenv("COMPLIANCEHUB_GAP_ANALYSIS_MODEL", "claude-sonnet-4-20250514")


def _gather_tenant_compliance_status(session: Session, tenant_id: str) -> dict:
    """Collect current compliance status from DB for gap analysis input."""
    scores = (
        session.execute(
            select(ComplianceScoreDB)
            .where(ComplianceScoreDB.tenant_id == tenant_id)
            .order_by(ComplianceScoreDB.created_at_utc.desc())
            .limit(20)
        )
        .scalars()
        .all()
    )
    return {
        "tenant_id": tenant_id,
        "scores": [
            {"norm": s.norm, "score": s.score_value, "type": s.score_type, "period": s.period}
            for s in scores
        ],
    }


def _gather_relevant_norm_chunks(session: Session, norms: list[str], limit: int = 50) -> list[dict]:
    """Fetch relevant norm embedding chunks for the requested norms."""
    rows = (
        session.execute(
            select(NormEmbeddingDB)
            .where(NormEmbeddingDB.norm.in_(norms))
            .order_by(NormEmbeddingDB.article_ref)
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [
        {
            "norm": r.norm,
            "article_ref": r.article_ref,
            "text_content": r.text_content[:500],
        }
        for r in rows
    ]


def _build_gap_analysis_prompt(
    compliance_status: dict, norm_chunks: list[dict], norms: list[str]
) -> str:
    """Build structured prompt for gap analysis (no PII)."""
    return (
        "Analysiere den aktuellen Compliance-Status des Mandanten und identifiziere Lücken "
        "auf Artikel-Ebene für folgende Normen: " + ", ".join(norms) + ".\n\n"
        "Compliance-Status:\n"
        + json.dumps(compliance_status, ensure_ascii=False, indent=2)
        + "\n\nRelevante Norm-Auszüge:\n"
        + json.dumps(norm_chunks, ensure_ascii=False, indent=2)
        + "\n\n"
        "Erstelle einen strukturierten Gap-Report mit:\n"
        "1. Lücken auf Artikel-Ebene (mit Referenz)\n"
        "2. Priorisierung nach Bußgeldrisiko (critical/high/medium/low)\n"
        "3. Maßnahmenempfehlungen mit Aufwandsschätzung\n"
        "4. Cross-Norm-Hinweise (Map once, comply many)\n"
        "\nFormat: JSON mit keys: gaps (list), cross_norm_hints (list), summary (string)"
    )


def _run_llm_gap_analysis(prompt: str, model: str) -> dict:
    """Call LLM for gap analysis.  Returns structured result.

    In production, this uses the multi-model router with LangSmith tracing.
    Falls back to a structured default when LLM is unavailable.
    """
    trace_id = f"gap-{uuid.uuid4().hex[:12]}"
    logger.info("gap_analysis_llm_call model=%s trace_id=%s", model, trace_id)
    try:
        from app.services.llm_router import route_llm_call

        result = route_llm_call(
            task="gap_analysis",
            prompt=prompt,
            model_preference=model,
        )
        if result and isinstance(result, dict):
            result["_trace_id"] = trace_id
            return result
    except Exception:
        logger.warning("gap_analysis_llm_unavailable, using fallback", exc_info=True)

    return {
        "gaps": [],
        "cross_norm_hints": [],
        "summary": "Gap-Analyse konnte nicht durchgeführt werden — LLM nicht verfügbar.",
        "_trace_id": trace_id,
        "_fallback": True,
    }


def run_gap_analysis(
    session: Session,
    *,
    tenant_id: str,
    norms: list[str] | None = None,
    requested_by: str | None = None,
) -> GapReportDB:
    """Execute gap analysis and persist report."""
    import time

    from app.services.langsmith_tracing import trace_gap_analysis

    target_norms = norms or ["eu_ai_act", "iso_42001", "nis2", "dsgvo"]
    norm_scope = ",".join(target_norms)

    report = GapReportDB(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        status="running",
        norm_scope=norm_scope,
        requested_by=requested_by,
        created_at_utc=datetime.now(UTC),
    )
    session.add(report)
    session.flush()

    t0 = time.monotonic()
    success = False
    try:
        compliance_status = _gather_tenant_compliance_status(session, tenant_id)
        norm_chunks = _gather_relevant_norm_chunks(session, target_norms)
        prompt = _build_gap_analysis_prompt(compliance_status, norm_chunks, target_norms)
        result = _run_llm_gap_analysis(prompt, GAP_ANALYSIS_LLM_MODEL)

        report.gaps_json = json.dumps(result.get("gaps", []), ensure_ascii=False)
        report.summary = result.get("summary", "")
        report.llm_model = GAP_ANALYSIS_LLM_MODEL
        report.llm_trace_id = result.get("_trace_id")
        report.status = "completed"
        report.completed_at_utc = datetime.now(UTC)
        success = True
    except Exception:
        logger.exception("gap_analysis_failed tenant_id=%s", tenant_id)
        report.status = "failed"
        report.summary = "Analyse fehlgeschlagen — siehe Logs."
    finally:
        latency_ms = (time.monotonic() - t0) * 1000
        trace_gap_analysis(
            tenant_id=tenant_id,
            norms=target_norms,
            latency_ms=latency_ms,
            token_estimate=len(norm_scope) * 10,  # rough heuristic: ~10 tokens per char of scope
            model=GAP_ANALYSIS_LLM_MODEL,
            success=success,
        )

    session.flush()
    return report


def get_gap_report(session: Session, tenant_id: str, report_id: str) -> dict | None:
    """Retrieve a gap report by ID for the tenant."""
    row = session.execute(
        select(GapReportDB).where(
            GapReportDB.id == report_id,
            GapReportDB.tenant_id == tenant_id,
        )
    ).scalar_one_or_none()
    if not row:
        return None
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "status": row.status,
        "norm_scope": row.norm_scope,
        "gaps": json.loads(row.gaps_json) if row.gaps_json else [],
        "summary": row.summary,
        "llm_model": row.llm_model,
        "llm_trace_id": row.llm_trace_id,
        "requested_by": row.requested_by,
        "created_at": row.created_at_utc.isoformat() if row.created_at_utc else None,
        "completed_at": row.completed_at_utc.isoformat() if row.completed_at_utc else None,
    }


def list_gap_reports(session: Session, tenant_id: str, limit: int = 20) -> list[dict]:
    """List gap reports for a tenant."""
    rows = (
        session.execute(
            select(GapReportDB)
            .where(GapReportDB.tenant_id == tenant_id)
            .order_by(GapReportDB.created_at_utc.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": r.id,
            "status": r.status,
            "norm_scope": r.norm_scope,
            "summary": r.summary,
            "created_at": r.created_at_utc.isoformat() if r.created_at_utc else None,
            "completed_at": r.completed_at_utc.isoformat() if r.completed_at_utc else None,
        }
        for r in rows
    ]

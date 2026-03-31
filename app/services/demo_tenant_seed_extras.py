"""Zusatz-Seed für Demo-Mandanten: KPI-Zeitreihen, Cross-Reg-Coverage, Wizard, Board-Reports."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import NAMESPACE_DNS, uuid5

from sqlalchemy import select

from app.models_db import (
    ComplianceControlDB,
    ComplianceFrameworkDB,
    ComplianceRequirementControlLinkDB,
    ComplianceRequirementDB,
)
from app.repositories.ai_compliance_board_reports import AiComplianceBoardReportRepository
from app.repositories.ai_kpis import AiKpiRepository
from app.repositories.tenant_ai_governance_setup import TenantAIGovernanceSetupRepository
from app.services.ai_kpi_seed import ensure_ai_kpi_definitions_seeded

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def _control_id(tenant_id: str, slug: str) -> str:
    return str(uuid5(NAMESPACE_DNS, f"compliancehub:demo:{tenant_id}:{slug}"))


_DEMO_KPI_PERIODS: tuple[tuple[datetime, datetime], ...] = (
    (datetime(2025, 10, 1, tzinfo=UTC), datetime(2025, 10, 31, 23, 59, 59, tzinfo=UTC)),
    (datetime(2025, 11, 1, tzinfo=UTC), datetime(2025, 11, 30, 23, 59, 59, tzinfo=UTC)),
)


def _definition_ids_by_keys(session: Session, keys: tuple[str, ...]) -> dict[str, str]:
    repo = AiKpiRepository(session)
    defs = repo.list_definitions()
    by_key = {d.key: str(d.id) for d in defs}
    out: dict[str, str] = {}
    for k in keys:
        if k in by_key:
            out[k] = by_key[k]
    return out


def _eu_ai_act_requirement_ids(session: Session, codes: tuple[str, ...]) -> dict[str, int]:
    fw = session.scalars(
        select(ComplianceFrameworkDB).where(ComplianceFrameworkDB.key == "eu_ai_act"),
    ).one()
    rows = session.scalars(
        select(ComplianceRequirementDB).where(
            ComplianceRequirementDB.framework_id == int(fw.id),
            ComplianceRequirementDB.code.in_(codes),
        ),
    ).all()
    return {r.code: int(r.id) for r in rows}


def apply_demo_seed_extensions(
    session: Session,
    tenant_id: str,
    *,
    primary_ai_system_id: str,
    secondary_ai_system_id: str,
) -> dict[str, int]:
    """
    Idempotent genug für leere Mandanten nach dem Kern-Seed: legt fehlende Artefakte an.
    """
    ensure_ai_kpi_definitions_seeded(session)
    kpi_repo = AiKpiRepository(session)
    def_ids = _definition_ids_by_keys(session, ("incident_rate_ai", "drift_indicator"))
    kpi_rows = 0
    for key in ("incident_rate_ai", "drift_indicator"):
        kid = def_ids.get(key)
        if not kid:
            continue
        for idx, (ps, pe) in enumerate(_DEMO_KPI_PERIODS):
            base = 1.2 + (0.35 * idx) if key == "incident_rate_ai" else 28.0 + (3.0 * idx)
            kpi_repo.upsert_value(
                tenant_id=tenant_id,
                ai_system_id=primary_ai_system_id,
                kpi_definition_id=kid,
                period_start=ps,
                period_end=pe,
                value=float(base),
                source="demo-seed",
                comment="Demo trend",
                new_id=str(uuid.uuid4()),
            )
            kpi_rows += 1

    req_map = _eu_ai_act_requirement_ids(session, ("Art.9", "Art.11", "Art.12"))
    ctrl_specs: list[tuple[str, str, str, str, list[tuple[str, str]]]] = [
        (
            _control_id(tenant_id, "rm"),
            "Risikomanagement-Framework KI (Demo)",
            "Rollen, Methodik und Nachweise zum EU-AI-Act-Art.-9-Bezug.",
            "implemented",
            [("Art.9", "partial")],
        ),
        (
            _control_id(tenant_id, "tdoc"),
            "Technische Dokumentation (Auszug)",
            "Struktur und Freigabeprozess – noch nicht vollständig für alle Systeme.",
            "planned",
            [("Art.11", "partial")],
        ),
        (
            _control_id(tenant_id, "log"),
            "Logging & Aufbewahrung KI-Betrieb",
            "Zentrale Vorgaben; Umsetzung für Teilsysteme offen.",
            "planned",
            [("Art.12", "partial")],
        ),
    ]
    ctrl_count = 0
    for cid, name, desc, st, links in ctrl_specs:
        existing = session.get(ComplianceControlDB, cid)
        if existing is None:
            session.add(
                ComplianceControlDB(
                    id=cid,
                    tenant_id=tenant_id,
                    name=name,
                    description=desc,
                    control_type="process",
                    owner_role="CISO",
                    status=st,
                ),
            )
            session.commit()
            ctrl_count += 1
        for code, level in links:
            rid = req_map.get(code)
            if rid is None:
                continue
            stmt = select(ComplianceRequirementControlLinkDB).where(
                ComplianceRequirementControlLinkDB.requirement_id == rid,
                ComplianceRequirementControlLinkDB.control_id == cid,
            )
            if session.execute(stmt).scalar_one_or_none() is None:
                session.add(
                    ComplianceRequirementControlLinkDB(
                        requirement_id=rid,
                        control_id=cid,
                        coverage_level=level,
                    ),
                )
                session.commit()

    setup_repo = TenantAIGovernanceSetupRepository(session)
    payload = {
        "tenant_kind": "manufacturing_sme",
        "compliance_scopes": ["eu_ai_act", "nis2", "iso_42001"],
        "governance_roles": {"ciso": "demo.ciso@example.com", "dpo": "demo.dpo@example.com"},
        "active_frameworks": ["eu_ai_act", "nis2", "iso_42001"],
        "steps_marked_complete": [1, 2, 3, 4, 5],
        "flags": {
            "gap_assist_previewed": True,
            "board_report_created": False,
        },
    }
    setup_repo.upsert_payload(tenant_id, payload)

    report_repo = AiComplianceBoardReportRepository(session)
    existing_n = len(report_repo.list_for_tenant(tenant_id, limit=5))
    board_n = 0
    if existing_n < 2:
        samples = [
            (
                "AI Compliance Board-Report (Demo) – Q1",
                "board",
                "## Executive Summary (Demo)\n\n"
                "Mandant zeigt solide Grundlagen in Klassifikation und NIS2-KPIs; "
                "Lücken bei Lieferketten-Nachweisen und technischer Dokumentation.\n\n"
                "### Empfehlungen\n"
                "- Supplier-Register für Hochrisiko-KI schließen.\n"
                "- Logging-Konzept mit Fachbereich abstimmen.\n",
            ),
            (
                "Management-Update KI-Governance (Demo)",
                "management",
                "## Kurzüberblick\n\n"
                f"Fokus-KI-Systeme inkl. **{primary_ai_system_id}** und "
                f"**{secondary_ai_system_id}**; Cross-Regulation-Gaps sind sichtbar "
                "im Dashboard.\n",
            ),
        ]
        for title, aud, md in samples[existing_n:]:
            report_repo.create(
                tenant_id=tenant_id,
                created_by="demo-seed",
                title=title,
                audience_type=aud,
                raw_payload={
                    "version": 1,
                    "demo": True,
                    "primary_ai_system_id": primary_ai_system_id,
                },
                rendered_markdown=md,
            )
            board_n += 1

    return {
        "ai_kpi_value_rows_count": kpi_rows,
        "cross_reg_control_rows_count": ctrl_count,
        "board_reports_count": board_n,
    }

"""Aggregiert Readiness, GAI und OAMI für Governance-Maturity-API."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.feature_flags import FeatureFlag, is_feature_enabled
from app.governance_maturity_models import (
    GovernanceActivityBlock,
    GovernanceMaturityResponse,
    GovernanceReadinessBlock,
    OperationalAiMonitoringBlock,
)
from app.services.governance_activity_index import compute_governance_activity_index
from app.services.oami_explanation import explain_tenant_oami_de
from app.services.operational_monitoring_index import compute_tenant_operational_monitoring_index
from app.services.readiness_score_service import compute_readiness_score

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _derive_narrative_tag_ids(
    *,
    readiness_score: int | None,
    gai_index: int,
    oami_has_data: bool,
) -> list[str]:
    tags: list[str] = []
    if readiness_score is not None and readiness_score >= 60 and gai_index < 40:
        tags.append("structurally_strong_low_usage")
    if readiness_score is not None and readiness_score < 45:
        tags.append("readiness_needs_attention")
    if not oami_has_data:
        tags.append("operational_monitoring_not_visible")
    elif gai_index >= 60 and readiness_score is not None and readiness_score >= 60:
        tags.append("balanced_governance_signals")
    return tags


def build_governance_maturity_response(
    session: Session,
    tenant_id: str,
    *,
    window_days: int = 90,
) -> GovernanceMaturityResponse:
    now = datetime.now(UTC)
    readiness_block: GovernanceReadinessBlock | None = None
    readiness_display: int | None = None

    if is_feature_enabled(FeatureFlag.readiness_score, tenant_id, session=session):
        try:
            rs = compute_readiness_score(session, tenant_id)
            readiness_block = GovernanceReadinessBlock(
                score=rs.score,
                level=str(rs.level),
                interpretation=rs.interpretation,
            )
            readiness_display = rs.score
        except Exception:
            logger.exception("governance_maturity_readiness_failed tenant=%s", tenant_id)

    try:
        gai = compute_governance_activity_index(
            session,
            tenant_id,
            window_days=window_days,
            as_of=now,
        )
    except Exception:
        logger.exception("governance_maturity_gai_failed tenant=%s", tenant_id)
        gai = GovernanceActivityBlock(
            index=0,
            level="low",
            window_days=window_days,
            last_computed_at=now,
            components=None,
        )

    oami_block: OperationalAiMonitoringBlock
    try:
        oami = compute_tenant_operational_monitoring_index(
            session,
            tenant_id,
            window_days=window_days,
            persist_snapshot=False,
        )
        expl = explain_tenant_oami_de(oami)
        if oami.has_any_runtime_data:
            oami_block = OperationalAiMonitoringBlock(
                status="active",
                index=oami.operational_monitoring_index,
                level=oami.level,
                window_days=window_days,
                message_de=expl.summary_de,
                drivers_de=list(expl.drivers_de),
            )
        else:
            oami_block = OperationalAiMonitoringBlock(
                status="not_configured",
                index=None,
                level=None,
                window_days=window_days,
                message_de=expl.summary_de,
                drivers_de=list(expl.drivers_de),
            )
    except Exception:
        logger.exception("governance_maturity_oami_failed tenant=%s", tenant_id)
        oami_block = OperationalAiMonitoringBlock(
            status="not_configured",
            window_days=window_days,
            message_de="Operatives Monitoring konnte nicht geladen werden.",
        )

    tags = _derive_narrative_tag_ids(
        readiness_score=readiness_display,
        gai_index=gai.index,
        oami_has_data=oami_block.status == "active",
    )

    return GovernanceMaturityResponse(
        tenant_id=tenant_id,
        computed_at=now,
        readiness=readiness_block,
        governance_activity=gai,
        operational_ai_monitoring=oami_block,
        narrative_tag_ids=tags,
        readiness_display_score=readiness_display,
        readiness_score_adjustment_note=None,
    )

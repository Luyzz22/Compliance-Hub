"""Temporal activity stub for deployment-check integration (Wave 14).

This activity is designed to be called from a future
``DeployAiSystemWorkflow`` before promoting a system to production.
It calls the deployment-check evaluation and logs the result but
**never** fails the workflow — the result is purely advisory.

Usage in a Temporal workflow (future):

    check_result = await workflow.execute_activity(
        "check_deployment_readiness_activity",
        {"tenant_id": ..., "system_id": ..., "trace_id": ...},
        start_to_close_timeout=timedelta(minutes=2),
    )
    # check_result is logged; workflow continues regardless.

TODO (future waves):
- Wire into DeployAiSystemWorkflow once that workflow exists.
- Add optional "require_human_approval" signal if is_high_risk_candidate
  and readiness_level == "insufficient_evidence".
- Integrate with Temporal schedules for periodic readiness polling.
"""

from __future__ import annotations

import logging

from temporalio import activity

from app.grc.ai_system_readiness import deployment_check

logger = logging.getLogger(__name__)


@activity.defn
def check_deployment_readiness_activity(params: dict) -> dict:
    """Run deployment-check and return result.  Never raises."""
    tenant_id = str(params.get("tenant_id", ""))
    system_id = str(params.get("system_id", ""))
    trace_id = str(params.get("trace_id", ""))

    result = deployment_check(
        tenant_id=tenant_id,
        system_id=system_id,
        caller_type="temporal",
        trace_id=trace_id,
    )

    if "error" in result:
        logger.warning(
            "deployment_check_not_found",
            extra={"system_id": system_id, "error": result["error"]},
        )
        return {"status": "not_found", "error": result["error"]}

    logger.info(
        "deployment_check_completed",
        extra={
            "system_id": system_id,
            "readiness_level": result.get("readiness_level"),
            "is_high_risk_candidate": result.get("is_high_risk_candidate"),
        },
    )
    return result

# Wave 14 — Deployment Checks & Advisory Gates

## Overview

Wave 14 adds a lightweight, opt-in **deployment-check mechanism** that
lets CI pipelines and Temporal workflows query AiSystem readiness before
deploying or promoting changes.  The check surfaces clear, actionable
information (what's missing) without auto-blocking — final decisions
remain with humans.

## Deployment-Check Endpoint

### `GET /api/v1/ai-systems/{system_id}/deployment-check`

**Query parameters:**
- `tenant_id` — override (defaults to auth context)
- `caller_type` — `ci` | `temporal` | `manual` (logged for audit)
- `trace_id` — optional correlation ID

**Response:**
```json
{
  "system_id": "SAP-CREDIT-AI-01",
  "lifecycle_stage": "pilot",
  "classification": "high_risk_candidate",
  "readiness_level": "partially_covered",
  "is_high_risk_candidate": true,
  "blocking_items": [
    "Offene ISO 42001 Kern-Gaps: governance",
    "Kein aktueller Board-Report für dieses High-Risk-Candidate-System vorhanden"
  ],
  "advisory_message_de": "System \u201eSAP-CREDIT-AI-01\u201c ...",
  "has_recent_board_report": false
}
```

**Semantics:**
- Always advisory, never hard-blocks
- OPA-secured (`view_ai_systems`)
- Every call logged as `deployment_check` evidence event

## Blocking Items

The check surfaces actionable blocking items:

| Condition | Blocking Item |
|-----------|---------------|
| No risk assessment | "Keine Risikobewertung vorhanden" |
| Open core ISO 42001 gaps (governance/data/monitoring) | "Offene ISO 42001 Kern-Gaps: ..." |
| NIS2 obligations not in progress | "NIS2-Pflichten noch nicht in Bearbeitung" |
| No business/technical owner | "Kein Business- oder Technical-Owner hinterlegt" |
| HRC without recent board report | "Kein aktueller Board-Report ..." |

## Board Report Linkage

If a board report covering the system was generated within the last
90 days, this is noted positively in the advisory message.  Conversely,
for `high_risk_candidate` systems, a missing recent report is flagged
as a blocking item — connecting the Kanzlei/Mandant reporting flow
(Wave 13) with deployment readiness.

## CI Integration

### Script: `scripts/ci/check_ai_system_readiness.py`

```bash
python scripts/ci/check_ai_system_readiness.py \
  --system-id SAP-CREDIT-AI-01 \
  --tenant-id acme-gmbh \
  --api-url https://compliancehub.example.com
```

**Exit codes:**
| Code | Meaning |
|------|---------|
| 0 | OK — ready or non-critical partial coverage |
| 1 | Warning — HRC with insufficient evidence, or strict mode with blocking items |
| 2 | Error — API unreachable or system not found |

### GitHub Actions Example

```yaml
jobs:
  deploy:
    steps:
      - name: Check AI System Readiness
        env:
          AI_SYSTEM_ID: SAP-CREDIT-AI-01
          COMPLIANCEHUB_TENANT_ID: ${{ secrets.TENANT_ID }}
          COMPLIANCEHUB_API_URL: ${{ secrets.API_URL }}
          COMPLIANCEHUB_API_KEY: ${{ secrets.API_KEY }}
        run: |
          python scripts/ci/check_ai_system_readiness.py \
            --system-id $AI_SYSTEM_ID
        continue-on-error: true  # advisory, not blocking

      - name: Deploy
        run: ./deploy.sh
```

For stricter enforcement (future):
```yaml
        run: |
          python scripts/ci/check_ai_system_readiness.py \
            --system-id $AI_SYSTEM_ID --strict
        # Remove continue-on-error to hard-block
```

## Temporal Integration

### Activity Stub: `check_deployment_readiness_activity`

```python
# In a future DeployAiSystemWorkflow:
check_result = await workflow.execute_activity(
    "check_deployment_readiness_activity",
    {"tenant_id": ..., "system_id": ..., "trace_id": ...},
    start_to_close_timeout=timedelta(minutes=2),
)
# Result is logged; workflow continues regardless.
```

The activity:
- Calls `deployment_check()` with `caller_type="temporal"`
- Logs evidence event
- Never raises — always returns result dict
- Ready to wire into future deployment workflows

### Future: Human Approval Signal

```python
if check_result.get("is_high_risk_candidate") and \
   check_result.get("readiness_level") == "insufficient_evidence":
    # Signal human review needed
    await workflow.wait_condition(lambda: self.human_approved)
```

## Evidence Trail

Every deployment check creates an evidence event:

```json
{
  "event_type": "deployment_check",
  "tenant_id": "acme-gmbh",
  "system_id": "SAP-CREDIT-AI-01",
  "caller_type": "ci",
  "classification": "high_risk_candidate",
  "readiness_level": "partially_covered",
  "blocking_items_count": 2,
  "trace_id": "CI-TRACE-001"
}
```

This enables auditors to verify: "Was a deployment-readiness check
performed before this system went to production?"

## Foundation for Future Hard Gates

This wave establishes the foundation.  Future waves can add:

1. **Opt-in hard blocking**: Remove `continue-on-error` in CI, or
   add `workflow.wait_condition` in Temporal
2. **Human confirmation workflow**: CISO approves HRC → production
3. **Scheduled re-checks**: Temporal cron checks readiness weekly
4. **Webhook notifications**: Alert Slack/Teams when readiness drops
5. **Audit compliance reports**: "100% of HRC deployments had a
   pre-deployment readiness check in Q1 2026"

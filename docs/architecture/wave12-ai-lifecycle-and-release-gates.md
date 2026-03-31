# Wave 12 — AI Lifecycle & Release-Gate Model

## Overview

Wave 12 adds a lightweight lifecycle and release-gate layer to `AiSystem`,
aligned with ISO 42001 lifecycle management ideas and EU AI Act
pre-deployment readiness expectations.

The model tracks lifecycle stages, computes advisory readiness hints from
existing GRC records and framework mappings, and exposes this via API —
without ever auto-blocking or auto-certifying.  Final go/no-go remains a
human decision.

## Lifecycle Stages

| Stage        | Meaning                                               |
|--------------|-------------------------------------------------------|
| `idea`       | Concept/ideation phase, no formal development started |
| `design`     | Architecture and requirements being defined           |
| `development`| Active development, model training, integration       |
| `testing`    | Internal QA, validation, adversarial testing          |
| `pilot`      | Limited production deployment, controlled scope       |
| `production` | Full production deployment                            |
| `retired`    | System decommissioned                                 |

Lifecycle stages are **never auto-advanced** by the platform.  They are
set by humans (via future UI) or external systems (e.g. CI/CD webhooks).

## Readiness Levels

| Level                    | Meaning                                          |
|--------------------------|--------------------------------------------------|
| `unknown`                | No evidence at all for this system               |
| `insufficient_evidence`  | Some records exist but key areas are missing     |
| `partially_covered`      | Core areas have evidence, some gaps remain open  |
| `ready_for_review`       | All key areas covered, suitable for human review |

## Readiness Evaluation Rules

The readiness service (`app/grc/ai_system_readiness.py`) applies simple,
transparent rules:

### `ready_for_review` requires:
1. At least one `AiRiskAssessment` exists for the system
2. If `ai_act_classification` is `high_risk_candidate` or `high_risk`:
   no open ISO 42001 gaps in core families (governance, data, monitoring)
3. If `nis2_relevant`: all NIS2 obligations at least `in_progress`

### `partially_covered`:
- Risk assessment exists but blocking items remain (gaps or obligations)

### `insufficient_evidence`:
- Risk assessment exists but critical areas are open (e.g. core ISO 42001
  gaps for a high-risk candidate)

### `unknown`:
- No GRC records at all

These rules are **advisory and intentionally simple**.  They are documented
in code comments and can be adjusted as regulations evolve.

## Per-Framework Hints

The readiness API returns structured hints per framework:

```json
{
  "eu_ai_act": {
    "has_risk_assessment": true,
    "classification": "high_risk_candidate",
    "findings": ["System als high_risk_candidate markiert"]
  },
  "nis2": {
    "relevant": true,
    "total_obligations": 2,
    "open_obligations": 1,
    "findings": ["2 Pflicht(en) identifiziert, 1 offen"]
  },
  "iso42001": {
    "in_scope": true,
    "total_gaps": 3,
    "open_gaps": 1,
    "open_core_families": ["monitoring"],
    "findings": ["3 Gap(s) erfasst, 1 offen"]
  }
}
```

## API Endpoint

### `GET /api/v1/ai-systems/{system_id}/readiness`

Returns:
- `lifecycle_stage`: current stage
- `readiness_level`: computed level
- `framework_hints`: per-framework details
- `blocking_items`: list of blocking findings (German-language)
- `framework_coverage`: articles/controls with evidence

Secured via OPA (`view_ai_systems`).

Each call also:
- Updates `readiness_level` and `last_reviewed_at` on the AiSystem record
- Logs a `readiness_evaluation` evidence event (no PII, only IDs/statuses)

## Evidence Traceability

```
readiness_evaluation (event)
  ├── ai_system_id: SYS-abc123
  ├── system_id: SAP-CREDIT-AI-01
  ├── readiness_level: partially_covered
  ├── blocking_items_count: 2
  └── trace_id → can link to advisor/GRC events
```

## Example Scenarios

### Scenario 1: New scoring model in „development"

- **System**: `SAP-CREDIT-AI-01`, `lifecycle_stage=development`
- **GRC records**: One risk assessment (high_risk_candidate), no gaps recorded
- **Readiness**: `insufficient_evidence`
- **Blocking**: "Keine ISO 42001 Gap-Analyse durchgeführt"
- **Action**: Compliance officer triggers ISO 42001 gap check preset

### Scenario 2: Mature system in „pilot" ready for review

- **System**: `HR-SCREENING-01`, `lifecycle_stage=pilot`
- **GRC records**:
  - Risk assessment: high_risk_candidate
  - NIS2 obligations: 2 identified, both `in_progress`
  - ISO 42001 gaps: governance (closed), data (closed), monitoring (closed)
- **Readiness**: `ready_for_review`
- **Blocking**: none
- **Action**: CISO reviews and confirms classification → `high_risk`

## Temporal / CI Integration (Future)

### Temporal Workflows
A Temporal workflow (e.g. „deploy-high-risk-model") could call the
readiness API before executing the deployment step:

```python
readiness = call_readiness_api(system_id)
if readiness["readiness_level"] != "ready_for_review":
    signal_human_review(readiness["blocking_items"])
    await human_approval_signal()
```

### CI/CD Gate (e.g. GitHub Actions)
A pre-merge check could query the readiness API and annotate the PR:

```yaml
- name: Check AI System Readiness
  run: |
    RESULT=$(curl -s .../api/v1/ai-systems/$SYSTEM_ID/readiness)
    LEVEL=$(echo $RESULT | jq -r .readiness_level)
    if [ "$LEVEL" != "ready_for_review" ]; then
      echo "::warning::AI System not ready: $LEVEL"
    fi
```

Both patterns are **advisory** — they surface information but do not
hard-block without human consent.

## Design Principles

- **Advisory, not enforcement**: Gates inform, they don't block
- **Human-in-the-loop**: Classification upgrades and go-live decisions need explicit human action
- **Transparent rules**: Every readiness rule is documented and easy to modify
- **Full traceability**: Every evaluation is logged as an evidence event
- **Tenant separation**: All queries scoped to `tenant_id` via OPA

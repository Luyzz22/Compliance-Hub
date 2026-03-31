# Wave 9 — Advisor Presets & DATEV/SAP Alignment

## Overview

Wave 9 introduces **advisor preset micro-flows** — structured, domain-specific entry points into the generic advisor stack, designed around the questions that Kanzleien (DATEV) and Industrie-Mittelstand (SAP) actually ask.

No direct DATEV/SAP API integration yet, but every preset is designed so a future connector can call it 1:1.

## Chosen Micro-Flows

### 1. EU AI Act Risk Assessment

**Endpoint:** `POST /api/v1/advisor/presets/eu-ai-act-risk-assessment`

**Use case:** A Steuerberater or Compliance-Beauftragter wants to know whether a planned AI use case is likely high-risk under the EU AI Act.

**Why this matters:**
- Art. 6 + Annex III classification is the single most frequent compliance question for companies deploying AI
- DATEV-Kanzleien advise mid-market clients on exactly this question
- SAP customers need to assess their AI modules (predictive analytics, intelligent RPA)

**Input:**
| Field | Type | Required | Description |
|---|---|---|---|
| `use_case_description` | string | yes | The planned AI use case |
| `industry_sector` | string | no | Industry (e.g. Finanzdienstleistungen) |
| `intended_purpose` | string | no | Intended purpose of the AI system |
| `channel` | enum | no | web / sap / datev / api_partner |
| `channel_metadata` | object | no | DATEV client no., SAP doc ID, etc. |

**Expected tags:** `eu_ai_act`, `high_risk`, `conformity_assessment`

### 2. NIS2 Obligations

**Endpoint:** `POST /api/v1/advisor/presets/nis2-obligations`

**Use case:** A compliance team needs to understand what NIS2 obligations apply to a specific entity role (e.g. KRITIS-naher Zulieferer).

**Why this matters:**
- NIS2 implementation (NIS2UmsuCG) affects ~30.000 companies in Germany
- Entity role → obligation mapping is complex and frequently misunderstood
- Kanzleien need to advise multiple Mandanten with different roles

**Input:**
| Field | Type | Required | Description |
|---|---|---|---|
| `entity_role` | string | yes | Role (e.g. KRITIS-naher Zulieferer) |
| `sector` | string | no | Sector (e.g. Energie, Transport) |
| `employee_count` | string | no | Size category (50-249, 250+) |
| `channel` | enum | no | web / sap / datev / api_partner |
| `channel_metadata` | object | no | Channel-specific refs |

**Expected tags:** `nis2`, `incident_reporting`, `risk_management`

### 3. ISO 42001 Gap Check

**Endpoint:** `POST /api/v1/advisor/presets/iso42001-gap-check`

**Use case:** A company with existing governance measures wants to understand gaps relative to ISO 42001.

**Why this matters:**
- ISO 42001 is becoming the standard for AI governance certification
- Companies with ISO 27001 need to understand what additional measures ISO 42001 requires
- Gap analysis is a natural starting point for a consulting engagement

**Input:**
| Field | Type | Required | Description |
|---|---|---|---|
| `current_measures` | string | yes | Description of existing governance |
| `ai_system_count` | string | no | Number of AI systems in scope |
| `channel` | enum | no | web / sap / datev / api_partner |
| `channel_metadata` | object | no | Channel-specific refs |

**Expected tags:** `iso_42001`, `risk_management`, `conformity_assessment`

## Architecture

### Thin Wrapper Pattern

Presets are **thin wrappers** around the existing advisor service — no separate business logic:

```
Preset Endpoint
  ├─ Validate structured input (Pydantic model)
  ├─ Build natural-language query from fields
  ├─ Enforce OPA policy (action = advisor_preset_{flow_type})
  ├─ Create AdvisorRequest with:
  │   ├─ channel, channel_metadata (from input)
  │   ├─ flow_type (from preset definition)
  │   └─ extra_tags (from preset definition)
  └─ Call run_advisor() — the generic GA service layer
        ├─ Idempotency check
        ├─ Agent execution (with timeout)
        ├─ Channel-aware formatting
        ├─ Structured output derivation
        └─ Evidence & metrics logging (with flow_type)
```

All existing guardrails, policies, error handling, SLA enforcement, and auditability remain fully active.

### Channel-Specific Formatting

| Channel | Format | Disclaimer | Structured fields |
|---|---|---|---|
| `web` | Full text + normal disclaimer | Standard | In response JSON, not in answer text |
| `datev` | Structured: tags + next steps in answer text | Kanzlei-specific (stronger) | Embedded in answer |
| `sap` | Structured: tags + next steps in answer text | Short | Embedded in answer |
| `api_partner` | Full text + normal disclaimer | Standard | In response JSON |

DATEV channel uses `DISCLAIMER_KANZLEI`: stronger wording about professional responsibility, appropriate for Berufsträger advising Mandanten.

### Evidence & Metrics Tagging

Every preset invocation is tagged with:
- `flow_type` in the agent event `extra` field → appears in metrics as `flow_type_distribution`
- `channel` in the agent event → appears in `channel_distribution`
- `flow_type` in `AdvisorResponseMeta` and `ref_ids`

This enables:
- Per-flow volume, confidence, and escalation rate tracking
- Identification of which flows have quality/safety issues
- Channel-specific usage patterns for DATEV vs. SAP vs. web

### OPA Policy Integration

Each preset endpoint enforces an OPA policy with a distinct action name:
- `advisor_preset_eu_ai_act_risk_assessment` (risk_score: 0.6)
- `advisor_preset_nis2_obligations` (risk_score: 0.6)
- `advisor_preset_iso42001_gap_check` (risk_score: 0.6)

This allows fine-grained access control per flow type.

## Preset Registry

All preset definitions live in `app/advisor/presets.py` with a central `PRESET_REGISTRY`:

```python
PRESET_REGISTRY: dict[FlowType, dict[str, Any]] = {
    FlowType.eu_ai_act_risk_assessment: {
        "build_query": build_eu_ai_act_risk_query,
        "extra_tags": EU_AI_ACT_RISK_EXTRA_TAGS,
        "input_model": EuAiActRiskAssessmentInput,
    },
    # ...
}
```

Adding a new preset requires:
1. Define a `FlowType` enum value
2. Add input model (Pydantic)
3. Write a `build_*_query` function
4. Register in `PRESET_REGISTRY`
5. Add endpoint in `main.py` (3 lines calling `_run_preset`)

## Path to Real DATEV/SAP Integrations

This wave sets the stage for real integrations:

| Current (Wave 9) | Future (DATEV Integration) | Future (SAP Integration) |
|---|---|---|
| `channel=datev` in request | DATEV DMS webhook calls preset endpoint | SAP BTP event calls preset endpoint |
| `channel_metadata.datev_client_number` | Extracted from DATEV context | — |
| `channel_metadata.sap_document_id` | — | Extracted from SAP document flow |
| Structured answer with tags/steps | Mapped to DATEV Aufgaben / Hinweise | Mapped to SAP workflow tasks |
| `flow_type` in evidence | Links to DATEV audit trail | Links to SAP GRC findings |

The preset endpoints are **the integration surface** — a DATEV connector would POST to the same endpoint with `channel=datev` and the appropriate metadata.

## Test Coverage

21 tests covering:
- Query building for all 3 presets (6 tests)
- Request mapping: channel, metadata, flow_type propagation (3 tests)
- Response shape: structured fields, DATEV vs. web formatting (3 tests)
- Evidence & metrics: flow_type in events, metrics aggregation (3 tests)
- Channel formatting: DATEV structured, SAP structured, web default (5 tests)
- Registry completeness (1 test)

## Files Changed

| File | Change |
|---|---|
| `app/advisor/presets.py` | **New** — Preset definitions, input schemas, query builders, registry |
| `app/advisor/service.py` | Extended `AdvisorRequest` with `flow_type` + `extra_tags`; propagated to response and evidence |
| `app/advisor/response_models.py` | Added `flow_type` to `AdvisorResponseMeta` |
| `app/advisor/channels.py` | Added `use_structured_format()` and `is_kanzlei_channel()` |
| `app/advisor/templates.py` | Added `DISCLAIMER_KANZLEI`, `ANSWER_STRUCTURED`, `format_structured_answer()` |
| `app/advisor/formatting.py` | Extended `format_answer_for_channel()` with tags/next_steps for structured channels |
| `app/advisor/metrics.py` | Added `flow_type_distribution` to metrics aggregation |
| `app/main.py` | Added 3 preset endpoints + `_run_preset` shared handler |
| `tests/test_advisor_presets.py` | **New** — 21 tests |
| `docs/architecture/wave9-advisor-presets-and-datev-sap-alignment.md` | **New** — This document |

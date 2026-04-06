# Wave 10 — Assess Once, Comply Many

## Overview

Wave 10 turns advisor answers into **structured compliance artefacts**. When an advisor preset runs successfully, it automatically creates or updates a GRC record (risk, obligation, or gap) that can be reused across frameworks and consumed by downstream systems.

```
Advisor Preset Call
  → AI Agent (RAG + LangGraph)
    → Preset Result (human + machine + grc)
      → GRC Record (persisted artefact)
        → Evidence Event (traceability link)
```

This implements the "assess once, comply many" pattern: one AI Act risk assessment can feed both an AI risk register and an ISMS risk matrix, without re-running the advisor.

## GRC Core Entities

Three lightweight entities, intentionally small and additive:

### AiRiskAssessment

| Field | Type | Purpose |
|---|---|---|
| `id` | string | Stable ID (RISK-xxxx) |
| `tenant_id`, `client_id`, `system_id` | string | Enterprise context |
| `risk_category` | string | high_risk / limited_risk / minimal_risk / unclassified |
| `use_case_type` | string | credit_scoring, recruitment, etc. |
| `high_risk_likelihood` | string | likely / unlikely / unclear / unknown |
| `conformity_assessment_required` | bool? | Art. 43 trigger |
| `status` | enum | open → accepted → superseded |
| `source_preset_type`, `source_event_id`, `source_trace_id` | string | Traceability back to advisor |

### Nis2ObligationRecord

| Field | Type | Purpose |
|---|---|---|
| `id` | string | Stable ID (NIS2-xxxx) |
| `nis2_entity_type` | string | essential / important / out_of_scope |
| `obligation_tags` | list[str] | incident_reporting, risk_management, etc. |
| `reporting_deadlines` | list[str] | 24h_early_warning, 72h_notification, etc. |
| `entity_role`, `sector` | string | Input context |
| `status` | enum | identified → in_progress → fulfilled |

### Iso42001GapRecord

| Field | Type | Purpose |
|---|---|---|
| `id` | string | Stable ID (GAP-xxxx) |
| `control_families` | list[str] | governance, risk, data, monitoring, etc. |
| `gap_severity` | string | critical / major / minor / none / unknown |
| `iso27001_overlap` | bool? | Whether ISO 27001 partially covers the gap |
| `status` | enum | open → remediation_planned → closed |

## Mapping: Preset → GRC Entity

```
preset_service.py                    ai_presets_mapper.py
┌──────────────────┐                ┌───────────────────┐
│ run_eu_ai_act_   │ ──PresetResult──→ map_preset_to_grc │
│   risk_preset()  │                │                   │
│                  │                │ • Check: not       │
│ run_nis2_        │                │   escalated/error  │
│   obligations_   │                │ • Build GRC entity │
│   preset()       │                │ • Upsert (idemp.)  │
│                  │                │ • Log evidence     │
│ run_iso42001_    │                │ • Return record ID │
│   gap_preset()   │                └───────────────────┘
└──────────────────┘
```

### When records are NOT created

| Condition | Behavior |
|---|---|
| Agent error (timeout, LLM failure) | Skipped — no unreliable artefact |
| Policy refusal (prohibited topic) | Skipped — needs human decision |
| Escalation (low confidence) | Skipped — needs human review |
| `needs_manual_followup = true` | Skipped |

These cases are logged in metrics/evidence so GRC can be completed manually later.

### Idempotency

Records use an idempotency key: `{tenant_id}:{client_id}:{system_id}:{entity_type}`

- Same key → **update** existing record (preserves ID, created_at, status)
- Different key → **create** new record

This means:
- Re-running a preset for the same AI system updates the existing risk assessment
- Running for a different system creates a separate record
- SAP/DATEV retries (with same context) don't create duplicates

## Read-Only API Endpoints

| Endpoint | Filters | Purpose |
|---|---|---|
| `GET /api/v1/grc/ai-risks` | tenant_id, client_id, system_id | SAP GRC / ISMS integration |
| `GET /api/v1/grc/nis2-obligations` | tenant_id, client_id, entity_type | NIS2 compliance dashboard |
| `GET /api/v1/grc/iso42001-gaps` | tenant_id, client_id, control_family | Gap analysis reporting |

All secured via OPA (`view_grc_records`). Write paths remain internal (advisor-driven only).

## Evidence & Traceability Chain

```
┌────────────┐     ┌──────────────────┐     ┌──────────────┐
│ Input      │ ──→ │ Advisor Decision │ ──→ │ GRC Artefact │
│ Context    │     │ (Evidence Event)  │     │ (Record)     │
│            │     │                  │     │              │
│ tenant_id  │     │ trace_id         │     │ id: RISK-... │
│ client_id  │     │ flow_type        │     │ source_      │
│ system_id  │     │ decision         │     │  trace_id    │
│ query_hash │     │ confidence       │     │ source_      │
└────────────┘     └──────────────────┘     │  event_id    │
                          │                 └──────────────┘
                          │                        │
                          ▼                        ▼
                   ┌──────────────────────────────────────┐
                   │ grc_record_created event             │
                   │  • grc_record_id                     │
                   │  • flow_type                         │
                   │  • trace_id (links back to advisor)  │
                   │  • tenant_id, client_id, system_id   │
                   └──────────────────────────────────────┘
```

An auditor can:
1. Start from an AI Act Evidence view
2. See the advisor decision (confidence, escalation)
3. Jump to the resulting GRC record
4. See the full chain: input → AI advice → compliance artefact

## Reuse Across Frameworks

One preset run can feed multiple compliance needs:

### Example: AI Act Risk Assessment

```
                     ┌─ AI Risk Register (Art. 49)
Preset Result ──────→│
  risk_category:     ├─ ISMS Risk Matrix (ISO 27001 Annex A.5)
    high_risk        │
  tags: [eu_ai_act]  └─ ISO 42001 Gap Input (cross-reference)
```

The GRC record contains all fields needed by:
- EU AI Act compliance (risk_category, conformity_assessment_required)
- ISMS risk matrices (risk_category maps to ISO 27005 severity)
- ISO 42001 scope definition (system_id, use_case_type)

### Example: NIS2 Obligations

```
                     ┌─ NIS2 Pflichtenkatalog
Preset Result ──────→│
  obligation_tags:   ├─ BCM Plan (ISO 22301)
    [incident_rep,   │
     risk_mgmt,      └─ ISMS Annex A controls (ISO 27001)
     supply_chain]
```

## Future SAP/DATEV Integration

### DATEV Add-on: Mandant Compliance Dossier

```
DATEV DMS Plugin
  │
  ├─ GET /api/v1/grc/ai-risks?tenant_id=kanzlei&client_id=mandant-123
  │   → Returns AI risk assessments for this Mandant
  │
  ├─ GET /api/v1/grc/nis2-obligations?tenant_id=kanzlei&client_id=mandant-123
  │   → Returns NIS2 obligations for this Mandant
  │
  └─ Renders in DATEV Compliance-Modul:
     - Risiko-Register (from ai-risks)
     - Pflichtenkatalog (from nis2-obligations)
     - Gap-Analyse (from iso42001-gaps)
```

### SAP S/4HANA Extension: Production Site Compliance

```
SAP BTP / GRC Module
  │
  ├─ GET /api/v1/grc/nis2-obligations?tenant_id=acme&system_id=WERK-SUED
  │   → Returns NIS2 obligations for Werk Süd
  │
  ├─ Maps to SAP GRC Finding:
  │   finding_type: NIS2_OBLIGATION
  │   obligations: obligation_tags
  │   deadlines: reporting_deadlines
  │
  └─ GET /api/v1/grc/ai-risks?tenant_id=acme&system_id=QA-AI-01
     → Returns AI risk assessment for QA AI system
     → Creates SAP EHS risk record
```

## Files

| File | Change |
|---|---|
| `app/grc/__init__.py` | **New** — Package |
| `app/grc/models.py` | **New** — AiRiskAssessment, Nis2ObligationRecord, Iso42001GapRecord |
| `app/grc/store.py` | **New** — In-memory store with idempotent upsert |
| `app/grc/ai_presets_mapper.py` | **New** — Preset → GRC entity mapper + evidence linking |
| `app/advisor/preset_service.py` | Extended — auto-creates GRC records after successful presets |
| `app/main.py` | Added 3 read-only GRC API endpoints |
| `tests/test_grc_records.py` | **New** — 11 tests |
| `docs/architecture/wave10-assess-once-comply-many.md` | **New** — This document |

## Test Coverage

11 tests covering:
- Preset → GRC record creation (all 3 types) (3 tests)
- Idempotent upsert (same context vs. different) (2 tests)
- Evidence traceability (event + ref_id linking) (2 tests)
- Escalated/errored results → no GRC record (1 test)
- Store filtering (by client_id, control_family) (2 tests)
- Cross-channel record creation (1 test)

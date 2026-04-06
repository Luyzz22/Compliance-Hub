# Wave 9.1 — Advisor Presets Enterprise Readiness

## Overview

Wave 9.1 evolves the advisor presets from "micro-flow prototypes" (Wave 9) into an **enterprise-ready capability** with:

- Clean tenant / Mandant / system separation
- GRC-aligned structured output per preset
- Anti-corruption boundary (`preset_service.py`) as the single integration surface
- Per-preset SLA timeouts
- Integration-friendly response contracts (human + machine + grc)

## Tenant / Mandant / System Separation

### The Three Levels

```
┌──────────────────────────────────────────┐
│ SaaS Tenant (tenant_id)                  │
│  = ComplianceHub-Kunde                   │
│  z.B. "kanzlei-mueller", "acme-gmbh"    │
│                                          │
│  ┌─────────────────────────────────────┐ │
│  │ Client / Mandant (client_id)        │ │
│  │  = Endkunde der Kanzlei / BK       │ │
│  │  z.B. "mandant-12345"              │ │
│  └─────────────────────────────────────┘ │
│                                          │
│  ┌─────────────────────────────────────┐ │
│  │ AI System (system_id)               │ │
│  │  = Konkretes KI-System / Use Case   │ │
│  │  z.B. "HR-AI-Recruiting-01"        │ │
│  └─────────────────────────────────────┘ │
└──────────────────────────────────────────┘
```

| Level | Field | Who sets it | Purpose |
|---|---|---|---|
| Tenant | `context.tenant_id` | Platform / Auth | SaaS isolation, billing, OPA |
| Client | `context.client_id` | Kanzlei-User / DATEV | Per-Mandant reporting, audit trail |
| System | `context.system_id` | User / SAP | EU AI Act Art. 49 register, ISMS asset link |

### Backward Compatibility

Callers can still set `tenant_id` at the top level (without `context`). The preset service merges it: `effective_tenant_id = context.tenant_id || tenant_id`.

### Evidence & Metrics

All three levels are propagated into:
- Agent evidence events (`extra.client_id`, `extra.system_id`)
- Metrics aggregation (`client_id_distribution` in `AdvisorMetricsResponse`)
- Response `ref_ids` and `meta.context`

## GRC Alignment

Each preset derives domain-specific GRC fields from the advisor response:

### EU AI Act Risk Assessment → `AiActRiskGrc`

| Field | Type | Values | GRC Purpose |
|---|---|---|---|
| `risk_category` | string | high_risk, limited_risk, minimal_risk, unclassified | Art. 6 classification |
| `use_case_type` | string | credit_scoring, recruitment, ... | Annex III mapping |
| `high_risk_likelihood` | string | likely, unlikely, unclear, unknown | Decision support |
| `annex_iii_category` | string | Raw Annex III reference | Audit trail |
| `conformity_assessment_required` | bool? | true/false/null | Art. 43 trigger |

### NIS2 Obligations → `Nis2ObligationsGrc`

| Field | Type | Values | GRC Purpose |
|---|---|---|---|
| `nis2_entity_type` | string | essential, important, out_of_scope | Entity classification |
| `obligation_tags` | list[str] | incident_reporting, risk_management, ... | Pflichtenkatalog |
| `reporting_deadlines` | list[str] | 24h_early_warning, 72h_notification, ... | Fristenverwaltung |

### ISO 42001 Gap Check → `Iso42001GapGrc`

| Field | Type | Values | GRC Purpose |
|---|---|---|---|
| `control_families` | list[str] | governance, risk, data, monitoring, ... | Gap-Matrix |
| `gap_severity` | string | critical, major, minor, none, unknown | Priorisierung |
| `iso27001_overlap` | bool? | Whether ISO 27001 partially covers gaps | Migration path |

## Anti-Corruption Boundary: `preset_service.py`

```
External Caller (REST / SAP / DATEV / Temporal)
        │
        ▼
┌─────────────────────────────────┐
│   preset_service.py             │
│   run_eu_ai_act_risk_preset()   │
│   run_nis2_obligations_preset() │
│   run_iso42001_gap_preset()     │
│                                 │
│   • Maps enterprise input       │
│   • Builds advisor query        │
│   • Runs generic advisor agent  │
│   • Derives GRC fields          │
│   • Builds PresetResult         │
│   • Tags evidence               │
└─────────┬───────────────────────┘
          │
          ▼
┌─────────────────────────────────┐
│   service.py (run_advisor)      │
│   • SLA timeout                 │
│   • Idempotency                 │
│   • Error handling              │
│   • Metrics logging             │
└─────────┬───────────────────────┘
          │
          ▼
┌─────────────────────────────────┐
│   AdvisorComplianceAgent        │
│   • RAG + LangGraph             │
│   • Policies & guardrails       │
│   • Sensitive topic detection   │
└─────────────────────────────────┘
```

The `preset_service` is the **only** entry point for preset invocations. REST controllers, Temporal workflows, and future connectors call it — never the raw agent.

## Per-Preset SLA Timeouts

| Preset | Timeout | Rationale |
|---|---|---|
| EU AI Act Risk Assessment | 45s | Complex classification, more RAG context needed |
| NIS2 Obligations | 30s | Shorter obligation-mapping query |
| ISO 42001 Gap Check | 45s | Detailed gap analysis, more synthesis |

## Response Contract (v1)

```json
{
  "human": {
    "answer_de": "Basierend auf Art. 6 und Anhang III ...",
    "is_escalated": false,
    "escalation_reason": "",
    "confidence_level": "high"
  },
  "machine": {
    "tags": ["eu_ai_act", "high_risk", "conformity_assessment"],
    "suggested_next_steps": ["EU AI Act Konformitätsbewertung prüfen"],
    "ref_ids": {
      "flow_type": "eu_ai_act_risk_assessment",
      "client_id": "mandant-12345",
      "system_id": "HR-AI-01"
    },
    "intent": "compliance_query"
  },
  "grc": {
    "risk_category": "high_risk",
    "use_case_type": "recruitment",
    "high_risk_likelihood": "likely",
    "annex_iii_category": "",
    "conformity_assessment_required": true
  },
  "meta": {
    "version": "v1",
    "flow_type": "eu_ai_act_risk_assessment",
    "channel": "datev",
    "request_id": "REQ-001",
    "latency_ms": 1234.5,
    "is_cached": false,
    "context": {
      "tenant_id": "kanzlei-mueller",
      "client_id": "mandant-12345",
      "system_id": "HR-AI-01"
    }
  },
  "error": null,
  "needs_manual_followup": false
}
```

Contract rules:
- Version is `"v1"` — fields are additive, no removals without version bump
- `human.answer_de` is always present (even on errors, contains German error message)
- `grc` fields vary by preset type but are always a dict
- `machine.ref_ids` always contains `flow_type`

## Example Flows

### Flow 1: DATEV-Kanzlei ruft EU AI Act Risk-Preset für Mandant X auf

```
1. Kanzlei-Berater öffnet ComplianceHub DATEV-Plugin
2. Wählt Mandant "12345" (Autohaus Müller GmbH)
3. Fragt: "Ist die geplante KI-Schadensbewertung hochrisiko?"

→ DATEV-Plugin sendet POST /api/v1/advisor/presets/eu-ai-act-risk-assessment
  {
    "context": {
      "tenant_id": "kanzlei-schmidt",
      "client_id": "mandant-12345"
    },
    "use_case_description": "KI-gestützte Kfz-Schadensbewertung ...",
    "channel": "datev",
    "channel_metadata": { "datev_client_number": "12345" },
    "request_id": "DATEV-REQ-2026-03-31-001"
  }

→ ComplianceHub:
  - OPA: advisor_preset_eu_ai_act_risk_assessment (risk=0.6) ✓
  - preset_service → build query → run_advisor() → agent
  - Derive GRC: risk_category="high_risk", likelihood="likely"
  - Format: structured DATEV answer with Kanzlei-Disclaimer

→ Response:
  human.answer_de: "...Hochrisiko...Schlagworte: eu_ai_act, high_risk..."
  grc.risk_category: "high_risk"
  machine.ref_ids: { client_id: "mandant-12345", flow_type: "..." }

→ DATEV-Plugin erstellt Aufgabe für Mandant 12345:
  "EU AI Act Konformitätsbewertung durchführen"
```

### Flow 2: SAP S/4HANA Add-on ruft NIS2-Obligations-Preset für Werk Y auf

```
1. SAP-Compliance-Officer im S/4HANA GRC-Modul
2. Wählt Buchungskreis "WERK-SUED" (Produktionsstandort)
3. Fragt: "NIS2-Pflichten für unseren Energiezulieferer-Status?"

→ SAP BTP calls POST /api/v1/advisor/presets/nis2-obligations
  {
    "context": {
      "tenant_id": "acme-industries",
      "system_id": "WERK-SUED"
    },
    "entity_role": "KRITIS-naher Zulieferer",
    "sector": "Energie",
    "employee_count": "250+",
    "channel": "sap",
    "channel_metadata": { "sap_document_id": "GRC-FINDING-2026-042" },
    "request_id": "SAP-REQ-WERK-SUED-001"
  }

→ ComplianceHub:
  - Derive GRC: nis2_entity_type="essential",
    obligation_tags=["incident_reporting", "risk_management", "supply_chain"]

→ SAP BTP maps response to GRC Finding:
  - finding_type: "NIS2_OBLIGATION"
  - obligations: grc.obligation_tags
  - deadlines: grc.reporting_deadlines
  - linked_entity: "WERK-SUED"
```

## Files Changed

| File | Change |
|---|---|
| `app/advisor/enterprise_context.py` | **New** — EnterpriseContext (tenant_id, client_id, system_id) |
| `app/advisor/preset_models.py` | **New** — Enterprise input schemas, GRC models, PresetResult contract |
| `app/advisor/preset_service.py` | **New** — Anti-corruption boundary with GRC derivation |
| `app/advisor/service.py` | Extended AdvisorRequest with client_id, system_id; evidence propagation |
| `app/advisor/metrics.py` | Added client_id_distribution to aggregation |
| `app/main.py` | Updated preset endpoints to use preset_service + new models |
| `tests/test_advisor_presets_enterprise.py` | **New** — 15 tests |
| `docs/architecture/wave9.1-advisor-presets-enterprise.md` | **New** — This document |

## Test Coverage

15 tests covering:
- Enterprise context propagation (tenant, client, system → evidence, metrics, ref_ids) (4 tests)
- GRC field derivation for all 3 presets (3 tests)
- PresetResult contract shape and version (3 tests)
- Idempotency at preset level (2 tests)
- Channel formatting (DATEV structured, SAP with document ID) (2 tests)
- Flow type in metrics aggregation (1 test)

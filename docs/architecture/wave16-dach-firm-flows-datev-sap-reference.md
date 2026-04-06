# Wave 16 — DACH Kanzlei & SAP Reference Flows

## Overview

Wave 16 moves the ComplianceHub integration layer closer to **DACH tax-compliance reality**
by adding domain-accurate export artefacts for Steuerberater/WP-Kanzleien and
sketching a concrete reference flow for SAP S/4HANA + BTP Event Mesh inbound events.

**Key principle:** integration-light (no real external calls), but domain-accurate.

---

## 1. Mandanten-Compliance-Dossier Export

### Purpose

Steuerkanzleien and WP-Kanzleien need structured compliance documentation per Mandant.
The Mandanten-Compliance-Dossier aggregates all AI governance data for a single
`client_id` into a single export artefact that can serve as:

- **Anlage zur Verfahrensdokumentation** (GoBD context)
- **AI Compliance Report** for board/management review
- **Mandanten-Akte** supplement in DATEV DMS or similar document management

### Dossier Structure (JSON, schema_version: v1)

```
{
  "schema_version": "v1",
  "export_type": "mandant_compliance_dossier",
  "period": "2026Q1",
  "export_version": 1,
  "exported_at": "2026-03-31T10:00:00+00:00",

  "stammdaten": {
    "tenant_id": "kanzlei-mueller",
    "client_id": "mandant-alpha",
    "mandant_kurzname": "Alpha GmbH",
    "branche": "Finanzdienstleistungen"
  },

  "ai_system_inventar": [
    {
      "system_id": "chatbot-v1",
      "name": "Kundenservice-Chatbot",
      "beschreibung": "LLM-basierter Chatbot",
      "business_owner": "Max Müller",
      "lebenszyklus_stufe": "production",
      "ki_act_klassifikation": "high_risk_candidate",
      "bereitschaftsgrad": "partially_covered",
      "nis2_relevant": false,
      "iso42001_im_scope": false
    }
  ],
  "ai_systeme_gesamt": 1,

  "grc_sicht": {
    "ai_risk_assessments": {
      "gesamt": 2,
      "status_verteilung": {"open": 1, "accepted": 1}
    },
    "nis2_pflichten": {
      "gesamt": 1,
      "status_verteilung": {"identified": 1}
    },
    "iso42001_gaps": {
      "gesamt": 3,
      "nach_control_family": {
        "A.6_Planning": {"open": 1},
        "A.7_Support": {"remediation_planned": 1}
      }
    }
  },

  "compliance_flags": {
    "deployment_check_verwendet": true,
    "board_reports_aktuell": true
  }
}
```

### DATEV Integration Perspective

The dossier format is designed to be importable into DATEV-adjacent workflows:

| Aspect | Design Decision |
|---|---|
| **Field labels** | German where Mandant-facing (`lebenszyklus_stufe`, `ki_act_klassifikation`), English technical IDs for system interop |
| **Naming convention** | `ai_compliance_mandant_export_{tenant}_{client}_{period}_{version}.json` |
| **Schema versioning** | `schema_version: "v1"` — changes only via versioned contract update |
| **Period tracking** | `period` + `export_version` for GoBD-Nachvollziehbarkeit |

### Payload Type & Integration Job

- `IntegrationPayloadType.mandant_compliance_dossier`
- Classified as **heavy** job (aggregates all GRC data for a Mandant)
- Target: `datev_export` connector
- Idempotency key: `datev_export:MandantComplianceDossier:{tenant}:{client}:{period}:v{version}`

---

## 2. Period & Versioning Model

All Kanzlei-Exports track three version dimensions:

| Field | Purpose | Example |
|---|---|---|
| `period` | Reporting period | `2026Q1`, `2026-01-01..2026-03-31` |
| `export_version` | Increment when rebuilt for same period | `1`, `2`, `3` |
| `schema_version` | Payload contract version | `v1` |

These fields are persisted on:
- `IntegrationJob` (period, export_version, schema_version)
- Export artifact metadata (in the artifact store)
- Evidence events (for audit trail)

This ensures Kanzleien can clearly identify and differentiate exports
(GoBD-Nachvollziehbarkeit).

---

## 3. Trigger Paths

### Manual API Trigger

```
POST /api/internal/integrations/mandant-export
{
  "client_id": "mandant-alpha",
  "period": "2026Q1",
  "export_version": 1,
  "mandant_kurzname": "Alpha GmbH",
  "branche": "Finanzdienstleistungen"
}
```

Protected by OPA `manage_integrations` permission.

### Board Report Auto-Trigger (Feature-Flagged)

When `ENABLE_DOSSIER_ON_BOARD_REPORT` is set to `True`:
- After successful `run_client_board_report()` completion
- Automatically enqueues a `mandant_compliance_dossier` IntegrationJob
- Same tenant/client/period as the board report

**Default: disabled.** Must be explicitly opted-in per deployment.
The `mandant_compliance_dossier` payload type must also be in
`ENABLED_PAYLOAD_TYPES` for the job to be created.

---

## 4. SAP S/4HANA + BTP Reference Flow

### Architecture

```
┌──────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  SAP S/4HANA     │     │  SAP BTP        │     │  ComplianceHub   │
│                  │     │  Event Mesh +   │     │                  │
│  AI use case     │────▶│  Integration    │────▶│  POST /api/v1/   │
│  created/updated │     │  Suite          │     │  integrations/   │
│                  │     │                 │     │  sap/ai-system-  │
│  CloudEvents     │     │  Transform +   │     │  event           │
│  publish         │     │  Route          │     │                  │
└──────────────────┘     └─────────────────┘     └──────────────────┘
```

### Event Types

| SAP Event Type | Trigger |
|---|---|
| `sap.s4.ai.system.created` | New AI system registered in S/4 |
| `sap.s4.ai.system.updated` | AI system metadata changed |
| `sap.s4.ai.deployment.requested` | AI scoring/model deployment requested |

### Inbound Endpoint

```
POST /api/v1/integrations/sap/ai-system-event
Content-Type: application/json

{
  "specversion": "1.0",
  "type": "sap.s4.ai.system.created",
  "source": "sap.s4hana.finance.prod",
  "id": "evt-abc123",
  "time": "2026-03-31T10:00:00Z",
  "tenantid": "kanzlei-mueller",
  "clientid": "mandant-alpha",
  "systemid": "sap-scoring-01",
  "traceid": "trace-xyz",
  "data": {
    "system_id": "sap-scoring-01",
    "name": "SAP Kredit-Scoring",
    "description": "ML scoring from S/4HANA",
    "business_owner": "Herr Finanz"
  }
}
```

### Processing

1. **Validate** CloudEvents envelope (mandatory fields, specversion, event type)
2. **Map** to AiSystem: `get_or_create_ai_system()` with data from envelope
3. **Update** enrichable fields (name, description, owner) — never overwrites existing data
4. **Emit** evidence event (`sap_btp_ai_system_event`) with full SAP traceability
5. **Return** 202 Accepted with created/updated system reference

### Validation Rules

- `specversion` must be `"1.0"`
- `type` must be one of the recognised SAP event types
- `data.system_id` is required
- `tenantid` is required (falls back to auth context)

---

## 5. Evidence & Audit

### Kanzlei-Export Evidence

```json
{
  "event_type": "mandant_compliance_export",
  "tenant_id": "kanzlei-mueller",
  "client_id": "mandant-alpha",
  "period": "2026Q1",
  "export_version": 1,
  "schema_version": "v1",
  "artifact_name": "ai_compliance_mandant_export_kanzlei-mueller_mandant-alpha_2026Q1_v1.json",
  "job_id": "INTJOB-...",
  "trace_id": "..."
}
```

### SAP Inbound Evidence

```json
{
  "event_type": "sap_btp_ai_system_event",
  "tenant_id": "kanzlei-mueller",
  "system_id": "sap-scoring-01",
  "ai_system_id": "SYS-...",
  "sap_event_type": "sap.s4.ai.system.created",
  "sap_source": "sap.s4hana.finance.prod",
  "envelope_id": "evt-abc123",
  "trace_id": "trace-xyz"
}
```

---

## 6. Anti-Corruption & Future Wiring

### What exists now

- Stable dossier JSON contract (schema_version v1)
- DATEV-style naming and artifact store
- CloudEvents-compliant SAP inbound validation
- AiSystem auto-creation from SAP events
- Full evidence trail for both directions

### What does NOT exist

- **No real DATEV API integration** — artifacts are stored in-memory
- **No real SAP BTP Event Mesh subscription** — the endpoint is ready but not wired
- **No DATEV DMS upload** — artifacts are not pushed anywhere
- **No S/4HANA system** — event types are based on reasonable SAP patterns

### Design for future wiring

The contracts, envelopes, and artifacts are intentionally designed so that:

1. **DATEV connector** can be extended to push artifacts to DATEV DMS/API
   without changing the payload shape
2. **SAP BTP Integration Suite** can route events to the inbound endpoint
   without any ComplianceHub-side changes
3. **Schema evolution** is handled via `schema_version` — consumers can
   check compatibility before processing

---

## Files

| File | Purpose |
|---|---|
| `app/integrations/mandant_dossier.py` | Dossier builder + evidence logging |
| `app/integrations/sap_inbound.py` | SAP CloudEvents validation + AiSystem mapping |
| `app/integrations/models.py` | `mandant_compliance_dossier` type, period/version fields |
| `app/integrations/outbox.py` | `enqueue_mandant_dossier()` helper |
| `app/integrations/connectors.py` | DATEV connector dossier dispatch path |
| `app/integrations/mappers.py` | Pass-through mapper for dossier type |
| `app/integrations/store.py` | `ENABLE_DOSSIER_ON_BOARD_REPORT` flag |
| `app/grc/client_board_report_service.py` | Board report → dossier auto-enqueue |
| `app/main.py` | Mandant-export API + SAP inbound endpoint |
| `tests/test_wave16_dach_flows.py` | 30 tests covering all Wave 16 features |

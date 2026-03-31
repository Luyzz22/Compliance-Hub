# Wave 13 — Client/Mandant-Level AI Compliance Board Reports

## Overview

Wave 13 introduces **Mandant-level AI Compliance Board Reports** for
Steuerberater-/WP-Kanzleien.  These reports aggregate AiSystem inventory
and GRC artefacts per Mandant (`client_id`) into a structured, advisory
summary — ready for recurring compliance reporting.

```
Kanzlei (tenant)
  └── Mandant A (client_id)
        ├── AiSystem: CREDIT-AI-01 (high_risk_candidate, pilot)
        │     ├── AiRiskAssessment: high_risk
        │     ├── Nis2ObligationRecord: in_progress
        │     └── Iso42001GapRecord: governance/monitoring open
        ├── AiSystem: CHATBOT-02 (limited, production)
        │     └── AiRiskAssessment: limited_risk
        └── → Board Report (Markdown + highlights)
```

## Tenant-Level vs. Client-Level Reports

| Aspect           | Tenant-Level (Wave 8+)              | Client-Level (Wave 13)                    |
|------------------|--------------------------------------|-------------------------------------------|
| Scope            | All AI systems in tenant             | AI systems for one Mandant                |
| Use case         | Internal governance overview         | Kanzlei → Mandant advisory report         |
| Triggered by     | Compliance Officer                   | Kanzlei-Berater for specific Mandant      |
| EnterpriseContext| `tenant_id` only                     | `tenant_id` + `client_id`                 |
| Temporal support | Full workflow                        | Workflow-ready, sync fallback for MVP     |

## Workflow

### ClientBoardReportWorkflow

**Input:**
- `tenant_id` — Kanzlei as SaaS tenant
- `client_id` — Mandant
- `reporting_period` — e.g. "Q1 2026"
- `system_filter` — optional subset of system_ids
- `language` — default "de"

**Steps:**
1. **Aggregate** — Load AiSystems + GRC records for this Mandant
2. **Synthesise** — Generate Markdown report (LLM or deterministic fallback)
3. **Persist** — Store report in-memory (DB later)
4. **Evidence** — Log `client_board_report_generated` event

**Output:**
- `report_id`, `workflow_id`, `systems_included`, `status`

## Data Aggregation

Per AiSystem for the Mandant:
- Classification, lifecycle stage, readiness level
- Count of risk assessments
- Open/in-progress NIS2 obligations
- Open/remediation-planned ISO 42001 gaps
- Framework coverage hints

Aggregated totals:
- Number of high-risk systems
- Total open gaps
- Total open obligations

All operations are **read-only** — no GRC record status changes.

## Report Synthesis

### Sections
1. **AI Systemübersicht Mandant X** — list with classification/lifecycle/readiness
2. **EU AI Act Risikoeinschätzungen & offene Punkte** — high-risk candidates, conformity
3. **NIS2-relevante Verpflichtungen** — open obligations, deadlines
4. **ISO 42001/27001 Governance & Gap-Status** — open gaps by control family
5. **Empfehlungen** (LLM path only)
6. **Disclaimer** — "keine Rechtsberatung, nur unverbindliche Einordnung"

### Two Paths
- **LLM path**: Guardrailed LLM call with `LlmCallContext(action="generate_client_board_report")`
- **Deterministic fallback**: Template-based Markdown (no LLM needed, always available)

## API Endpoints

### `POST /api/v1/clients/{client_id}/ai-board-report/workflows/start`
Start a Mandant board report.  OPA: `start_client_board_report`.
Returns `202 Accepted` with workflow_id, report_id, status.

### `GET /api/v1/clients/{client_id}/ai-board-report/workflows/{workflow_id}`
Check workflow status and retrieve report when complete.
OPA: `view_client_board_report`.

### `GET /api/v1/clients/{client_id}/ai-board-reports`
List past reports for a Mandant.
OPA: `view_client_board_report`.

## Evidence & Metrics

Each completed report emits:
```json
{
  "event_type": "client_board_report_generated",
  "tenant_id": "kanzlei-mueller",
  "client_id": "mandant-42",
  "report_id": "CBR-abc123",
  "reporting_period": "Q1 2026",
  "systems_included": 3,
  "system_ids": ["CREDIT-AI-01", "CHATBOT-02", "HR-SCREEN-03"]
}
```

Enables:
- Kanzlei-internes Reporting (wie viele Mandanten-Reports pro Quartal?)
- AI-Act-Audit trail (wann wurde welcher Mandant zuletzt bewertet?)

## DATEV Integration Outlook

These reports are designed for future DATEV-nahe integration:

1. **DATEV DMS Export**: Report Markdown → PDF → upload to DATEV Dokumentenmanagement per Mandantennummer
2. **DATEV Schnittstelle**: Structured `snapshot` payload → DATEV comfort letter / Prüfungsdokumentation
3. **DATEV Online**: Mandant-portal view showing latest AI compliance status

The `client_id` maps directly to DATEV Mandantennummer, making the
data model ready for these integrations.

## Example: Kanzlei Mueller, Mandant Acme GmbH

1. Kanzlei-Berater starts report: `POST .../clients/mandant-42/ai-board-report/workflows/start?reporting_period=Q1 2026`
2. System aggregates: 2 AiSystems, 1 high_risk_candidate, 1 open ISO gap
3. Report generated:

```markdown
# AI Compliance Board-Report — Mandant mandant-42
**Berichtszeitraum:** Q1 2026

## AI Systemübersicht
- **2** AI-System(e) erfasst
- **1** als high_risk_candidate eingestuft

### KI-Kreditprüfung (CREDIT-AI-01)
- Klassifizierung: high_risk_candidate
- Lifecycle: pilot
- Readiness: insufficient_evidence
- Offene ISO 42001 Gaps: 1

### Mandanten-Chatbot (CHATBOT-02)
- Klassifizierung: limited
- Lifecycle: production
...

*Hinweis: Dieser Report dient ausschließlich der unverbindlichen
Einordnung und stellt keine Rechtsberatung dar.*
```

4. Evidence event logged with all system_ids and report_id
5. Report available via list/status API for future reference

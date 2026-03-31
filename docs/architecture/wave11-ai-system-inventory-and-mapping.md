# Wave 11 — AI System Inventory & Cross-Framework Mapping

## Overview

Wave 11 introduces the **AiSystem** entity — a lightweight inventory record
that turns a `system_id` (+ tenant/client context) into a coherent AI system
view.  Every GRC record (risk assessment, NIS2 obligation, ISO 42001 gap)
that references a `system_id` is automatically linked to the corresponding
AiSystem, enabling the **"assess once, comply many" principle at system level**.

```
AiSystem  ──┐
             ├── AiRiskAssessment(s)    → EU AI Act articles
             ├── Nis2ObligationRecord(s) → NIS2 Art. 21 ff.
             └── Iso42001GapRecord(s)    → ISO 42001 Annex A / ISO 27001
```

## AiSystem Entity

| Field                   | Type   | Description                                              |
|-------------------------|--------|----------------------------------------------------------|
| `id`                    | str    | Internal ID (`SYS-...`)                                   |
| `system_id`             | str    | External reference (e.g. SAP asset ID)                    |
| `tenant_id`             | str    | ComplianceHub SaaS tenant                                |
| `client_id`             | str    | Optional Mandant / Buchungskreis                         |
| `name`                  | str    | Human-readable name                                      |
| `description`           | str    | Free-text description                                    |
| `business_owner`        | str    | Business owner contact                                   |
| `technical_owner`       | str    | Technical owner contact                                  |
| `ai_act_classification` | enum   | `not_in_scope` / `minimal` / `limited` / `high_risk_candidate` / `high_risk` |
| `nis2_relevant`         | bool   | Whether NIS2 obligations apply                           |
| `iso42001_in_scope`     | bool   | Whether ISO 42001 scope applies                          |
| `auto_created`          | bool   | True if auto-created as stub                             |

### Auto-Creation Behaviour

When a GRC record is created with a `system_id` that has no matching
AiSystem, the mapper **auto-creates a minimal stub** with:
- `name` = `system_id`
- `auto_created` = `True`
- All other fields at defaults

This ensures every GRC record is navigable from the system view without
requiring upfront manual registration.

### Classification Guardrails

- A risk assessment flagging `high_risk` sets classification to
  **`high_risk_candidate`**, never directly to `high_risk`.
- Upgrading to `high_risk` is a **human decision** — the platform provides
  a hook for a future confirmation step but does not implement it in Wave 11.
- NIS2 and ISO 42001 presets set the corresponding `nis2_relevant` /
  `iso42001_in_scope` flags automatically.

## Cross-Framework Mapping

The mapping module (`app/grc/framework_mapping.py`) provides declarative
lookups from GRC record fields to regulatory articles and control IDs:

| Source                  | Target Framework        | Example Mapping                              |
|-------------------------|-------------------------|----------------------------------------------|
| `risk_category=high_risk` | EU AI Act             | Art. 6, 8–15, 43                              |
| `obligation_tags=[incident_reporting]` | NIS2     | Art. 23(1), Art. 23(4)                        |
| `control_families=[governance]` | ISO 42001         | A.2.2, A.2.3, A.2.4                          |
| `control_families=[governance]` | ISO 27001 overlay | A.5.1, A.5.2, A.5.3                          |

The mapping is **structuring, not certifying** — it shows which
articles/controls are *touched* by existing evidence, not that compliance
is achieved.

### Aggregated Coverage

`aggregate_framework_coverage()` merges all GRC records for a system into a
single `{framework: [articles]}` dict, used by the overview API.

## API Endpoints

### `GET /api/v1/ai-systems`

List AI systems.  Filters: `tenant_id`, `client_id`, `classification`,
`nis2_relevant`.

### `GET /api/v1/ai-systems/{system_id}/overview`

Returns:
```json
{
  "system": { ... AiSystem fields ... },
  "risk_assessments": [ ... ],
  "nis2_obligations": [ ... ],
  "iso42001_gaps": [ ... ],
  "framework_coverage": {
    "eu_ai_act": ["Art. 6", "Art. 9", "Art. 10", ...],
    "nis2": ["Art. 21(1)", "Art. 23(1)", ...],
    "iso42001": ["A.2.2", "A.4.2", ...],
    "iso27001": ["A.5.1", ...]
  }
}
```

Both endpoints are secured via OPA (`view_ai_systems`).

## Evidence Traceability

Evidence events now include `ai_system_id` when a system is linked:

```
AiSystem
  └── grc_record_created (event)
        ├── ai_system_id: SYS-abc123
        ├── grc_record_id: RISK-def456
        ├── flow_type: eu_ai_act_risk_assessment
        └── trace_id → advisor_agent event → RAG query
```

An auditor can navigate:  
**AiSystem → risk assessments → advisor events → RAG/LLM activity**

## Example: SAP High-Risk Scoring Model

1. **System registered**: `system_id="SAP-CREDIT-AI-01"`, `tenant_id="acme-gmbh"`
2. **Risk preset run**: Advisor identifies high-risk → `AiRiskAssessment` created
3. **AiSystem auto-created** as stub with `ai_act_classification=high_risk_candidate`
4. **NIS2 preset run**: Obligation record created, `nis2_relevant=True` set on AiSystem
5. **ISO 42001 preset run**: Gap record created, `iso42001_in_scope=True` set
6. **Overview API** returns all 3 record types + framework coverage:
   - EU AI Act: Art. 6, 8–15, 43
   - NIS2: Art. 21(1), Art. 23(1)
   - ISO 42001: A.2.2, A.3.2, A.4.2 + ISO 27001 overlay
7. **Human confirms** high-risk classification (future wave)

## Future Integration Points

- **SAP GRC**: Push AiSystem + classification to SAP risk objects
- **DATEV DMS**: Link Mandant-scoped AiSystems to DATEV document bundles
- **Human classification step**: Confirm/reject `high_risk_candidate` → `high_risk`
- **Backoffice UI**: Full CRUD for AiSystem metadata, owner assignment
- **Temporal workflows**: Scheduled re-assessment of system classification

# Wave 15.1 — Enterprise Integrations: BTP & DATEV Hardening

## Summary

Wave 15.1 hardens the integration layer for real enterprise readiness:

- **RLS-style tenant isolation** on all IntegrationJob operations.
- **SAP BTP Event Mesh–style envelope** (CloudEvents-aligned) as a first-class
  contract for BTP consumers.
- **DATEV export artifacts** with naming conventions, CSV/JSON rendering, and
  a dedicated artifact store.
- **Dispatcher enhancements**: throttling, exponential backoff, job weight
  classification, priority ordering with DATEV boost.
- **Integration-specific OPA roles** (`integration_admin`, `it_ops`,
  `view_integration_jobs`, `manage_integrations`).
- **Connector-specific refs** (artifact name, envelope ID) on job records
  and evidence events for end-to-end traceability.

No external API calls are made.  All connectors remain stubbed.

---

## RLS-Hardened IntegrationJob Storage

### Tenant Isolation Rules

All `IntegrationJob` read/write operations enforce tenant isolation:

| Operation        | Tenant enforcement                              |
|------------------|-------------------------------------------------|
| `enqueue_job`    | Requires non-empty `tenant_id` (ValueError if missing) |
| `get_job`        | Returns `None` if caller's `tenant_id` doesn't match   |
| `list_jobs`      | Returns empty list if no `tenant_id` and not `_internal` |
| `update_status`  | Returns `None` for tenant mismatch                      |
| `mark_for_retry` | Returns `None` for tenant mismatch                      |

### Internal Service Bypass

Infrastructure operations (metrics, ops UI, dispatcher) pass
`_internal=True` to bypass tenant filtering.  This maps to:

- **PostgreSQL**: a service-role RLS bypass policy.
- **Application**: explicit `_internal=True` parameter on store functions.

### Indexed Fields

For future PostgreSQL migration, the store is designed around:

```sql
CREATE INDEX idx_integration_jobs_tenant ON integration_jobs (tenant_id);
CREATE INDEX idx_integration_jobs_tenant_client ON integration_jobs (tenant_id, client_id);
CREATE INDEX idx_integration_jobs_status ON integration_jobs (status);
```

---

## Integration Roles & OPA Policies

### Defined Actions

| OPA Action               | Who                        | Purpose                        |
|--------------------------|----------------------------|--------------------------------|
| `manage_integrations`    | `integration_admin`, `it_ops`, `platform_admin` | Create, retry, dispatch jobs |
| `view_integration_jobs`  | Above + `tenant_admin`     | Read-only job listing/detail   |
| `trigger_exports`        | `tenant_admin` (future)    | Tenant-initiated DATEV exports |

### SAML / Azure AD Role Mapping (Document-only)

For enterprise SSO setups, the following mapping is recommended:

| SAML/AAD Group            | OPA Role             | Description                      |
|---------------------------|----------------------|----------------------------------|
| `ComplianceHub-IntAdmin`  | `integration_admin`  | Full integration management      |
| `ComplianceHub-ITOps`     | `it_ops`             | Infrastructure monitoring        |
| `ComplianceHub-TenantAdmin` | `tenant_admin`     | Tenant-scoped administration     |
| `ComplianceHub-Viewer`    | `viewer`             | Read-only across all modules     |

Actual IdP wiring is a future wave.  The role names are registered in
`ALLOWED_OPA_ROLES` and ready for claim-based mapping.

---

## SAP BTP Event Mesh Envelope

### Contract (v1)

The SAP connector builds a CloudEvents-aligned JSON envelope:

```json
{
  "specversion": "1.0",
  "type": "compliancehub.grc.ai_risk_assessment",
  "source": "compliancehub.ai-governance",
  "id": "evt-abc123...",
  "time": "2025-12-01T10:00:00+00:00",
  "tenantid": "acme-corp",
  "clientid": "mandant-42",
  "systemid": "scoring-ai",
  "traceid": "trace-001",
  "jobid": "INTJOB-xyz789",
  "datacontenttype": "application/json",
  "payload_type": "ai_risk_assessment",
  "payload_version": "v1",
  "data": {
    "schema_version": "v1",
    "record_type": "ai_risk_assessment",
    "risk_category": "high",
    "...": "..."
  }
}
```

### Design Principles

- **CloudEvents alignment**: `specversion`, `type`, `source`, `id`, `time`
  follow the CloudEvents spec for SAP Event Mesh compatibility.
- **Stable IDs**: `id` (envelope), `tenantid`, `systemid`, `traceid`, `jobid`
  are all traceable back to internal entities.
- **Versioned**: `specversion` + `payload_version` enable contract evolution.
- **No PII**: no raw prompts, no personal data beyond business identifiers.

### BTP Consumer Pattern

A BTP-side consumer subscribes to topics matching
`compliancehub.grc.*` and processes events by `payload_type`.
The `tenantid` header enables multi-tenant routing on the BTP side.

---

## DATEV Export Artifacts

### Artifact Naming Convention

```
ai_compliance_mandant_export_{tenant}_{client}_{period}_{version}.{ext}
```

Example: `ai_compliance_mandant_export_acme_mandant-42_2025-Q4_v1.json`

### JSON Export Format

```json
{
  "schema_version": "v1",
  "export_type": "datev_mandant_export",
  "exported_at": "2025-12-01T10:00:00+00:00",
  "records": [
    {
      "record_type": "Risikobewertung_KI",
      "source_id": "RISK-abc123",
      "client_id": "mandant-42",
      "risikokategorie": "high",
      "...": "..."
    }
  ]
}
```

### CSV Export Format

German column headers for Kanzlei compatibility:

| Column                  | Description                           |
|-------------------------|---------------------------------------|
| `Datensatz_Typ`         | Record type (German label)            |
| `Datensatz_ID`          | Source entity ID                      |
| `Mandant_ID`            | Client/Mandant ID                     |
| `System_ID`             | AI system reference                   |
| `Status`                | Current record status                 |
| `Risikokategorie`       | Risk category (AI Act)                |
| `NIS2_Entitaetstyp`     | NIS2 entity type                      |
| `ISO42001_Schweregrad`   | ISO 42001 gap severity               |
| `Bereitschaftsgrad`     | Readiness level                       |
| `Lebenszyklus_Stufe`    | Lifecycle stage                       |
| `Erstellt_Am`           | Creation timestamp                    |
| `Schema_Version`        | Payload schema version                |

### Artifact Store

Artifacts are persisted in an in-memory store (future: S3/database) with:
- Tenant-isolated retrieval (tenant mismatch returns `None`).
- Metadata: `name`, `tenant_id`, `client_id`, `job_id`, `format`, `size_bytes`,
  `stored_at`.
- Linked to `IntegrationJob` via `connector_artifact_name`.

### Kanzlei Consumption Pattern

1. Operator triggers a DATEV export via the internal API.
2. Dispatcher maps GRC records to DATEV payloads and writes an artifact.
3. Kanzlei downloads the artifact manually (future: DATEV add-on polls).
4. Artifact name and job ID provide full audit trail.

---

## Dispatcher Enhancements

### Configurable Settings

```python
@dataclass
class DispatcherSettings:
    max_concurrent_per_target: int = 5
    backoff_base_seconds: float = 1.0
    backoff_max_seconds: float = 30.0
    datev_priority_boost: int = 0
    heavy_job_limit: int = 2
    enable_backoff: bool = True
```

### Throttling

- `max_concurrent_per_target`: limits parallel dispatches per connector.
- `heavy_job_limit`: limits concurrent heavy jobs (board reports, readiness
  snapshots).

### Exponential Backoff

For retried jobs: `delay = base * 2^(attempt-1)`, capped at `backoff_max`.
Disabled in test mode (`enable_backoff=False`).

### Priority Ordering

Jobs are dispatched in priority order (highest first).
`datev_priority_boost` adds priority points to DATEV jobs, useful during
Kanzlei closing periods (Jahresabschluss).

### Job Weight Classification

| Weight | Payload Types                                    |
|--------|--------------------------------------------------|
| light  | `ai_risk_assessment`, `nis2_obligation`, `iso42001_gap` |
| heavy  | `board_report_summary`, `ai_system_readiness_snapshot`  |

Weight is set automatically on enqueue.

---

## Observability & Evidence

### Evidence Events

Every job state transition emits a structured event including:

| Field             | Description                                |
|-------------------|--------------------------------------------|
| `event_type`      | `integration_job_created`, `_dispatched`, `_delivered`, `_failed`, `_dead_letter`, `_retried` |
| `job_id`          | IntegrationJob ID                          |
| `tenant_id`       | Tenant scope                               |
| `client_id`       | Client/Mandant scope                       |
| `system_id`       | AI system reference                        |
| `target`          | Connector target                           |
| `payload_type`    | Payload type                               |
| `weight`          | Job weight (light/heavy)                   |
| `priority`        | Job priority                               |
| `artifact_name`   | DATEV artifact name (if applicable)        |
| `envelope_id`     | SAP BTP envelope ID (if applicable)        |
| `trace_id`        | Distributed tracing correlation            |

### Connector-Specific Refs on Jobs

After dispatch, jobs carry:
- `connector_artifact_name`: for DATEV exports.
- `connector_envelope_id`: for SAP BTP envelopes.

These enable the ops UI to show target-specific detail without
re-querying the connector sink.

---

## Enterprise Anti-Corruption Architecture

```
┌────────────────────────┐
│  GRC / AiSystem Domain │  ← internal, clean, no external deps
└────────┬───────────────┘
         │ enqueue_for_entity()
┌────────▼───────────────┐
│  Integration Outbox    │  ← IntegrationJob + feature flags
└────────┬───────────────┘
         │ dispatch_pending()
┌────────▼───────────────┐
│  Payload Mappers       │  ← DATEV / SAP / generic translation
└────────┬───────────────┘
         │
    ┌────▼────┐  ┌────▼────┐  ┌────▼─────┐
    │  DATEV  │  │ SAP BTP │  │ Generic  │
    │Connector│  │Connector│  │Connector │
    └─────────┘  └─────────┘  └──────────┘
         │             │              │
    [artifact]   [envelope]     [payload]
    (mock sink)  (mock sink)   (mock sink)
```

The core GRC domain never depends on external schemas.
Connectors are pure translation layers.

---

## Files

| File | Purpose |
|------|---------|
| `app/integrations/models.py` | Enhanced: `JobWeight`, `priority`, `connector_artifact_name`, `connector_envelope_id` |
| `app/integrations/store.py` | RLS-hardened with tenant isolation and `_internal` bypass |
| `app/integrations/sap_envelope.py` | **New**: CloudEvents SAP BTP envelope builder |
| `app/integrations/datev_export.py` | **New**: DATEV artifact builder (CSV/JSON), naming, artifact store |
| `app/integrations/connectors.py` | Enhanced: SAP builds envelopes, DATEV writes artifacts |
| `app/integrations/dispatcher.py` | Enhanced: throttling, backoff, priority, weight |
| `app/integrations/outbox.py` | Unchanged (weight set via store) |
| `app/integrations/mappers.py` | Unchanged |
| `app/policy/role_resolution.py` | Added `integration_admin`, `it_ops`, `platform_admin` roles |
| `app/main.py` | Updated: `view_integration_jobs` for read, `manage_integrations` for write |
| `tests/test_integration_hardened.py` | **New**: 30 tests for RLS, envelopes, artifacts, throttling |
| `tests/test_integration_jobs.py` | Updated for RLS-aware `list_jobs` |

---

## Future Wiring

When ready to connect real external systems:

1. **SAP BTP**: implement `SapBtpConnector.dispatch` to POST the envelope
   to SAP Event Mesh via OAuth2 client credentials.
2. **DATEV**: implement `DatevExportConnector.dispatch` to upload artifacts
   via DATEV DMS API or partner connector.
3. **IdP**: wire SAML/Azure AD groups to `ALLOWED_OPA_ROLES` via the
   existing `resolve_opa_role_for_policy` mechanism.
4. **PostgreSQL RLS**: create `integration_jobs` table with `tenant_id`
   RLS policies; the store API is already aligned.

# Wave 15 — Enterprise Connectors Skeleton

## Summary

Wave 15 introduces the **integration foundation** for DATEV/SAP/BTP-style
outbound synchronisation.  It provides:

- Stable connector contracts and payload versioning.
- An outbox/event model for reliable delivery.
- Mapping layers that translate internal GRC / AiSystem artefacts into
  DATEV-friendly and SAP/BTP-friendly payloads.
- Manual trigger, retry, and dead-letter semantics.
- Full tenant / client / system traceability through evidence events.

**No external API calls are made in this wave.**  All connectors write to
deterministic mock sinks, ensuring the integration layer can be tested and
audited without external dependencies.

---

## Why Outbox + Connector Abstraction

Enterprise customers (Industrie-Mittelstand, Steuerberater/WP-Kanzleien)
require predictable, auditable data flows to their existing systems.
Directly coupling the GRC domain to DATEV or SAP APIs would create tight
bindings and fragile failure modes.

The **outbox pattern** decouples intent from delivery:

1. An internal event (e.g. GRC record created) enqueues an
   `IntegrationJob` with payload type, target, and idempotency key.
2. A dispatcher picks pending jobs, maps payloads via the translation
   layer, and calls the target connector.
3. Failures are retried up to `MAX_DISPATCH_ATTEMPTS` (3) before moving
   to `dead_letter`.

This ensures:
- **At-least-once delivery** semantics (idempotency keys prevent
  duplicate processing on the source side).
- **Clean anti-corruption boundary**: the internal GRC/advisor domain
  remains decoupled from external data formats.
- **Auditability**: every state transition emits a structured evidence
  event with `tenant_id`, `client_id`, `system_id`, and `trace_id`.

---

## DATEV vs SAP/BTP Payload Families

### DATEV-Friendly Export

- Compact, compliance-dossier oriented.
- Strong Mandant (client) context: `client_id` is first-class.
- German field names where useful (e.g. `risikokategorie`,
  `konformitaetsbewertung_erforderlich`, `Mandanten_Board_Bericht`).
- Designed for import into DATEV DMS or similar document/dossier systems.

### SAP/BTP-Friendly Payload

- Structured JSON envelope with stable, machine-consumable IDs.
- English field names, lifecycle/readiness/GRC fields exposed directly.
- Designed for event-based integration (SAP BTP Event Mesh, standard
  REST APIs).

Both families include:
- `schema_version: "v1"` for explicit contract versioning.
- Tenant / client / system references.
- Source record IDs and timestamps.
- Machine-readable tags.
- **No raw prompts, no PII beyond business-safe identifiers.**

---

## Domain Model

### IntegrationTarget

| Value                  | Description                          |
|------------------------|--------------------------------------|
| `datev_export`         | DATEV-style dossier/JSON export      |
| `sap_btp`              | SAP BTP event/API envelope           |
| `generic_partner_api`  | Generic partner API (fallback)       |

### IntegrationPayloadType

| Value                           | Source Entity              |
|---------------------------------|----------------------------|
| `ai_risk_assessment`            | `AiRiskAssessment`         |
| `nis2_obligation`               | `Nis2ObligationRecord`     |
| `iso42001_gap`                  | `Iso42001GapRecord`        |
| `board_report_summary`          | `ClientBoardReport`        |
| `ai_system_readiness_snapshot`  | `AiSystem`                 |

### IntegrationJobStatus (Lifecycle)

```
pending → dispatched → delivered
                    ↘ failed → (retry) → pending
                              ↘ dead_letter → (retry) → pending
```

Jobs move to `dead_letter` after `MAX_DISPATCH_ATTEMPTS` (3) consecutive
failures.  Both `failed` and `dead_letter` jobs can be manually retried
via the internal API.

### IntegrationJob Fields

| Field                | Description                                      |
|----------------------|--------------------------------------------------|
| `job_id`             | Unique ID (`INTJOB-...`)                         |
| `tenant_id`          | Owning tenant                                    |
| `client_id`          | Optional Mandant/client                          |
| `system_id`          | Optional AI system reference                     |
| `target`             | `IntegrationTarget` enum                         |
| `payload_type`       | `IntegrationPayloadType` enum                    |
| `payload_version`    | Contract version (default `v1`)                  |
| `payload`            | Mapped outbound payload (dict)                   |
| `status`             | Current `IntegrationJobStatus`                   |
| `idempotency_key`    | `{target}:{entity_type}:{entity_id}`             |
| `source_entity_type` | Internal entity class name                       |
| `source_entity_id`   | Internal entity ID                               |
| `trace_id`           | Correlation ID for distributed tracing           |
| `created_at`         | ISO 8601 creation timestamp                      |
| `last_attempt_at`    | ISO 8601 last dispatch attempt                   |
| `attempt_count`      | Number of dispatch attempts                      |
| `last_dispatch_result` | Human-readable dispatch outcome                |

---

## Feature Flags / Opt-In

Outbox job creation is controlled by `ENABLED_PAYLOAD_TYPES`:

```python
from app.integrations.store import configure_enabled_types

# Only create outbox jobs for risk assessments and NIS2 obligations
configure_enabled_types({"ai_risk_assessment", "nis2_obligation"})
```

If the set is empty, **all** payload types are allowed (default for
development/testing).  This allows per-tenant opt-in without code
changes.

---

## Connector Interface

```python
class BaseConnector(ABC):
    @abstractmethod
    def dispatch(self, job: IntegrationJob, payload: dict) -> DispatchResult:
        ...
```

Stub implementations:
- `DatevExportConnector` — writes JSON to mock sink.
- `SapBtpConnector` — writes structured envelope to mock sink.
- `GenericPartnerApiConnector` — logs full payload.
- `FailingConnector` — always fails (test utility).

Connectors are registered per target and can be overridden for testing:

```python
register_connector("datev_export", MyRealDatevConnector())
```

---

## Internal APIs

All endpoints require OPA permission `manage_integrations`.

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/internal/integrations/jobs` | List jobs (filter by status, target, tenant, client, payload_type) |
| `POST` | `/api/internal/integrations/jobs` | Manually create a job for a source entity |
| `GET`  | `/api/internal/integrations/jobs/{job_id}` | Job detail + dispatch result |
| `POST` | `/api/internal/integrations/jobs/{job_id}/retry` | Retry a failed/dead-letter job |
| `POST` | `/api/internal/integrations/dispatch` | Trigger dispatch of all pending jobs |

---

## Evidence & Audit Trail

Every job state transition emits a structured event via `record_event`:

| Event Type                        | When                          |
|-----------------------------------|-------------------------------|
| `integration_job_created`         | Job enqueued                  |
| `integration_job_dispatched`      | Connector called              |
| `integration_job_delivered`       | Connector reported success    |
| `integration_job_failed`          | Connector reported failure    |
| `integration_job_dead_letter`     | Max attempts exceeded         |
| `integration_job_retried`         | Manual retry triggered        |

Each event includes: `job_id`, `tenant_id`, `client_id`, `system_id`,
`target`, `payload_type`, `source_entity_type`, `source_entity_id`,
`status`, `attempt_count`, `trace_id`.

---

## Multi-Tenancy & Idempotency

- All jobs carry `tenant_id`, `client_id`, `system_id` — there is no
  cross-tenant data leakage.
- Idempotency keys are `{target}:{entity_type}:{entity_id}`, ensuring
  that re-enqueuing the same entity for the same target returns the
  existing job rather than creating a duplicate.
- Store-level locking prevents race conditions.

---

## How This Supports Enterprise Rollout

1. **No premature coupling**: mock sinks mean zero external dependency.
   Real connectors (DATEV OAuth, SAP BTP Event Mesh) can be wired in
   later by implementing `BaseConnector.dispatch`.
2. **Contract stability**: `schema_version: "v1"` payloads are frozen.
   Breaking changes require a new version.
3. **Retry & dead-letter**: enterprise-grade reliability from day one.
4. **Audit compliance**: full evidence trail satisfies DACH enterprise
   audit requirements.
5. **Mandant-aware**: DATEV payloads are structured around
   `client_id` (Mandant), matching the Kanzlei operating model.

---

## Files

| File | Purpose |
|------|---------|
| `app/integrations/__init__.py` | Package marker |
| `app/integrations/models.py` | Enums + `IntegrationJob` + `DispatchResult` |
| `app/integrations/store.py` | In-memory job store, feature flags, evidence |
| `app/integrations/outbox.py` | Outbox helper: entity → job creation |
| `app/integrations/mappers.py` | DATEV / SAP / generic payload mappers |
| `app/integrations/connectors.py` | Connector interface + stub implementations |
| `app/integrations/dispatcher.py` | Dispatch loop: pending → deliver / dead-letter |
| `app/main.py` | Internal API endpoints (Wave 15 section) |
| `tests/test_integration_jobs.py` | 33 tests covering all scenarios |

---

## Example Scenario

1. Advisor preset creates an `AiRiskAssessment` for tenant `acme`,
   client `mandant-42`, system `scoring-ai`.
2. Operator calls `POST /api/internal/integrations/jobs` with
   `source_entity_type=AiRiskAssessment`, `target=datev_export`.
3. System creates an `IntegrationJob` (status: `pending`).
4. Operator calls `POST /api/internal/integrations/dispatch`.
5. Dispatcher maps the risk record to a DATEV-friendly payload
   (`Risikobewertung_KI`, German labels) and calls
   `DatevExportConnector.dispatch`.
6. Connector writes JSON to mock sink, returns success.
7. Job transitions to `delivered`.
8. Evidence events recorded at each step with full trace context.

---

## Future Integration Wiring

When ready to connect real systems:

1. Implement `BaseConnector.dispatch` for DATEV OAuth / SAP BTP.
2. Register via `register_connector("datev_export", RealDatevConnector())`.
3. Add Temporal workflow for background dispatch (structure already
   matches the activity pattern used in Waves 13/14).
4. Enable per-tenant feature flags for automatic outbox enqueue on
   GRC record creation.

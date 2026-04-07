# Enterprise governance hardening (audit trail, RBAC, NIS2 workflow, compliance calendar)

This document supports review of the GoBD-style audit log, API-key enterprise RBAC, NIS2 incident API, and compliance calendar. It is **not legal advice**. Operational deadlines (24h / 72h / final) depend on national transposition, sector guidance, and case facts; the product encodes **configurable defaults** and explicit overrides with audit.

## 1. Four feature blocks

| Block | Purpose | Primary persistence |
| --- | --- | --- |
| GoBD audit log (`audit_logs`) | Append-only governance trail with hash chain | `AuditLogTable` |
| Enterprise RBAC | Capability-style permissions on API-key routes | `Permission` + `x-opa-user-role` |
| NIS2 incidents | Tenant-scoped incident record + workflow + regulatory deadlines | `NIS2IncidentTable` |
| Compliance calendar | Structured regulatory **obligations / due dates** (not a general task list) | `ComplianceDeadlineTable` |

## 2. Audit event model (governance)

Canonical governance event names are centralized in `app/governance_taxonomy.py` and should be
used by enterprise-critical mutation endpoints to avoid drift in action/entity labels over time.

Hash-chain fields (`previous_hash`, `entry_hash`) intentionally cover the **legacy payload** only (tenant, action, entity, before/after text, timestamp, previous hash) so existing chains remain verifiable. Extended fields are **stored for query and export** but are not yet mixed into the hash input.

Recommended populated fields for critical mutations (when applicable):

- `tenant_id`, `actor` (subject id), `actor_role`, `action`, `entity_type`, `entity_id`
- `outcome` (e.g. `success` / `failure`)
- `correlation_id` (from `x-correlation-id` or `x-request-id` when present)
- `metadata_json` (sanitised JSON; secrets/tokens redacted; size-bounded)
- `created_at_utc` (server time at insert)
- `ip_address` / `user_agent` when the request is available

**Append-only:** SQLAlchemy `before_flush` rejects UPDATE/DELETE on `AuditLogTable`. Database triggers are still recommended for production PostgreSQL.

## 3. Permission model (API key + `x-opa-user-role`)

| Permission | Typical use |
| --- | --- |
| `VIEW_AUDIT_LOG` | List JSON audit entries |
| `EXPORT_AUDIT_LOG` | GoBD XML export |
| `VIEW_INCIDENTS` / `MANAGE_INCIDENTS` | NIS2 incident read / write + deadline override |
| `VIEW_COMPLIANCE_CALENDAR` | List/get/iCal export |
| `MANAGE_COMPLIANCE_CALENDAR` | Create/update/delete deadlines + idempotent seed |

Missing or unknown `x-opa-user-role` resolves to **contributor** (conservative for export; still allows read-only calendar/incident views where granted).

## 4. NIS2 workflow and deadlines

- **Technical workflow (IR):** `detected → contained → eradicated → recovered → closed` with deterministic transitions.
- **Regulatory clock (authoritative start):** `detected_at` (set at creation). Notification and report deadlines are initialised from this instant.
- **Default offsets:** early notification **+24h**, detailed report **+72h** from `detected_at`; **final_report_deadline** defaults to **+30 days after** the 72h report deadline (placeholder product default—adjust per legal/process).
  The numeric defaults are centralized in `NIS2DeadlinePolicy` (`app/governance_taxonomy.py`).
- **Overdue flags** on the API compare `datetime.now(UTC)` to each open deadline until `closed_at` is set.
- **Overrides:** `PATCH /api/v1/nis2-incidents/{id}/deadlines` requires `MANAGE_INCIDENTS`, a minimum-length **reason**, at least one deadline field, and emits a governance audit entry.

## 5. Calendar vs reminders vs SLA

- **Reminder:** operational follow-up in existing reminder/advisor flows (out of scope for `compliance_deadlines`).
- **SLA / evaluation:** breach or escalation signals from monitoring/KPI layers; not duplicated as calendar rows.
- **Compliance calendar:** time-bound **regulatory or programme obligations** with optional linkage via `source_type` / `source_id` (e.g. DACH catalog seeds). User-created entries have null source fields.

**Idempotent seed:** `POST .../seed-defaults` upserts by `(tenant_id, source_type='dach_catalog', source_id)` using a partial unique index.

## 6. Limitations (DACH)

- National BSI / reporting channels and exact statutory windows may differ; deadlines are **defaults** plus audited overrides.
- GoBD XML export aids technical traceability; organisational GoBD processes (retention, access control, system documentation) remain customer responsibility.
- RLS in production PostgreSQL must align with these tables; API-key tests use SQLite without RLS.

## 7. Suggested reviewer checklist

- [ ] Confirm OPA/gateway forwards `x-opa-user-role`, `x-actor-id`, and correlation headers on enterprise routes.
- [ ] Verify production DB append-only policy (ORM guard + trigger) for `audit_logs`.
- [ ] Validate calendar seed keys and due dates against your compliance programme.
- [ ] Reconcile NIS2 final reporting window with counsel / national guidance.
